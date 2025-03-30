from fastapi import Depends, status
from sqlalchemy.orm import Session

from adapters.AdapterConfig import get_adapter
from database.postgres_db import get_db
from entities.User import User
from schemas.Token import TokenData
from exceptions.CwHTTPException import CwHTTPException
from schemas.User import UserSchema
from middleware.auth_headers import user_token_header
from utils.common import is_empty, is_not_empty
from utils.flag import ALL_FLAGS, is_flag_enabled
from utils.jwt import jwt_decode
from utils.logger import log_msg
from utils.observability.cid import get_current_cid

CACHE_ADAPTER = get_adapter('cache')

def add_flag_if_not_present(key, decoded_user, user):
    if 'enabled_features' not in decoded_user:
        decoded_user['enabled_features'] = {}

    if key not in decoded_user['enabled_features']:
        decoded_user['enabled_features'][key] = is_flag_enabled(user.enabled_features, key)

def get_pre_current_user(user_token: str = Depends(user_token_header), db: Session = Depends(get_db)):
    user = None
    if is_not_empty(user_token):
        try:
            decoded_user = jwt_decode(user_token)
            email: str = decoded_user.get("email")
            token_data = TokenData(email = email)

            log_msg("DEBUG", "[pre_token_required] data = {}".format(decoded_user))
            decoded_mem_token = CACHE_ADAPTER().get(token_data.email)

            if not decoded_mem_token == user_token:
                raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)

            user = User.getUserByEmail(token_data.email, db)

            for flag in ALL_FLAGS:
                add_flag_if_not_present(flag, decoded_user, user)

        except Exception as ex:
            log_msg("ERROR", "[pre_token_required] unexpected error: type = {}, file = {}, lno = {}, msg = {}".format(type(ex).__name__, __file__, ex.__traceback__.tb_lineno, ex))
            raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)
    else:
        raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)
    if is_empty(user):
        raise CwHTTPException(message = {"status": "ko", "error": "authentification failed", "i18n_code": "auth_failed", "cid": get_current_cid()}, status_code = status.HTTP_401_UNAUTHORIZED)
    else:
        return user

async def pre_token_required(current_user: UserSchema = Depends(get_pre_current_user)):
    if is_empty(current_user.confirmed):
        raise CwHTTPException(message = {"status": "ko", "error": "your account has not been confirmed yet", "i18n_code": "account_not_confirmed", "cid": get_current_cid()}, status_code = status.HTTP_403_FORBIDDEN)
    return current_user
