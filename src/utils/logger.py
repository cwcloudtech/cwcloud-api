import os
import requests
import logging
import json
import sys

from datetime import datetime

from utils.http import HTTP_REQUEST_TIMEOUT
from utils.observability.cid import get_current_cid
from utils.common import get_env_bool, is_disabled, is_enabled

SLACK_WEBHOOK_TPL = "https://hooks.slack.com/services/{}"
DISCORD_WEBHOOK_TPL = "https://discord.com/api/webhooks/{}/slack"


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT')

_slack_token = os.getenv('SLACK_TOKEN')
_slack_public_token = os.getenv('SLACK_TOKEN_PUBLIC')

_discord_token = os.getenv('DISCORD_TOKEN')
_discord_public_token = os.getenv('DISCORD_TOKEN_PUBLIC')

_slack_channel = os.getenv('SLACK_CHANNEL', '#cloud')
_slack_emoji = os.getenv('SLACK_EMOJI', ':cwcloud:')
_username = os.getenv('SLACK_USERNAME', 'cwcloud')

if is_disabled(_username):
    _username = os.getenv('DISCORD_USERNAME')

if is_disabled(_username):
    _username = "logger"

def slack_message(log_level, message, is_public):
    token = _slack_token
    if is_public and is_enabled(_slack_public_token):
        if is_enabled(token):
            slack_message(log_level, message, False)
        token = _slack_public_token

    if is_enabled(token):
        data = { "attachments": [{ "color": get_color_level(log_level), "text": message, "title": log_level }], "username": _username, "channel": _slack_channel, "icon_emoji": _slack_emoji }
        try:
            requests.post(SLACK_WEBHOOK_TPL.format(token), json=data, timeout=HTTP_REQUEST_TIMEOUT)
        except Exception as e:
            logging.warning("[slack_message] unexpected exception: {}".format(e))

def discord_message(log_level, message, is_public):
    token = _discord_token
    if is_public and is_enabled(_discord_public_token):
        if is_enabled(token):
            discord_message(log_level, message, False)
        token = _discord_public_token

    if is_enabled(token):
        data = { "attachments": [{ "color": get_color_level(log_level), "text": message, "title": log_level }], "username": _username }
        try:
            requests.post(DISCORD_WEBHOOK_TPL.format(token), json=data, timeout=HTTP_REQUEST_TIMEOUT)
        except Exception as e:
            logging.warning("[discord_message] unexpected exception: {}".format(e))

def is_level_partof(level, levels):
    return any(log == "{}".format(level).lower() for log in levels)

def is_debug(level):
    return is_level_partof(level, ["debug", "notice"])

def is_warn(level):
    return is_level_partof(level, ["warning", "warn"])

def is_error(level):
    return is_level_partof(level, ["error", "fatal", "crit"])

def get_color_level(level):
    if is_debug(level):
        return "#D4D5D7"
    elif is_warn(level):
        return "#FDCB94"
    elif is_error(level):
        return "#D80020"
    else:
        return "#95C8F3"

def get_int_value_level(level):
    if is_debug(level):
        return 0
    elif is_warn(level):
        return 2
    elif is_error(level):
        return 3
    else:
        return 1

if is_debug(LOG_LEVEL):
    logging.basicConfig(stream = sys.stdout, level = "DEBUG")
elif is_warn(LOG_LEVEL):
    logging.basicConfig(stream = sys.stdout, level = "WARNING")
elif is_error(LOG_LEVEL):
    logging.basicConfig(stream = sys.stderr, level = "ERROR")
else:
    logging.basicConfig(stream = sys.stdout, level = "INFO")

def quiet_log_msg (log_level, message):
    vdate = datetime.now().isoformat()
    cid = get_current_cid()

    formatted_log = "[{}][{}][{}] {}".format(log_level, vdate, cid, message)
    if is_enabled(LOG_FORMAT) and LOG_FORMAT == "json":
        if isinstance(message, dict):
            message['level'] = log_level
            message['time'] = vdate
            message['cid'] = cid
            formatted_log = json.dumps(message)
        else:
            formatted_log = json.dumps({"body": message, "level": log_level, "time": vdate, "cid": cid })

    if is_debug(log_level):
        logging.debug(formatted_log)
    elif is_warn(log_level):
        logging.warning(formatted_log)
    elif is_error(log_level):
        logging.error(formatted_log)
    else:
        logging.info(formatted_log)

    return formatted_log

def is_notif_enabled():
    notifs_providers = ['SLACK', 'DISCORD']
    return any(get_env_bool("{}_TRIGGER".format(n)) for n in notifs_providers)

def log_msg(log_level, message, is_public = False):
    formated_log = quiet_log_msg (log_level, message)

    if get_int_value_level(log_level) >= get_int_value_level(LOG_LEVEL) and is_notif_enabled():
        slack_message(log_level, formated_log, is_public)
        discord_message(log_level, formated_log, is_public)
