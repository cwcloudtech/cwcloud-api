from fastapi import Depends, status
from sqlalchemy.orm import Session

from entities.User import User
from schemas.User import UserSchema
from exceptions.CwHTTPException import CwHTTPException
from database.postgres_db import get_db
from middleware.auth_guard import get_current_user

from utils.common import is_false, is_not_empty, is_true
from utils.flag import is_flag_enabled
from utils.observability.cid import get_current_cid

def emailapi_required(current_user: UserSchema = Depends(get_current_user), db: Session = Depends(get_db)):
    is_granted = is_not_empty(current_user) and is_true(current_user.is_admin)
    if is_false(is_granted) and is_not_empty(current_user):
        user = User.getUserByEmail(current_user.email, db)
        is_granted = is_flag_enabled(user.enabled_features, 'emailapi')

    if is_false(is_granted):
        raise CwHTTPException(message = {"status": "ko", "error": "permission denied", "i18n_code": "not_emailapi", "cid": get_current_cid()}, status_code = status.HTTP_403_FORBIDDEN)

    return current_user
