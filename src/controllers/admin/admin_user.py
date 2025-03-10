import json

from urllib.error import HTTPError
from fastapi.responses import JSONResponse

from datetime import datetime, timedelta

from entities.Apikeys import ApiKeys
from entities.faas.Function import FunctionEntity
from entities.faas.Trigger import TriggerEntity
from entities.faas.Invocation import InvocationEntity
from entities.iot.Device import Device
from entities.User import User

from utils.common import is_false, is_numeric, generate_hash_password
from utils.env_vars import DOMAIN
from utils.flag import is_flag_enabled
from utils.jwt import jwt_encode
from utils.logger import log_msg
from utils.mail import send_confirmation_email
from utils.paginator import get_paginated_list
from utils.gitlab import create_gitlab_user
from utils.encoder import AlchemyEncoder
from utils.security import check_password, is_not_email_valid
from utils.observability.cid import get_current_cid

def admin_delete_user_2fa(current_user, userId, db):
    if not is_numeric(userId):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid user id',
            'i18n_code': 'invalid_numeric_id',
            'cid': get_current_cid()
        }, status_code = 400)

    user = User.getUserById(userId, db)
    if not user:
        return JSONResponse(content = {
            'status': 'ko',
            'message' : 'user not found', 
            'i18n_code': 'user_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
        
    from entities.Mfa import Mfa        
    mfa_methods = Mfa.getUserMfaMethods(user.id, db)
    if not mfa_methods:
        return JSONResponse(content = {
            'status': 'ko',
            'message' : 'user has no 2fa methods', 
            'i18n_code': 'user_no_2fa_methods',
            'cid': get_current_cid()
        }, status_code = 404)

    Mfa.deleteUserMethods(userId, db)
    return JSONResponse(content = {
        'status': 'ok',
        'message': '2fa successfully deleted',
        'i18n_code': '2fa_deleted'
    }, status_code = 200)

def admin_update_user(current_user, userId, payload, db):
    email = payload.email
    if is_not_email_valid(email):
        return JSONResponse(content = {
            'status': 'ko',           
            'error': 'the email is not valid', 
            'i18n_code': 'invalid_email',
            'cid': get_current_cid()
        }, status_code = 400)

    exisUser = User.getUserByEmail(email, db)
    if exisUser and int(exisUser.id) != int(userId):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'email already exists', 
            'i18n_code': 'email_exist',
            'cid': get_current_cid()
        }, status_code = 409)

    User.adminUpdateUser(userId, payload, db)
    return JSONResponse(content = {
        'status': 'ok',        
        'message': 'user successfully updated', 
        'i18n_code': 'user_updated'
    }, status_code = 200)

