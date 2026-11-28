import json
from datetime import datetime

from fastapi.responses import JSONResponse

from entities.Apikeys import ApiKeys
from entities.User import User
from utils.api_keys import generate_apikey_access_key, generate_apikey_secret_key
from utils.common import is_empty, is_not_empty
from utils.encoder import AlchemyEncoder
from utils.logger import log_msg
from utils.observability.cid import get_current_cid


def _ko(error, i18n_code, http_code):
    return JSONResponse(content = {
        'status': 'ko',
        'error': error,
        'i18n_code': i18n_code,
        'cid': get_current_cid()
    }, status_code = http_code)


def create_api_key_for_user(user_id, payload, db):
    """Generate a key pair for `user_id` (a user for himself, or an admin for
    another user). Returns the created key, secret included: it's the only time
    it's shown in full."""
    if is_empty(payload.name):
        return _ko('please provide a name for the api key', 'invalid_api_key', 400)

    while True:
        access_key = generate_apikey_access_key()
        if not ApiKeys.getApiKeysByAccessKey(access_key, db):
            break

    while True:
        secret_key = generate_apikey_secret_key()
        if not ApiKeys.getApiKeysBySecretKey(secret_key, db):
            break

    api_key = ApiKeys(name = payload.name)
    api_key.access_key = access_key
    api_key.secret_key = secret_key
    api_key.user_id = user_id
    api_key.created_at = datetime.now().isoformat()
    api_key.save(db)

    api_key_json = json.loads(json.dumps(api_key, cls = AlchemyEncoder))
    api_key_json["id"] = api_key.id
    return JSONResponse(content = api_key_json, status_code = 201)


def _admin_key_dict(key, email):
    return {
        "id": key.id,
        "name": key.name,
        "user_id": key.user_id,
        "email": email,
        "created_at": key.created_at
    }


def admin_create_api_key(current_user, payload, db):
    target_user = User.getUserByEmail(payload.email, db) if is_not_empty(payload.email) else None
    if is_empty(target_user):
        return _ko('user not found', 'user_not_found', 404)
    response = create_api_key_for_user(target_user.id, payload, db)
    if response.status_code == 201:
        log_msg("INFO", f"[api_keys][admin] {current_user.email} created the api key '{payload.name}' for {target_user.email}")
    return response


def admin_get_api_keys(db, user_id = None):
    keys = ApiKeys.getUserApiKeys(user_id, db) if is_not_empty(user_id) else ApiKeys.getAllApiKeys(db)
    emails = {}
    result = []
    for key in keys:
        if key.user_id not in emails:
            user = User.getUserById(key.user_id, db)
            emails[key.user_id] = user.email if is_not_empty(user) else None
        result.append(_admin_key_dict(key, emails[key.user_id]))
    return JSONResponse(content = {'status': 'ok', 'api_keys': result}, status_code = 200)


def admin_get_api_key_value(key_id, db):
    key = ApiKeys.getApiKeyById(key_id, db)
    if is_empty(key):
        return _ko('api key not found', 'api_key_not_found', 404)
    return JSONResponse(content = {'status': 'ok', 'value': key.secret_key}, status_code = 200)


def admin_delete_api_key(current_user, key_id, db):
    key = ApiKeys.getApiKeyById(key_id, db)
    if is_empty(key):
        return _ko('api key not found', 'api_key_not_found', 404)
    ApiKeys.deleteUserApiKey(key.user_id, key.id, db)
    log_msg("INFO", f"[api_keys][admin] {current_user.email} deleted the api key #{key.id} '{key.name}' of user #{key.user_id}")
    return JSONResponse(content = {
        'status': 'ok',
        'message': 'api key successfully deleted',
        'i18n_code': 'api_key_deleted'
    }, status_code = 200)
