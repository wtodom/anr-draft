#!/usr/bin/env python


import json
import os
import random
import string
import time

from flask import Flask, jsonify, request
import requests
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import slack

from templates import blocks, templates

app = Flask(__name__)


HERE = os.path.dirname(os.path.abspath(__file__))

on_heroku = os.environ.get('on_heroku')
if on_heroku:
    API_TOKEN = os.environ.get('api_token')
    VERIFICATION_TOKEN = os.environ.get('verification_token')
    SENTRY_DSN = os.environ.get('sentry_dsn')
else:
    with open(HERE + '/secrets.json', 'r') as f:
        secrets = json.loads(f.read())
        API_TOKEN = secrets['api_token']
        VERIFICATION_TOKEN = secrets['verification_token']
        SENTRY_DSN = secrets['sentry_dsn']

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[FlaskIntegration()]
)

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


def get_pack(draft_id, player_name, pack_num):
    return DRAFTS[draft_id]['players'][player_name]['packs'][pack_num]


def get_picks(draft_id, player_name):
    return DRAFTS[draft_id]['players'][player_name]['picks']


def player_has_pack_waiting(draft_id, player_name):
    inbox = DRAFTS[draft_id]['players'][player_name]['inbox']
    return len(inbox) > 0


def player_has_open_pack(draft_id, player_name):
    return DRAFTS[draft_id]['players'][player_name]['has_open_pack']


def draft_finished(draft_id):
    for player in get_players(draft_id):
        inbox = DRAFTS[draft_id]['players'][player]['inbox']
        packs = DRAFTS[draft_id]['players'][player]['packs']
        if len(packs) > 0 or len(inbox) > 0:
            return False
    return True


def draft_started(draft_id):
    return DRAFTS[draft_id]['metadata']['has_started']


def user_can_create_draft(username):
    for draft in DRAFTS:
        if DRAFTS[draft]['metadata']['creator'] == username:
            return False
    return True


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


def deal_card(draft_id, player_name, pack_num, card):
    DRAFTS[draft_id]["players"][player_name]['packs'][pack_num].append(
        card)


def read_cards_from_file(filepath):
    with open(filepath, 'r') as f:
        cards = json.loads(f.read())['cards']
        return cards


def setup_packs(draft_id):
    num_players = get_num_players(draft_id)
    total_ids = num_players * 5
    card_total = num_players * 15 * 3

    data_dir = HERE + '/data'
    corp_ids = read_cards_from_file(data_dir + '/corp_ids.json')
    random.shuffle(corp_ids)
    corp_ids = corp_ids[:total_ids]
    corp_cards = read_cards_from_file(data_dir + '/corp_cards.json')
    random.shuffle(corp_cards)
    corp_cards = corp_cards[:card_total]
    runner_ids = read_cards_from_file(data_dir + '/runner_ids.json')
    random.shuffle(runner_ids)
    runner_ids = runner_ids[:total_ids]
    runner_cards = read_cards_from_file(data_dir + '/runner_cards.json')
    random.shuffle(runner_cards)
    runner_cards = runner_cards[:card_total]

    pack_num = 0
    cards_per_pack = len(corp_cards) // (get_num_players(draft_id) * 3)
    while len(corp_ids) >= get_num_players(draft_id):
        for player in get_players(draft_id):
            card_index = random.randint(0, len(corp_ids) - 1)
            card = corp_ids.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
    pack_num += 1

    while corp_cards and pack_num <= 3:
        for player in get_players(draft_id):
            card_index = random.randint(0, len(corp_cards) - 1)
            card = corp_cards.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
        if len(get_pack(draft_id, player, pack_num)) == cards_per_pack:
            pack_num += 1

    while len(runner_ids) >= get_num_players(draft_id):
        for player in get_players(draft_id):
            card_index = random.randint(0, len(runner_ids) - 1)
            card = runner_ids.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
    pack_num += 1

    while len(runner_cards) >= get_num_players(draft_id):
        for player in get_players(draft_id):
            card_index = random.randint(0, len(runner_cards) - 1)
            card = runner_cards.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
        if len(get_pack(draft_id, player, pack_num)) == cards_per_pack:
            pack_num += 1


