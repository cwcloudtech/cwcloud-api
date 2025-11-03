import json

from datetime import datetime
from fastapi import Request, Depends, APIRouter
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from adapters.AdapterConfig import get_adapter
from schemas.User import UserLoginSchema
from database.postgres_db import get_db
from utils.jwt import jwt_encode

from utils.logger import log_msg
from utils.common import get_env_int, verify_password
from utils.flag import is_flag_enabled
from utils.encoder import AlchemyEncoder
from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method
from utils.observability.tracker import track_log

router = APIRouter()
CACHE_ADAPTER = get_adapter('cache')

_span_prefix = "login"
_counter = create_counter("auth_api", "Auth API counter")

@router.post("/login")
def login_user(request: Request, payload: UserLoginSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        from entities.User import User
        email = payload.email
        password = payload.password

        track_log(request, "login_user", email)

        if not payload or not email or not password:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Missing informations for login',
                'i18n_code': 'missing_info_for_login',
                'cid': get_current_cid()
            }, status_code = 403)

        user = User.getUserByEmail(email, db)
        if not user:
            log_msg("WARN", "User {} try to authenticate but it not exists".format(email))
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Authentification failed',
                'i18n_code': 'auth_failed',
                'cid': get_current_cid()
            }, status_code = 403)

        from entities.Mfa import Mfa
        mfaMethods = Mfa.getUserMfaMethods(user.id, db)
        if verify_password(password, user.password):
            token = jwt_encode({
                "id": user.id,
                "email": user.email,
                "confirmed": user.confirmed,
                "is_admin": user.is_admin,
                "emailapi": is_flag_enabled(user.enabled_features, 'emailapi'),
                "cwaiapi": is_flag_enabled(user.enabled_features, 'cwaiapi'),
                "verified": "true" if len(mfaMethods) == 0 else "false",
                "time": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            })
            CACHE_ADAPTER().delete(user.email)
            CACHE_ADAPTER().put(user.email, token, get_env_int("TOKEN_EXPIRATION_TIME"))
            from entities.Mfa import Mfa
            mfaMethods = Mfa.getUserMfaMethods(user.id, db)
            mfaMethodsJson = json.loads(json.dumps(mfaMethods, cls = AlchemyEncoder))
            log_msg("INFO", "User {} successfully authenticated".format(user.email))
            return JSONResponse(content = {
                'status': 'ok',
                'token': token,
                'confirmed': user.confirmed,
                'methods': mfaMethodsJson
            }, status_code = 200)

        log_msg("WARN", "User {} fails to authenticate".format(user.email))
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Authentification failed',
            'i18n_code': 'auth_failed',
            'cid': get_current_cid()
        }, status_code = 403)
