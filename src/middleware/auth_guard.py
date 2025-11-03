from jose import JWTError

from sqlalchemy.orm import Session
from fastapi import Depends, status, APIRouter, WebSocket, HTTPException
from typing import Optional, Tuple

from middleware.auth_headers import user_token_header, auth_token_header
from schemas.Token import TokenData
from schemas.User import UserSchema
from schemas.UserAuthentication import UserAuthentication
from entities.User import User
from entities.Apikeys import ApiKeys
from exceptions.CwHTTPException import CwHTTPException
from database.postgres_db import get_db
from adapters.AdapterConfig import get_adapter

from utils.common import is_empty, is_not_empty, is_false
from utils.date import is_expired
from utils.flag import is_flag_enabled
from utils.jwt import jwt_decode
from utils.logger import log_msg
from utils.observability.cid import get_current_cid

router = APIRouter()
CACHE_ADAPTER = get_adapter('cache')

def is_mock_test():
    return False

def get_mock_current_user():
    return None

async def get_mem_user_token(user_token):
    decoded_user = jwt_decode(user_token)
    email: str = decoded_user.get("email")
    log_msg("DEBUG", "[auth_guard][get_mem_user_token] decoded_user = {}".format(decoded_user))
    return CACHE_ADAPTER().get(email), TokenData(email = email)

async def get_user_authentication(user_token: str = Depends(user_token_header), auth_token: str = Depends(auth_token_header)):
    if is_not_empty(user_token):
        user_auth = UserAuthentication(is_authenticated = True, header_key = "X-User-Token", header_value = user_token)
        return { "is_authenticated": True, "header_key": "X-User-Token", "header_value": user_token }
    elif is_not_empty(auth_token):
        user_auth = UserAuthentication(is_authenticated = True, header_key = "X-Auth-Token", header_value = auth_token)
    else:
        user_auth = UserAuthentication(is_authenticated = False)
    return user_auth

async def get_current_not_mandatory_user(user_token: str = Depends(user_token_header), auth_token: str = Depends(auth_token_header), db: Session = Depends(get_db)):
        user = None
        if is_mock_test():
            current_user = get_mock_current_user()
            return current_user
        if is_not_empty(user_token):
            try:
                decoded_mem_token, token_data = await get_mem_user_token(user_token)
                if not decoded_mem_token:
                    log_msg("DEBUG", "[auth_guard][get_current_not_mandatory_user] mem_user_token is not defined")
                    return None
                if decoded_mem_token != user_token:
                    log_msg("DEBUG", "[auth_guard][get_current_not_mandatory_user] decoded_mem_token != user_token")
                    return None
                user = User.getUserByEmail(token_data.email, db)
            except JWTError as e:
                log_msg("DEBUG", "[auth_guard][get_current_not_mandatory_user] e.type = {}, e.msg = {}".format(type(e), e))
                return None
        elif is_not_empty(auth_token):
            secret_key = auth_token
            user_api_key = ApiKeys.getApiKeyBySecretKey(secret_key, db)
            if is_empty(user_api_key):
                log_msg("DEBUG", "[auth_guard][get_current_not_mandatory_user] user_api_key is not set")
                return None

            user = User.getUserById(user_api_key.user_id, db)
        else:
            log_msg("DEBUG", "[auth_guard][get_current_not_mandatory_user] auth_token is not set")
            return None

        if is_empty(user):
            log_msg("DEBUG", "[auth_guard][get_current_not_mandatory_user] user is not found")
            return None

        return user

async def get_current_user(user_token: str = Depends(user_token_header), auth_token: str = Depends(auth_token_header), db: Session = Depends(get_db)):
        user = None
        if is_mock_test():
            current_user = get_mock_current_user()
            return current_user

        if is_not_empty(user_token):
            try:
                decoded_mem_token, token_data = await get_mem_user_token(user_token)
                if not decoded_mem_token:
                    raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)
                if decoded_mem_token != user_token:
                    raise CwHTTPException(message = {"status": "ko", "error": "authentification failed 2", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)

                user = User.getUserByEmail(token_data.email, db)
            except JWTError:
                raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)
        elif is_not_empty(auth_token):
            secret_key = auth_token
            user_api_key = ApiKeys.getApiKeyBySecretKey(secret_key, db)
            if is_empty(user_api_key):
                raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)
            user = User.getUserById(user_api_key.user_id, db)
        else:
            raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)

        if is_empty(user):
            raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)

        return user

async def get_current_active_user(current_user: UserSchema = Depends(get_current_user)):
    if is_false(current_user.confirmed):
        raise CwHTTPException(message = {"status": "ko", "error": "your account has not been confirmed yet", "i18n_code": "account_not_confirmed", "cid": get_current_cid()}, status_code = status.HTTP_403_FORBIDDEN)

    if is_flag_enabled(current_user.enabled_features, 'block'):
        raise CwHTTPException(message = {"status": "ko", "error": "your account has been blocked", "i18n_code": "blocked_account", "cid": get_current_cid()}, status_code = status.HTTP_403_FORBIDDEN)

    return current_user

