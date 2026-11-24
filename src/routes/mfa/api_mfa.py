import os
import json
import pyotp

from datetime import datetime
from urllib.error import HTTPError
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse
from utils.common import get_env_int
from yubico_client import Yubico

from entities.Mfa import Mfa
from schemas.User import UserSchema
from schemas.MFA import MFASchema, MFARegister2faSchema
from database.postgres_db import get_db
from adapters.AdapterConfig import get_adapter
from middleware.pre_auth_guard import pre_token_required
from middleware.auth_guard import get_current_active_user

from utils.encoder import AlchemyEncoder
from utils.flag import is_flag_enabled
from utils.jwt import jwt_encode
from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()
CACHE_ADAPTER = get_adapter('cache')

YUBICO_CLIENT_ID = os.getenv("YUBICO_CLIENT_ID")
YUBICO_SECRET_KEY = os.getenv("YUBICO_SECRET_KEY")

_span_prefix = "mfa"
_counter = create_counter("mfa_api", "MFA API counter")

@router.get("")
def get_MFA_methods(current_user: Annotated[UserSchema, Depends(get_current_active_user)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.ALL)):
        increment_counter(_counter, Method.GET, Action.ALL)
        try:
            mfaMethods = Mfa.getUserMfaMethods(current_user.id, db)
            mfaMethodsJson = json.loads(json.dumps(mfaMethods, cls = AlchemyEncoder))
            return JSONResponse(content = {
                'status': 'ok',
                'methods': mfaMethodsJson
            }, status_code = 200)
        except HTTPError as e:
            return JSONResponse(content = {
                'status': 'ko',
                'error': e.msg,
                'i18n_code': e.headers['i18n_code'],
                'cid': get_current_cid()
            }, status_code = e.code)

@router.delete("")
def delete_user_methods(current_user: Annotated[UserSchema, Depends(get_current_active_user)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE, Action.ALL)):
        increment_counter(_counter, Method.DELETE, Action.ALL)
        Mfa.deleteUserMethods(current_user.id, db)
        return JSONResponse(content = {
            'status': 'ok',
            'message': '2fa successfully deleted'
        }, status_code = 200)

@router.delete("/{method_id}")
def delete_MFA(current_user: Annotated[UserSchema, Depends(get_current_active_user)], method_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        try:
            method = Mfa.findOne(method_id, db)
            if not method:
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': '2fa method not found',
                    'i18n_code': '2fa_method_not_found',
                    'cid': get_current_cid()
                }, status_code = 404)
            Mfa.deleteOne(method.id, db)
            return JSONResponse(content = {
                'status': 'ok',
                'message': 'successfully deleted mfa method'
            }, status_code = 200)
        except HTTPError as e:
            return JSONResponse(content = {
                'status': 'ko',
                'error': e.msg,
                'i18n_code': e.headers['i18n_code'],
                'cid': get_current_cid()
            }, status_code = e.code)

@router.post("/register/u2f")
def register_u2f(current_user: Annotated[UserSchema, Depends(get_current_active_user)], payload: MFASchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST, Action.REGISTER)):
        increment_counter(_counter, Method.POST, Action.REGISTER)
        try:
            code = payload.code
            yubico = Yubico(YUBICO_CLIENT_ID, YUBICO_SECRET_KEY)
            yubico.verify(code)
            key_id = code[0:12]
            user2faMethods = Mfa.getUserMfaMethodsByType(current_user.id, "security_key", db)
            if len(user2faMethods)>0:
                return JSONResponse(content = {
                    'status': 'ok',
                    'message': 'u2f already added'
                }, status_code = 400)
            else:
                new_method = Mfa()
                new_method.user_id = current_user.id
                new_method.type = "security_key"
                new_method.otp_code = key_id
                new_method.save(db)
            mfaMethodsJson = json.loads(json.dumps(new_method, cls = AlchemyEncoder))
            return JSONResponse(content = {
                'status': 'ok',
                'method': mfaMethodsJson
            }, status_code = 200)
        except Exception as e:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid code',
                'i18n_code': 'invalid_code',
                'cid': get_current_cid()
            }, status_code = 400)

