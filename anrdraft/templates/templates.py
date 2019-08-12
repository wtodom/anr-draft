import json


def identity_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Text*: {text}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        text=card.get('text', 'none')
    )


def agenda_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Agenda Points*: {agenda_points}\n'
        '*Advancement Requirement*: {adv_req}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        agenda_points=card.get('agenda_points', 'none'),
        adv_req=card.get('advancement_cost', 'none'),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def asset_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Rez Cost*: {rez_cost}\n'
        '*Trash Cost*: {trash_cost}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        rez_cost=str(card.get('cost', 'none')),
        trash_cost=str(card.get('trash_cost', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def ice_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Rez Cost*: {rez_cost}\n'
        '*Strength*: {strength}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        rez_cost=str(card.get('cost', 'none')),
        strength=str(card.get('strength', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def operation_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Play Cost*: {play_cost}\n'
        '*Trash Cost*: {trash_cost}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        play_cost=str(card.get('cost', 'none')),
        trash_cost=str(card.get('trash_cost', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def upgrade_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Rez Cost*: {rez_cost}\n'
        '*Trash Cost*: {trash_cost}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        rez_cost=str(card.get('cost', 'none')),
        trash_cost=str(card.get('trash_cost', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def event_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Play Cost*: {play_cost}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        play_cost=str(card.get('cost', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def hardware_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Install Cost*: {install_cost}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        install_cost=str(card.get('cost', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def program_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Install Cost*: {install_cost}\n'
        '*Memory*: {memory_cost}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        install_cost=str(card.get('cost', 'none')),
        memory_cost=str(card.get('memory_cost', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def resource_text(card):
    return (
        '*Name*: {name}\n'
        '*Type*: {type}\n'
        '*Subtype*: {subtype}\n'
        '*Install Cost*: {install_cost}\n'
        '*Text*: {text}\n'
        '*Faction*: {faction}'
    ).format(
        name=card.get('title', 'none'),
        type=card.get('type_code', 'none').title(),
        subtype=card.get('keywords', 'none'),
        install_cost=str(card.get('cost', 'none')),
        text=card.get('text', 'none'),
        faction=card.get('faction_code', 'none').title()
    )


def format(card):
    card_type = card.get('type_code', 'none')

    if card_type == 'identity':
        return identity_text(card)
    elif card_type == 'agenda':
        return agenda_text(card)
    elif card_type == 'asset':
        return asset_text(card)
    elif card_type == 'ice':
        return ice_text(card)
    elif card_type == 'operation':
        return operation_text(card)
    elif card_type == 'upgrade':
        return upgrade_text(card)
    elif card_type == 'event':
        return event_text(card)
    elif card_type == 'hardware':
        return hardware_text(card)
    elif card_type == 'program':
        return program_text(card)
    elif card_type == 'resource':
        return resource_text(card)
    else:
        return '```' + json.dumps(card, indent=4, sort_keys=True) + '```'