async def admin_required(current_user: UserSchema = Depends(get_current_active_user)):
    if is_false(current_user.is_admin):
        raise CwHTTPException(message = {"status": "ko", "error": "permission denied", "i18n_code": "permission_denied", "cid": get_current_cid()}, status_code = status.HTTP_403_FORBIDDEN)
    return current_user

def _ws_subprotocol_token(websocket: WebSocket) -> Tuple[Optional[str], Optional[str]]:
    raw = websocket.headers.get("sec-websocket-protocol")
    if not raw:
        return None, None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) >= 2 and parts[0].lower() in ("bearer", "token", "jwt"):
        return parts[1], parts[0]
    return None, None

def _ws_query_user_token(websocket: WebSocket) -> Optional[str]:
    try:
        return websocket.query_params.get("x_user_token")
    except Exception:
        return None

def _ws_bearer(websocket: WebSocket) -> Optional[str]:
    auth = websocket.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None

def _ws_x_user(websocket: WebSocket) -> Optional[str]:
    x = websocket.headers.get("x-user-token")
    return x.strip() if x else None

def _ws_x_auth(websocket: WebSocket) -> Optional[str]:
    x = websocket.headers.get("x-auth-token")
    return x.strip() if x else None

async def _get_mem_user_token(user_token: str):
    decoded = jwt_decode(user_token)
    email: str = decoded.get("email")
    log_msg("DEBUG", f"[auth_ws] decoded_user={decoded}")
    from adapters.AdapterConfig import get_adapter
    CACHE_ADAPTER = get_adapter('cache')
    return CACHE_ADAPTER().get(email), TokenData(email=email)

async def get_current_user_ws(websocket: WebSocket, db: Session = Depends(get_db)) -> User:
    log_msg("DEBUG", f"[auth_ws] headers={dict(websocket.headers)}")
    user_token = _ws_bearer(websocket) or _ws_x_user(websocket)
    auth_token = _ws_x_auth(websocket)
    proto_token, proto_to_echo = _ws_subprotocol_token(websocket)
    query_token = _ws_query_user_token(websocket)
    user_token = user_token or proto_token or query_token
    websocket.state.ws_subprotocol = proto_to_echo
    user: Optional[User] = None
    try:
        if is_not_empty(user_token):
            decoded_mem_token, token_data = await _get_mem_user_token(user_token)
            if not decoded_mem_token:
                raise CwHTTPException(message={"status": "ko", "error": "authentication failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code=status.HTTP_401_UNAUTHORIZED)
            if decoded_mem_token != user_token:
                raise CwHTTPException(message={"status": "ko", "error": "authentication failed 2", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code=status.HTTP_401_UNAUTHORIZED)
            user = User.getUserByEmail(token_data.email, db)
        elif is_not_empty(auth_token):
            user_api_key = ApiKeys.getApiKeyBySecretKey(auth_token, db)
            if is_empty(user_api_key):
                raise CwHTTPException(message={"status": "ko", "error": "authentication failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code=status.HTTP_401_UNAUTHORIZED)
            if is_expired(user_api_key.expiration_date):
                raise CwHTTPException(message={"status": "ko", "error": "api key has expired", "i18n_code": "api_key_expired", "cid": get_current_cid()}, status_code=status.HTTP_401_UNAUTHORIZED)
            user = User.getUserById(user_api_key.user_id, db)
        else:
            raise CwHTTPException(message={"status": "ko", "error": "authentication failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code=status.HTTP_401_UNAUTHORIZED)
        if is_empty(user):
            raise CwHTTPException(message={"status": "ko", "error": "authentication failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code=status.HTTP_401_UNAUTHORIZED)
        return user
    except CwHTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

async def get_current_active_user_ws(current_user: User = Depends(get_current_user_ws)) -> User:
    try:
        if is_false(current_user.confirmed):
            raise CwHTTPException(message={"status": "ko", "error": "your account has not been confirmed yet", "i18n_code": "account_not_confirmed", "cid": get_current_cid()}, status_code=status.HTTP_403_FORBIDDEN)
        return current_user
    except CwHTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

async def admin_required_ws(current_user: User = Depends(get_current_active_user_ws)) -> User:
    try:
        if is_false(current_user.is_admin):
            raise CwHTTPException(message={"status": "ko", "error": "permission denied", "i18n_code": "permission_denied", "cid": get_current_cid()}, status_code=status.HTTP_403_FORBIDDEN)
        return current_user
    except CwHTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
