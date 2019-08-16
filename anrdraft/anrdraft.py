#!/usr/bin/env python


import json
import os
import random
import string

from flask import Flask, jsonify, request
import requests
import slack

from templates import blocks, templates

app = Flask(__name__)


HERE = os.path.dirname(os.path.abspath(__file__))
with open(HERE + '/secrets.json', 'r') as f:
    tokens = json.loads(f.read())
    API_TOKEN = tokens['api_token']
    VERIFICATION_TOKEN = tokens['verification_token']

client = slack.WebClient(token=API_TOKEN)

DRAFTS = {}
PLAYERS = {}


# Getters

def get_player_id(player_name):
    if player_name in PLAYERS:
        return PLAYERS[player_name]['player_id']


def get_player_dm_id(player_name):
    return PLAYERS[player_name]['dm_id']


def get_player_draft_info(player_name):
    draft_id = PLAYERS[player_name]['draft_id']
    return DRAFTS[draft_id]['players'][player_name]


def get_seat_number(player_name):
    return PLAYERS[player_name]['seat_number']


def get_num_players(draft_id):
    return len(get_players(draft_id))


def get_players(draft_id):
    return DRAFTS[draft_id]['players'].keys()


def get_creator(draft_id):
    return DRAFTS[draft_id]['metadata']['creator']


def get_picks(draft_id, player_name, side, pack_num):
    return DRAFTS[draft_id]['players'][player_name][side]['packs'][pack_num]


def player_has_pack_waiting(draft_id, player_name):
    inbox = DRAFTS[draft_id]['players'][player_name]['inbox']
    return len(inbox) > 0


def player_has_open_pack(draft_id, player_name):
    return DRAFTS[draft_id]['players'][player_name]['has_open_pack']

# Draft Setup


def setup_draft(initiating_user_name, initiating_user_id):
    draft_id = gen_draft_id()
    while draft_id in DRAFTS:
        draft_id = gen_draft_id()
    DRAFTS[draft_id] = {
        'metadata': {
            'creator': initiating_user_name,
            'has_started': False,
            'stage': 0
        },
        'players': {}
    }
    add_player(initiating_user_name, initiating_user_id, draft_id)
    return draft_id


def gen_draft_id():
    code = ''
    for _ in range(4):
        total_chars = len(string.ascii_lowercase)
        index = random.randint(0, total_chars - 1)
        letter = string.ascii_lowercase[index]
        code += letter
    return code


def deal_card(draft_id, player_name, side, pack_num, card):
    DRAFTS[draft_id]["players"][player_name][side]['packs'][pack_num].append(
        card)


def setup_packs(draft_id):
    data_files = os.listdir(HERE + '/data')
    for filename in data_files:
        filepath = HERE + '/data/' + filename
        with open(filepath, 'r') as f:
            side = filename.split('_')[0]
            cards = json.loads(f.read())['cards']
            if filename in ['corp_ids.json', 'runner_ids.json']:
                cards = cards[:8]
                while len(cards) >= get_num_players(draft_id):
                    for player in DRAFTS[draft_id]["players"]:
                        card_index = random.randint(0, len(cards) - 1)
                        card = cards.pop(card_index)
                        deal_card(draft_id, player, side, 0, card)
            elif filename in ['corp_cards.json', 'runner_cards.json']:
                cards = cards[:30]
                cards_per_pack = len(cards) // (get_num_players(draft_id) * 3)
                pack_num = 1
                while cards:
                    for player in DRAFTS[draft_id]["players"]:
                        card_index = random.randint(0, len(cards) - 1)
                        card = cards.pop(card_index)
                        deal_card(draft_id, player, side, pack_num, card)
                    if len(get_picks(draft_id, player, side, pack_num)) == cards_per_pack:
                        pack_num += 1


def add_player(player_name, player_id, draft_id):
    im_list = client.im_list()
    for im in im_list['ims']:
        if im['user'] == player_id:
            player_dm_id = im['id']

    DRAFTS[draft_id]['players'][player_name] = {
        'inbox': [],
        'corp': {
            'packs': [[], [], [], []],
            'picks': []
        },
        'runner': {
            'packs': [[], [], [], []],
            'picks': []
        },
        'has_open_pack': False
    }
    PLAYERS[player_name] = {
        'player_id': player_id,
        'draft_id': draft_id,
        'dm_id': player_dm_id
    }

    return 'ADD_SUCCESSFUL'


