
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse

from database.postgres_db import get_db
from middleware.auth_guard import get_current_active_user
from schemas.User import UserSchema
from schemas.API_keys import ApiKeysSchema, ApiKeysVerificationSchema
from entities.Apikeys import ApiKeys
from controllers.api_keys import create_api_key_for_user

from utils.common import is_empty
from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()

_span_prefix = "api-keys"
_counter = create_counter("keys_api", "Keys API counter")

@router.post("")
def create_api_key(current_user: Annotated[UserSchema, Depends(get_current_active_user)], payload: ApiKeysSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return create_api_key_for_user(current_user.id, payload, db)

@router.get("")
def get_api_keys(current_user: Annotated[UserSchema, Depends(get_current_active_user)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        from entities.Apikeys import ApiKeys
        api_keys = ApiKeys.getUserApiKeys(current_user.id, db)
        keys = [{"id": key.id, "name": key.name, "created_at": key.created_at} for key in api_keys]
        return JSONResponse(content = {
            'status': 'ok',
            'api_keys': keys
        }, status_code = 200)

@router.get("/{key_id}/value")
def get_api_key_value(current_user: Annotated[UserSchema, Depends(get_current_active_user)], key_id: str, db: Session = Depends(get_db)):
    """The API key's value - what goes in the X-Auth-Token header - for the copy button."""
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        apiKey = ApiKeys.getUserApiKey(current_user.id, key_id, db)
        if not apiKey:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'api key not found',
                'i18n_code': 'api_key_not_found',
                'cid': get_current_cid()
            }, status_code = 404)
        return JSONResponse(content = {
            'status': 'ok',
            'value': apiKey.secret_key
        }, status_code = 200)

@router.delete("/{key_id}")
def delete_api_key(current_user: Annotated[UserSchema, Depends(get_current_active_user)], key_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        from entities.Apikeys import ApiKeys
        apiKey = ApiKeys.getUserApiKey(current_user.id, key_id, db)
        if not apiKey:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'api key not found',
                'i18n_code': 'api_key_not_found',
                'cid': get_current_cid()
            }, status_code = 404)
        ApiKeys.deleteUserApiKey(current_user.id, key_id, db)
        return JSONResponse(content = {
            'status': 'ok',
            'message': 'api key successfully deleted',
            'i18n_code': 'api_key_deleted'
        }, status_code = 200)

@router.post("/verify")
def verify_api_key(payload: ApiKeysVerificationSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.VERIFY)):
        increment_counter(_counter, Method.GET, Action.VERIFY)
        access_key = payload.access_key
        secret_key = payload.secret_key

        if is_empty(access_key):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'please provide an access key',
                'i18n_code': 'api_key_not_found',
                'cid': get_current_cid()
            }, status_code = 400)

        if is_empty(secret_key):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'please provide a secret key',
                'i18n_code': 'api_key_not_found',
                'cid': get_current_cid()
            }, status_code = 400)

        api_key = ApiKeys.getApiKey(access_key, secret_key, db)
        if is_empty(api_key):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'invalid api key credentials',
                'cid': get_current_cid()
            }, status_code = 401)

        return JSONResponse(content = {
            'status': 'ok',
            'message': 'api key credentials are valid'
        }, status_code = 200)