def admin_remove_user(current_user, userId, db):
    if not is_numeric(userId):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid user id', 
            'i18n_code': 'invalid_numeric_id'
        }, status_code = 400)

    user = User.getUserById(userId, db)
    if not user:
        return JSONResponse(content = {
            'status': 'ko',
            'message' : 'user not found', 
            'i18n_code': 'user_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    ApiKeys.deleteUserAllApiKeys(user.id, db)

    first_admin_user = User.getFirstAdminUser(db)
    if first_admin_user:
        FunctionEntity.transferAllFunctionsOwnership(userId, first_admin_user.id, db)
        TriggerEntity.transferAllTriggersOwnership(userId, first_admin_user.id, db)
        InvocationEntity.transferAllInvocationsOwnership(userId, first_admin_user.id, db)
        Device.transferAllDevicesOwnership(user.email, first_admin_user.email, db)
    User.deleteUserById(user.id, db)

    return JSONResponse(content = {
        'status': 'ok',
        'message' : 'user successfully deleted', 
        'i18n_code': 'user_deleted'
    }, status_code = 200)

def admin_update_user_confirmation(current_user, userId, db):
    if not is_numeric(userId):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid user id', 
            'i18n_code': 'invalid_numeric_id',
            'cid': get_current_cid()
        }, status_code = 400)

    user = User.getUserById(userId, db)
    if not user:
        return JSONResponse(content = {
            'status': 'ko',
            'message' : 'user not found', 
            'i18n_code': 'user_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    User.updateConfirmation(user.id, not user.confirmed, db)
    return JSONResponse(content = {
        'status': 'ok',
        'message' : 'user successfully confirmed', 
        'i18n_code': 'user_confirmed'
    }, status_code = 200)

def admin_update_user_role(current_user, userId, payload, db):
    is_admin = payload.is_admin
    if not is_numeric(userId):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid user id', 
            'i18n_code': 'invalid_numeric_id',
            'cid': get_current_cid()
        }, status_code = 400)

    user = User.getUserById(userId, db)
    if not user:
        return JSONResponse(content = {
            'status': 'ko',
            'message' : 'user not found', 
            'i18n_code': 'user_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    User.updateUserRole(user.id, is_admin, db)
    return JSONResponse(content = {
        'status': 'ok',
        'message' : 'user successfully updated', 
        'i18n_code': 'user_updated'
    }, status_code = 200)

def admin_add_user(current_user, payload, db):
    try:
        email = payload.email
        password = payload.password

        if is_not_email_valid(email):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'the email is not valid', 
                'i18n_code': 'not_valid_email',
                'cid': get_current_cid()
            }, status_code = 400)

        check = check_password(password)
        if is_false(check['status']):
            return JSONResponse(content = {
                'status': 'ko', 
                'error': 'the password is invalid', 
                'i18n_code': check['i18n_code'],
                'cid': get_current_cid()
            }, status_code = 400)

        exist_user = User.getUserByEmail(email, db)
        if exist_user:
            return JSONResponse(content = {
                'status': 'ko', 
                'error': 'email already exists', 
                'i18n_code': 'email_exist',
                'cid': get_current_cid()
            }, status_code = 409)

        payload.password = generate_hash_password(password)
        new_user = User(**payload.dict())
        new_user.save(db)

        create_gitlab_user(email)

        if is_flag_enabled(payload.enabled_features, 'disable_emails'):
            return JSONResponse(content = {
                'status': 'ok', 
                'message': 'user successfully created', 
                'i18n_code': 'user_created'
            }, status_code = 200)

        subject = "Confirm your account"
        token = jwt_encode({
            'exp': (datetime.now() + timedelta(minutes = 5)).timestamp(),
            'id': new_user.id,
            'email': new_user.email,
            'time': datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        })
        activation_link = '{}/confirmation/{}'.format(DOMAIN, token)
        log_msg("INFO", f"[api_admin_user_register] User {email} has joined comwork cloud")
        send_confirmation_email(new_user.email, activation_link, subject)

        return JSONResponse(content = {
            'status': 'ok', 
            'message': 'user successfully created', 
            'id': new_user.id, 
            'i18n_code': 'user_created'
        }, status_code = 201)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko', 
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def admin_get_users(current_user, no_per_page, page, db):
    users = User.getAllUsers(db)
    users_per_page = no_per_page
    _page = page
    if _page and users_per_page:
        _page = int(_page)
        users_per_page = int(no_per_page)
        pages = get_paginated_list(users, "/user", _page, users_per_page)
        return JSONResponse(content = {"result": pages}, status_code = 200)

    return JSONResponse(content = {"result": users}, status_code = 200)

def admin_get_user(current_user, userId, db):
    if not is_numeric(userId):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid user id', 
            'i18n_code': 'invalid_numeric_id',
            'cid': get_current_cid()
        }, status_code = 400)

    user = User.getUserById(userId, db)
    userJson = json.loads(json.dumps(user, cls = AlchemyEncoder))
    return JSONResponse(content = {
        'status': 'ok',
        'result': userJson
    }, status_code = 200)