def remove_player(player_name, draft_id):
    if draft_id not in DRAFTS:
        return 'DRAFT_NOT_FOUND'
    if DRAFTS[draft_id]['metadata']['has_started']:
        return 'DRAFT_STARTED'
    if player_name not in DRAFTS[draft_id]['players']:
        return 'PLAYER_NOT_FOUND'
    del DRAFTS[draft_id]['players'][player_name]
    return 'REMOVE_SUCCESSFUL'


def assign_seat_numbers(draft_id):
    num_players = get_num_players(draft_id)
    seats = list(range(num_players))
    random.shuffle(seats)
    for player in get_players(draft_id):
        PLAYERS[player]['seat_number'] = seats.pop(0)

# Draft Operations


def open_new_pack(draft_id, side):
    """
    Sends first set of picks to players.
    After this the pack-sending logic is entirely event-driven.
    """
    for player in get_players(draft_id):
        pack = DRAFTS[draft_id]['players'][player][side]['packs'].pop(0)
        DRAFTS[draft_id]['players'][player]['inbox'].append(pack)
        card_blocks = [blocks.divider()]
        for card in pack:
            card_text = templates.format(card)
            button_value = '--'.join([draft_id, player, card['code']])
            pick_block = blocks.text_with_button(
                card_text, card['title'], button_value)
            card_blocks.append(pick_block)
            card_blocks.append(blocks.divider())
        client.chat_postMessage(
            channel=get_player_dm_id(player),
            text='Welcome to the draft! Here is your {side} ID pack. Good luck!'.format(
                side=side)
        )
        client.chat_postMessage(
            channel=get_player_dm_id(player),
            blocks=card_blocks
        )
        DRAFTS[draft_id]['players'][player]['has_open_pack'] = True


def handle_pick(actions):
    for action in actions:
        encoded_value = action['value']
        draft_id, player_name, card_code = encoded_value.split('--')
        pack = DRAFTS[draft_id]['players'][player_name]['inbox'].pop(0)
        for i, card in enumerate(pack):
            if card['code'] == card_code:
                card_index = i
                break
        picked_card = pack.pop(card_index)
        add_card_to_picks(draft_id, player_name, picked_card)
        DRAFTS[draft_id]['players'][player_name]['has_open_pack'] = False
        if len(pack) > 0:
            pass_pack(draft_id, player_name, pack)


def add_card_to_picks(draft_id, player_name, picked_card):
    draft = DRAFTS[draft_id]
    player = draft['players'][player_name]
    player_picks = player[picked_card['side_code']]['picks']
    player_picks.append(picked_card['title'])


def pass_pack(draft_id, player_name, pack):
    player_seat = get_seat_number(player_name)
    next_seat = (player_seat + 1) % get_num_players(draft_id)
    for player in get_players(draft_id):
        if get_seat_number(player) == next_seat:
            DRAFTS[draft_id]['players'][player]['inbox'].append(pack)


def open_next_pack(draft_id, player):
    pack = DRAFTS[draft_id]['players'][player]['inbox'][0]
    card_blocks = [blocks.divider()]
    for card in pack:
        card_text = templates.format(card)
        button_value = '--'.join([draft_id, player, card['code']])
        pick_block = blocks.text_with_button(
            card_text, card['title'], button_value)
        card_blocks.append(pick_block)
        card_blocks.append(blocks.divider())
    side = pack[0]['side_code']
    client.chat_postMessage(
        channel=get_player_dm_id(player),
        text='Here is your next {side} pack.'.format(side=side))
    client.chat_postMessage(
        channel=get_player_dm_id(player),
        blocks=card_blocks
    )
    DRAFTS[draft_id]['players'][player]['has_open_pack'] = True


