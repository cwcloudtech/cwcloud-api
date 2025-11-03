from fastapi import APIRouter, Depends, Response, Header
from sqlalchemy.orm import Session
from typing import Annotated

from database.postgres_db import get_db
from middleware.auth_guard import get_current_not_mandatory_user, get_user_authentication
from schemas.User import UserSchema
from schemas.UserAuthentication import UserAuthentication
from controllers.faas.invocations import invoke, invoke_sync

from utils.faas.invocations import convert_to_invocation
from utils.fastapi import get_raw_body
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()

_span_prefix = "faas-webhook"
_counter = create_counter("faas_webhook_api", "FaaS webhook invocation API counter")

@router.post("/webhook/{function_id}")
def webhook_invocation(function_id: str, response: Response, current_user: Annotated[UserSchema, Depends(get_current_not_mandatory_user)], user_auth: Annotated[UserAuthentication, Depends(get_user_authentication)], x_arg_key: Annotated[str | None, Header()] = "raw_data", body: str = Depends(get_raw_body), db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        payload = convert_to_invocation(function_id, body, x_arg_key)
        result = invoke(payload, current_user, user_auth, db)
        response.status_code = result['code']
        return result

@router.post("/webhook/{function_id}/sync")
def webhook_invocation_sync(function_id: str, response: Response, current_user: Annotated[UserSchema, Depends(get_current_not_mandatory_user)], user_auth: Annotated[UserAuthentication, Depends(get_user_authentication)], x_arg_key: Annotated[str | None, Header()] = "raw_data", body: str = Depends(get_raw_body), db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST, Action.SYNC)):
        increment_counter(_counter, Method.POST, Action.SYNC)
        payload = convert_to_invocation(function_id, body, x_arg_key)
        result = invoke_sync(payload, current_user, user_auth, db)
        response.status_code = result['code']
        return result