@router.post("/u2f/verify")
def verify_u2f(current_user: Annotated[UserSchema, Depends(pre_token_required)], payload: MFASchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST, Action.VERIFY)):
        increment_counter(_counter, Method.POST, Action.VERIFY)
        try:
            code = payload.code
            yubico = Yubico(YUBICO_CLIENT_ID, YUBICO_SECRET_KEY)
            yubico.verify(code)
            key_id = code[0:12]
            user2faMethod = Mfa.getUserMfaMethod(current_user.id, "security_key", db)

            if key_id != user2faMethod.otp_code:
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'Invalid code',
                    'i18n_code': 'invalid_code',
                    'cid': get_current_cid()
                }, status_code = 400)

            token = jwt_encode({
                "id": current_user.id,
                "email": current_user.email,
                "confirmed": current_user.confirmed,
                "is_admin": current_user.is_admin,
                "emailapi": is_flag_enabled(current_user.enabled_features, 'emailapi'),
                "cwaiapi": is_flag_enabled(current_user.enabled_features, 'cwaiapi'),
                "verified": "true",
                "time": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            })
            CACHE_ADAPTER().delete(current_user.email)
            CACHE_ADAPTER().put(current_user.email, token, get_env_int("TOKEN_EXPIRATION_TIME"))
            return JSONResponse(content = {
                'status': 'ok',
                'token': token
            }, status_code = 200)
        except Exception as e:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid code',
                'i18n_code': 'invalid_code',
                'cid': get_current_cid()
            }, status_code = 400)

@router.get("/register/2fa")
def get_2fa(current_user: Annotated[UserSchema, Depends(get_current_active_user)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST, Action.REGISTER)):
        increment_counter(_counter, Method.POST, Action.REGISTER)
        found = True
        random_code = ""
        while found:
            random_code = pyotp.random_base32()
            user2faMethods = Mfa.getUserMfaMethodsByType(current_user.id, "auth_app", db)
            users = Mfa.getUserByOtpCode(random_code, db)
            if len(users) == 0:
                found = False
        otp = pyotp.TOTP(random_code)
        issuer_name = "{} cloud".format(os.getenv("COMPANY_NAME"))
        auth_uri = otp.provisioning_uri(name = current_user.email, issuer_name = issuer_name)
        if len(user2faMethods)>0:
            JSONResponse(content = {
                'status': 'ko',
                'error': 'authentification method already exits',
                'cid': get_current_cid()
            }, status_code = 400)

        return JSONResponse(content = {
            'status': 'ok',
            'auth_uri': auth_uri,
            'otp_code': random_code
        }, status_code = 200)

@router.patch("/register/2fa")
def register_2fa(current_user: Annotated[UserSchema, Depends(get_current_active_user)], payload: MFARegister2faSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PATCH, Action.REGISTER)):
        increment_counter(_counter, Method.PATCH, Action.REGISTER)
        code = payload.code
        otp_code = payload.otp_code
        user2faMethod = Mfa.getUserMfaMethod(current_user.id, "auth_app", db)
        if user2faMethod:
            return JSONResponse(content = {
                'status': 'ok',
                'message': '2fa already added'
            }, status_code = 400)

        otp = pyotp.TOTP(otp_code)
        if str(otp.now()) == str(code):
            new_method = Mfa()
            new_method.user_id = current_user.id
            new_method.type = "auth_app"
            new_method.otp_code = otp_code
            new_method.save(db)
            mfaMethodsJson = json.loads(json.dumps(new_method, cls = AlchemyEncoder))
            return JSONResponse(content = {
                'status': 'ok',
                'message': '2fa activated', 
                'method': mfaMethodsJson
            }, status_code = 200)
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'failed',
            'cid': get_current_cid()
        }, status_code = 400)

@router.post("/2fa/verify")
def post(current_user: Annotated[UserSchema, Depends(pre_token_required)], payload: MFASchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST, Action.VERIFY)):
        increment_counter(_counter, Method.POST, Action.VERIFY)
        code = payload.code
        user2faMethod = Mfa.getUserMfaMethod(current_user.id, "auth_app", db)
        if not user2faMethod:
            return JSONResponse(content = {
                'status': 'ko',
                'error': '2fa method not found',
                'i18n_code': '2fa_method_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        otp = pyotp.TOTP(user2faMethod.otp_code)
        if str(otp.now()) != str(code):
            return JSONResponse(content = {
                'status': 'ko',
                'error': '2fa authentification failed',
                'i18n_code': 'invalid_code',
                'cid': get_current_cid()
            }, status_code = 400)

        token = jwt_encode({
            "id": current_user.id,
            "email": current_user.email,
            "confirmed": current_user.confirmed,
            "is_admin": current_user.is_admin,
            "emailapi": is_flag_enabled(current_user.enabled_features, 'emailapi'),
            "cwaiapi": is_flag_enabled(current_user.enabled_features, 'cwaiapi'),
            "verified": "true",
            "time": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        })
        CACHE_ADAPTER().delete(current_user.email)
        CACHE_ADAPTER().put(current_user.email, token, get_env_int("TOKEN_EXPIRATION_TIME"))
        return JSONResponse(content = {
            'status': 'ok',
            'token': token
        }, status_code = 200)
