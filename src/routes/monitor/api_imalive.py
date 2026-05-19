from typing import Annotated
from fastapi import APIRouter, Depends

from schemas.User import UserSchema
from middleware.auth_guard import get_current_user
from schemas.Monitor import ImAliveSchema
from controllers.monitor import ingest_imalive

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "imalive"
_counter = create_counter("imalive_api", "ImAlive API counter")

@router.post("")
def post_imalive(current_user: Annotated[UserSchema, Depends(get_current_user)], payload: ImAliveSchema):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return ingest_imalive(current_user, payload)
