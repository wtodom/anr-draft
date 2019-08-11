import json


def card_text(text_string):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "{text}".format(text=text_string)
        }
    }


def card_image(url, text):
    return {
        "type": "image",
        "title": {
            "type": "plain_text",
            "text": "{text}".format(text=text),
                "emoji": True
        },
        "image_url": "{url}".format(url=url),
        "alt_text": "{alt_text}".format(alt_text=text)
    }


def pick_button(value):
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                        "emoji": True,
                        "text": "Pick"
                },
                "style": "primary",
                "value": "{value}".format(value=value)
            }
        ]
    }


def divider():
    return {
        "type": "divider"
    }


def text_with_button(text_string, button_value):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "{text}".format(text=text_string)
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                    "text": "Pick " + button_value,
                    "emoji": True
            },
            "style": "primary",
            "value": "{value}".format(value=button_value)
        }
    }
