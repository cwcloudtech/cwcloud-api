from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.api_keys import admin_create_api_key, admin_delete_api_key, admin_get_api_key_value, admin_get_api_keys
from database.postgres_db import get_db
from middleware.auth_guard import admin_required
from schemas.API_keys import ApiKeysAdminSchema
from schemas.User import UserSchema
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format

router = APIRouter()

_span_prefix = "admin-api-keys"
_counter = create_counter("admin_keys_api", "Admin API keys counter")

@router.post("")
def create_api_key(current_user: Annotated[UserSchema, Depends(admin_required)], payload: ApiKeysAdminSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return admin_create_api_key(current_user, payload, db)

@router.get("")
def get_api_keys(current_user: Annotated[UserSchema, Depends(admin_required)], user_id: Optional[int] = None, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return admin_get_api_keys(db, user_id)

@router.get("/{key_id}/value")
def get_api_key_value(current_user: Annotated[UserSchema, Depends(admin_required)], key_id: int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return admin_get_api_key_value(key_id, db)

@router.delete("/{key_id}")
def delete_api_key(current_user: Annotated[UserSchema, Depends(admin_required)], key_id: int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return admin_delete_api_key(current_user, key_id, db)
