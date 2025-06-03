from typing import Annotated, Optional
from fastapi import Depends, APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.postgres_db import get_db
from middleware.auth_guard import admin_required
from schemas.User import UserSchema
from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "admin-prompt-usage"
_counter = create_counter("admin_prompt_usage_api", "Admin Prompt Usage API counter")

@router.get("/prompt/usage/all")
def get_all_users_usage(
    current_user: Annotated[UserSchema, Depends(admin_required)],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adapter: Optional[str] = None,
    start_index: int = Query(0, ge=0),
    max_results: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.GET}"):
        increment_counter(_counter, Method.GET)

        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Not Implemented',
            'i18n_code': 'not_implemented',
            'cid': get_current_cid()
        }, status_code = 405)

@router.get("/prompt/usage/user/{user_id}")
def get_user_usage_by_id(
    current_user: Annotated[UserSchema, Depends(admin_required)],
    user_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adapter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.GET}"):
        increment_counter(_counter, Method.GET)

        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Not Implemented',
            'i18n_code': 'not_implemented',
            'cid': get_current_cid()
        }, status_code = 405)

@router.get("/prompt/usage/summary")
def get_all_users_usage_summary(
    current_user: Annotated[UserSchema, Depends(admin_required)],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db)
):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.GET}"):
        increment_counter(_counter, Method.GET)

        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Not Implemented',
            'i18n_code': 'not_implemented',
            'cid': get_current_cid()
        }, status_code = 405)
