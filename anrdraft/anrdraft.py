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


def get_num_players(draft_id):
    return len(get_players(draft_id))


def get_players(draft_id):
    return DRAFTS[draft_id]['players'].keys()


def get_creator(draft_id):
    return DRAFTS[draft_id]['metadata']['creator']


def get_picks(draft_id, player_name, side, pack_num):
    return DRAFTS[draft_id]['players'][player_name][side]['packs'][pack_num]


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
                while len(cards) > get_num_players(draft_id):
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
        }
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


# Draft Operations

def open_new_pack(draft_id, side):
    """
    Sends first set of picks to players.
    After this the pack-sending logic is entirely event-driven.
    """
    for player in get_players(draft_id):
        pack = DRAFTS[draft_id]['players'][player][side]['packs'].pop(0)
        card_blocks = [blocks.divider()]
        for card in pack:
            card_text = templates.format(card)
            card_blocks.append(blocks.card_text(templates.format(card)))
            card_blocks.append(blocks.text_with_button(
                card_text, card['title']))
            card_blocks.append(blocks.divider())
        client.chat_postMessage(
            channel=get_player_dm_id(player),
            text='Welcome to the draft! Here is your first corp ID pack. Good luck!'
        )
        client.chat_postMessage(
            channel=get_player_dm_id(player),
            blocks=card_blocks
        )

# Endpoints / Slash Commands


def respond_to_selection(payload):
    request = {
        'text': payload['actions'][0]['selected_option']['value'] + ' was selected!',
        "replace_original": False
    }
    requests.post(payload['response_url'], json=request, verify=False)


@app.route('/actions', methods=['POST'])
def actions():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        payload = request.form['payload']
        respond_to_selection(payload)
        return jsonify({'success': True})


@app.route('/debug', methods=['POST'])
def debug():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        # return '```' + json.dumps(DRAFTS, indent=4, sort_keys=True) + '```'
        return '```' + json.dumps(PLAYERS, indent=4, sort_keys=True) + '```'
        # draft = DRAFTS[request.form['text']]
        # me = draft['players']['weston.odom']
        # cards = me['corp']['packs'][2]
        # card_blocks = [blocks.divider()]
        # for card in cards:
        #     print('\ncard:\n')
        #     print(card)
        #     print('\n\n')
        #     card_text = templates.format(card)
        #     # card_blocks.append(blocks.card_text(templates.format(card)))
        #     # image_url = card.get('image_url')
        #     # if image_url:
        #     #     card_blocks.append(blocks.card_image(
        #     #         image_url,
        #     #         card['title']
        #     #     ))
        #     # card_blocks.append(blocks.pick_button(card['title']))
        #     card_blocks.append(blocks.text_with_button(
        #         card_text, card['title']))
        #     card_blocks.append(blocks.divider())
        #     print('\nblocks:\n')
        #     print({"blocks": card_blocks})
        #     print('\n\n')
        # return jsonify({"blocks": card_blocks})


@app.route('/createdraft', methods=['POST'])
def create_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        user_name = request.form['user_name']
        user_id = request.form['user_id']
        new_draft_code = setup_draft(user_name, user_id)
        # TODO: add player and draft_id to reverse lookup table
        # TODO: add player and draft_id to reverse lookup table
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
        DRAFTS[draft_id]['metadata']['has_started'] = True
        open_new_pack(draft_id, 'corp')
        return 'Draft successfully started.'


@app.route('/joindraft', methods=['POST'])
def join_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        draft_id = request.form['text']
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        player_name = request.form['user_name']
        player_id = request.form['user_id']
        add_player(player_name, player_id, draft_id)
        creator_name = get_creator(draft_id)
        # TODO: notify creator
        # TODO: add player and draft_id to reverse lookup table
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
