from typing import Annotated
from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse

from schemas.User import UserSchema
from middleware.auth_guard import admin_required

from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()

_span_prefix = "admin-ai-adapters"
_counter = create_counter("admin_ai_adapter_api", "Admin CWAI Adapter API counter")

@router.get("/adapters")
def get_all_adapters(current_user: Annotated[UserSchema, Depends(admin_required)]):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET, Action.ALL)
        return JSONResponse(content = {
                'status': 'ko',
                'error': 'Cwai not implemented',
                'i18n_code': 'cwai_not_implemened',
                'cid': get_current_cid()
            }, status_code = 405)

@router.get("/adapters/{adapter_id}")
def get_adapter(current_user: Annotated[UserSchema, Depends(admin_required)], adapter_id: str):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return JSONResponse(content = {
                'status': 'ko',
                'error': 'Cwai not implemented',
                'i18n_code': 'cwai_not_implemened',
                'cid': get_current_cid()
            }, status_code = 405)

@router.post("/adapters")
def create_adapter(current_user: Annotated[UserSchema, Depends(admin_required)]):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return JSONResponse(content = {
                'status': 'ko',
                'error': 'Cwai not implemented',
                'i18n_code': 'cwai_not_implemened',
                'cid': get_current_cid()
            }, status_code = 405)

@router.put("/adapters/{adapter_id}")
def update_adapter(current_user: Annotated[UserSchema, Depends(admin_required)], adapter_id: str):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        return JSONResponse(content = {
                'status': 'ko',
                'error': 'Cwai not implemented',
                'i18n_code': 'cwai_not_implemened',
                'cid': get_current_cid()
            }, status_code = 405)

@router.delete("/adapters/{adapter_id}")
def delete_adapter(current_user: Annotated[UserSchema, Depends(admin_required)], adapter_id: str):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return JSONResponse(content = {
                'status': 'ko',
                'error': 'Cwai not implemented',
                'i18n_code': 'cwai_not_implemened',
                'cid': get_current_cid()
            }, status_code = 405)
