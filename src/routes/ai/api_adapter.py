from typing import Annotated
from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse

from schemas.User import UserSchema
from middleware.auth_guard import get_current_active_user

from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()

_span_prefix = "ai-adapters"
_counter = create_counter("ai_adapter_api", "CWAI Model API counter")

@router.get("/adapters")
def get_adapters(current_user: Annotated[UserSchema, Depends(get_current_active_user)]):

    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET, Action.ALL)    
        return JSONResponse(content = {
                'status': 'ko',
                'error': 'Cwai not implemented',
                'i18n_code': 'cwai_not_implemened',
                'cid': get_current_cid()
            }, status_code = 405)
