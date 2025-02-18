from typing import Annotated
from fastapi import Depends, status, APIRouter, Response
from fastapi.responses import JSONResponse

from middleware.auth_guard import get_current_active_user
from schemas.User import UserSchema

from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "ai-prompt"
_counter = create_counter("ai_prompt_api", "CWAI Prompt API counter")

@router.post("/prompt", status_code = status.HTTP_201_CREATED)
def create_prompt(current_user: Annotated[UserSchema, Depends(get_current_active_user)], response: Response):
    with get_otel_tracer().start_as_current_span("{}-{}".format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)

        return JSONResponse(content = {
                'status': 'ko',
                'error': 'Cwai not implemented',
                'i18n_code': 'cwai_not_implemened',
                'cid': get_current_cid()
            }, status_code = 405)