def add_player(player_name, player_id, draft_id):
    im_list = client.im_list()
    for im in im_list['ims']:
        if im['user'] == player_id:
            player_dm_id = im['id']

    DRAFTS[draft_id]['players'][player_name] = {
        'inbox': [],
        'packs': [[], [], [], [], [], [], [], []],
        'picks': {
            'corp': [],
            'runner': []
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
        return 'Draft `{draft_id}` does not exist.'.format(draft_id=draft_id)
    if DRAFTS[draft_id]['metadata']['has_started']:
        return 'Draft `{draft_id}` has already started.'.format(draft_id=draft_id)
    if player_name not in get_players(draft_id):
        return 'You were not registered for `{draft_id}`.'.format(draft_id=draft_id)
    del DRAFTS[draft_id]['players'][player_name]
    return 'ok'


def assign_seat_numbers(draft_id):
    num_players = get_num_players(draft_id)
    seats = list(range(num_players))
    random.shuffle(seats)
    for player in get_players(draft_id):
        PLAYERS[player]['seat_number'] = seats.pop(0)


# Draft Operations

def open_new_pack(draft_id):
    """
    Sends first set of picks to players.
    After this the pack-sending logic is entirely event-driven.
    """
    for player in get_players(draft_id):
        pack = DRAFTS[draft_id]['players'][player]['packs'].pop(0)
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
    player_picks = player['picks'][picked_card['side_code']]
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
        # TODO: maybe encode list index so we don't have to iterate to pick the card.
        button_value = '--'.join([draft_id, player, card['code']])
        pick_block = blocks.text_with_button(
            card_text, card['title'], button_value)
        card_blocks.append(pick_block)
        card_blocks.append(blocks.divider())
    client.chat_postMessage(
        channel=get_player_dm_id(player),
        text='Here is your next pack.'
    )
    client.chat_postMessage(
        channel=get_player_dm_id(player),
        blocks=card_blocks
    )
    DRAFTS[draft_id]['players'][player]['has_open_pack'] = True


def open_next_pack_or_wait(payload):
    card_name = ' '.join(payload['actions'][0]['text']['text'].split(' ')[1:])
    request = {
        'text': card_name + ' was picked. A new pack will open once it is passed to you.',
        "replace_original": True
    }
    requests.post(payload['response_url'], json=request)
    need_new_pack = True
    for action in payload['actions']:
        draft_id, _, _ = action['value'].split('--')
        for player in get_players(draft_id):
            if player_has_pack_waiting(draft_id, player):
                need_new_pack = False
                if not player_has_open_pack(draft_id, player):
                    open_next_pack(draft_id, player)
    if need_new_pack:
        if draft_finished(draft_id):
            for player in get_players(draft_id):
                client.chat_postMessage(
                    channel=get_player_dm_id(player),
                    text='The draft is complete! Here are your picks:'
                )
                picks = get_picks(draft_id, player)
                client.chat_postMessage(
                    channel=get_player_dm_id(player),
                    text=format_picks('Corp:\n\n', picks['corp'])
                )
                client.chat_postMessage(
                    channel=get_player_dm_id(player),
                    text=format_picks('Runner:\n\n', picks['runner'])
                )
            cleanup(draft_id)
        else:
            open_new_pack(draft_id)


def cleanup(draft_id):
    del DRAFTS[draft_id]
    # make a copy for iteration so you can delete from the real one
    for player in list(PLAYERS.keys()):
        if PLAYERS[player]['draft_id'] == draft_id:
            del PLAYERS[player]


def format_picks(heading, picks):
    picks_copy = picks[:]
    for i, card in enumerate(picks_copy):
        if i < 5 or 49 < i < 53:
            pre = '1 '
        else:
            pre = '3 '
        picks_copy[i] = pre + card
    cards = '\n'.join(picks_copy)
    return '```' + heading + '\n' + cards + '```'


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
        if request.form['user_name'] == 'weston.odom':
            with open('debug.log', 'w') as f:
                f.write(json.dumps({
                    'dumped_at': time.strftime("%Y-%m-%d %H:%M"),
                    'PLAYERS': PLAYERS,
                    'DRAFTS': DRAFTS
                }, indent=4, sort_keys=True))
            return 'Dump successful.'
        return 'Only an admin can use this command.'


@app.route('/draft-create', methods=['POST'])
def create_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        user_name = request.form['user_name']
        if user_can_create_draft(user_name):
            user_id = request.form['user_id']
            new_draft_code = setup_draft(user_name, user_id)
            return (
                'Draft successfully created. Your draft ID is `{draft_id}`. '
                'Other players can use this code with the `/draft-join` '
                'command to join the draft.'
            ).format(draft_id=new_draft_code)
        else:
            return (
                'You can only create one draft at a time. You can use '
                '`/draft-cancel [draft_id]` to quit and then start over.'
            )


@app.route('/draft-cancel', methods=['POST'])
def cancel_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        user_name = request.form['user_name']
        draft_id = request.form['text']
        if user_name != get_creator(draft_id):
            return 'Only the draft creator can cancel it.'
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        if draft_started(draft_id):
            return 'Draft `{draft_id}` has already started.'.format(
                draft_id=draft_id
            )
        _cancel_draft(draft_id)
        return 'Draft successfully cancelled.'


def _cancel_draft(draft_id):
    for player in get_players(draft_id):
        client.chat_postMessage(
            channel=get_player_dm_id(player),
            text=(
                'Draft `{draft_id}` was cancelled by '
                '`{creator}`.'.format(
                    draft_id=draft_id,
                    creator=get_creator(draft_id)
                )
            )
        )
    cleanup(draft_id)


@app.route('/draft-start', methods=['POST'])
def start_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        draft_id = request.form['text']
        user_name = request.form['user_name']
        if user_name != get_creator(draft_id):
            return 'Only the draft creator can start the draft.'
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        if draft_started(draft_id):
            return 'Draft `{draft_id}` has already started.'.format(
                draft_id=draft_id
            )
        setup_packs(draft_id)
        assign_seat_numbers(draft_id)
        DRAFTS[draft_id]['metadata']['has_started'] = True
        for player in get_players(draft_id):
            client.chat_postMessage(
                channel=get_player_dm_id(player),
                text='Welcome to the draft! Here is your first pack. Good luck!'
            )
        open_new_pack(draft_id)
        return '', 200


@app.route('/draft-join', methods=['POST'])
def join_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        draft_id = request.form['text']
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        player_name = request.form['user_name']
        if player_name in get_players(draft_id):
            return 'You can not join the same draft more than once.'
        if draft_started(draft_id):
            return 'Draft `{draft_id}` has already started.'.format(
                draft_id=draft_id
            )
        player_id = request.form['user_id']
        add_player(player_name, player_id, draft_id)
        creator_name = get_creator(draft_id)
        player_dm_channel = get_player_dm_id(creator_name)
        num_players = get_num_players(draft_id)
        client.chat_postMessage(
            channel=player_dm_channel,
            text=(
                '{player} has joined your draft (`{draft}`). There are now '
                '{num} players registered.').format(
                    player=player_name, draft=draft_id, num=num_players
            )
        )
    return (
        'Successfully joined draft `{draft_id}`. Please wait for `{creator}` '
        'to begin the draft.'
    ).format(draft_id=draft_id, creator=creator_name)


@app.route('/draft-leave', methods=['POST'])
def leave_draft():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        draft_id = request.form['text']
        player_name = request.form['user_name']
        # remove_player() does the checks I usually do here
        res = remove_player(player_name, draft_id)
        if res != 'ok':
            return 'Failed to leave draft. Error: ' + res
        if player_name == get_creator(draft_id):
            _cancel_draft(draft_id)
            return (
                'Successfully withdrew from draft `{draft_id}`. '
                'Because you were the creator of this draft it has '
                'been cancelled. The other players have been notified.'
            ).format(draft_id=draft_id)
        creator_name = get_creator(draft_id)
        player_dm_channel = get_player_dm_id(creator_name)
        num_players = get_num_players(draft_id)
        client.chat_postMessage(
            channel=player_dm_channel,
            text=(
                '{player} has left your draft (`{draft}`). There are now '
                '{num} players registered.').format(
                    player=player_name, draft=draft_id, num=num_players
            )
        )
    return (
        'Successfully withdrew from draft `{draft_id}`.'
    ).format(draft_id=draft_id, creator=creator_name)


@app.route('/draft-picks', methods=['POST'])
def picks():
    request_token = request.form['token']
    if request_token == VERIFICATION_TOKEN:
        player_name = request.form['user_name']
        # remove_player() does the checks I usually do here
        if player_name not in PLAYERS:
            return 'You are not enrolled in a draft.'
        draft_id = PLAYERS[player_name]['draft_id']
        client.chat_postMessage(
            channel=get_player_dm_id(player_name),
            text='Here are your picks so far:'
        )
        picks = get_picks(draft_id, player_name)
        client.chat_postMessage(
            channel=get_player_dm_id(player_name),
            text=format_picks('Corp:\n\n', picks['corp'])
        )
        client.chat_postMessage(
            channel=get_player_dm_id(player_name),
            text=format_picks('Runner:\n\n', picks['runner'])
        )
    return '', 200


if __name__ == '__main__':
    app.run()
