#!/usr/bin/env python

import json
import os
import random
import string

import requests

from flask import Flask, jsonify, request


app = Flask(__name__)

TOKEN = 'pphnmMPvRz4Dy3xzR9WmbJtf'
DRAFTS = {

}


###########
# helpers #
###########

def get_num_players(draft_id):
    return len(get_players(draft_id))


def get_players(draft_id):
    return DRAFTS[draft_id]['players'].keys()


def get_creator(draft_id):
    return DRAFTS[draft_id]['metadata']['creator']


def get_picks(draft_id, player_name, side, pack_num):
    return DRAFTS[draft_id]['players'][player_name][side]['packs'][pack_num]


#####################
# draft setup logic #
#####################

def setup_draft(initiating_user):
    draft_id = gen_draft_id()
    while draft_id in DRAFTS:
        draft_id = gen_draft_id()
    DRAFTS[draft_id] = {
        'metadata': {
            'creator': initiating_user,
            'has_started': False
        },
        'players': {
            initiating_user: {
                'corp': {
                    'packs': [[], [], [], []],
                    'picks': []
                },
                'runner': {
                    'packs': [[], [], [], []],
                    'picks': []
                }
            }
        }
    }
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
        card['title'])


def setup_packs(draft_id):
    here = os.path.dirname(os.path.abspath(__file__))
    data_files = os.listdir(here + '/data')
    for filename in data_files:
        if filename.split('.')[1] != 'json':
            # TODO: remove this check after removing file
            continue
        filepath = here + '/data/' + filename
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


def add_player(player_name, draft_id):
    DRAFTS[draft_id]['players'][player_name] = {
        'corp': {
            'packs': [[], [], [], []],
            'picks': []
        },
        'runner': {
            'packs': [[], [], [], []],
            'picks': []
        }
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

##################
# slash commands #
##################


@app.route('/debug', methods=['POST'])
def debug():
    request_token = request.form['token']
    if request_token == TOKEN:
        return '```' + json.dumps(DRAFTS, indent=4, sort_keys=True) + '```'


@app.route('/createdraft', methods=['POST'])
def create_draft():
    request_token = request.form['token']
    if request_token == TOKEN:
        new_draft_code = setup_draft(request.form['user_name'])
        return (
            'Draft successfully created. Your draft ID is `{draft_id}`. '
            'Other players can use this code with the `/joindraft` command '
            'to join the draft.'
        ).format(draft_id=new_draft_code)


@app.route('/startdraft', methods=['POST'])
def start_draft():
    request_token = request.form['token']
    if request_token == TOKEN:
        draft_id = request.form['text']
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        setup_packs(draft_id)
    return 'Draft successfully started.'


@app.route('/joindraft', methods=['POST'])
def join_draft():
    request_token = request.form['token']
    if request_token == TOKEN:
        draft_id = request.form['text']
        if draft_id not in DRAFTS:
            return 'Draft does not exist.'
        player_name = request.form['user_name']
        add_player(player_name, draft_id)
        creator_name = get_creator(draft_id)
        # TODO: notify creator
    return (
        'Successfully joined draft `{draft_id}`. Please wait for `{creator}` '
        'begin the draft.'
    ).format(draft_id=draft_id, creator=creator_name)


@app.route('/leavedraft', methods=['POST'])
def leave_draft():
    request_token = request.form['token']
    if request_token == TOKEN:
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
    request_token = request.form['token']
    if request_token == TOKEN:
        if request.form['user_name'] != 'weston.odom':
            return 'This action is only available to admins.'
        draft_id = request.form['text']
        if draft_id == '':
            return 'You must provide a draft_id.'
        del DRAFTS[draft_id]
        return 'Draft `{draft_id}` successfully deleted.'.format(
            draft_id=draft_id
        )


if __name__ == '__main__':
    app.run()
    # setup_packs('fsdf')