def open_next_pack_or_wait(payload):
    request = {
        'text': ' '.join(payload['actions'][0]['text']['text'].split(' ')[1:]) + ' was picked.',
        "replace_original": True
    }
    requests.post(payload['response_url'], json=request)
    need_new_pack = True
    for action in payload['actions']:
        draft_id, player_name, _ = action['value'].split('--')
        for player in get_players(draft_id):
            if (player_has_pack_waiting(draft_id, player) and
                    not player_has_open_pack(draft_id, player_name)):
                open_next_pack(draft_id, player)
                need_new_pack = False
    if need_new_pack:
        open_new_pack(draft_id)


# Endpoints / Slash Commands

@app.route('/actions', methods=['POST'])
def actions():
    payload = json.loads(request.form['payload'])

    request_token = payload['token']
    if request_token == VERIFICATION_TOKEN:
        actions = payload['actions']
        handle_pick(actions)
        open_next_pack_or_wait(payload)
        return jsonify({'success': True})


@app.route('/debug', methods=['POST'])
def debug():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        with open('debug.log', 'w') as f:
            f.write(json.dumps({
                'PLAYERS': PLAYERS,
                'DRAFTS': DRAFTS
            }, indent=4, sort_keys=True))
        return 'OK', 200


@app.route('/createdraft', methods=['POST'])
def create_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        user_name = request.form['user_name']
        user_id = request.form['user_id']
        new_draft_code = setup_draft(user_name, user_id)
        return (
            'Draft successfully created. Your draft ID is `{draft_id}`. '
            'Other players can use this code with the `/joindraft` command '
            'to join the draft.'
        ).format(draft_id=new_draft_code)


@app.route('/startdraft', methods=['POST'])
def start_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        draft_id = request.form['text']
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        setup_packs(draft_id)
        assign_seat_numbers(draft_id)
        DRAFTS[draft_id]['metadata']['has_started'] = True
        open_new_pack(draft_id, 'corp')
        return '', 200


@app.route('/joindraft', methods=['POST'])
def join_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        draft_id = request.form['text']
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        player_name = request.form['user_name']
        # TODO: don't allow joining the same draft multiple times
        player_id = request.form['user_id']
        add_player(player_name, player_id, draft_id)
        creator_name = get_creator(draft_id)
        channel = get_player_dm_id(creator_name)
        num_players = get_num_players(draft_id)
        client.chat_postMessage(
            channel=channel,
            text=(
                '{player} has joined your draft (`{draft}`). There are now '
                '{num} players registered.').format(
                    player=player_name, draft=draft_id, num=num_players
            )
        )
    return (
        'Successfully joined draft `{draft_id}`. Please wait for `{creator}` '
        'begin the draft.'
    ).format(draft_id=draft_id, creator=creator_name)


@app.route('/leavedraft', methods=['POST'])
def leave_draft():
    # NOTE: UNTESTED
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        draft_id = request.form['text']
        player_name = request.form['user_name']
        res = remove_player(player_name, draft_id)
        if 'SUCCESS' not in res:
            return 'Failed to leave draft. Error: ' + res
        creator_name = get_creator(draft_id)
        # TODO: notify creator
    return (
        'Successfully joined draft `{draft_id}`. Please wait for `{creator}` '
        'begin the draft.'
    ).format(draft_id=draft_id, creator=creator_name)


@app.route('/resetdraft', methods=['POST'])
def reset_draft():
    return '`/resetdraft` is deprecated.'
    # request_token = request.form['token']
    # if request_token == VERIFICATION_TOKEN:
    #     if request.form['user_name'] != 'weston.odom':
    #         return 'This action is only available to admins.'
    #     draft_id = request.form['text']
    #     if draft_id == '':
    #         return 'You must provide a draft_id.'
    #     del DRAFTS[draft_id]
    #     return 'Draft `{draft_id}` successfully deleted.'.format(
    #         draft_id=draft_id
    #     )


if __name__ == '__main__':
    app.run()

    # data_files = os.listdir(HERE + '/data')
    # for filename in data_files:
    #     if filename.split('.')[1] != 'json':
    #         continue
    #     filepath = HERE + '/data/' + filename
    #     with open(filepath, 'r') as f:
    #         side = filename.split('_')[0]
    #         cards = json.loads(f.read())['cards']
    #         for card in cards:
    #             print(templates.format(card))
    #             print('~~~')
