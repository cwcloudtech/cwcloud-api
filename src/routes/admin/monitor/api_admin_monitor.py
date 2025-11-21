from typing import Annotated, Optional
from sqlalchemy.orm import Session
from controllers.admin.admin_monitor import get_monitors, get_monitor, add_monitor, update_monitor, remove_monitor
from fastapi import Depends, APIRouter

from schemas.User import UserSchema
from database.postgres_db import get_db
from schemas.Monitor import AdminMonitorSchema
from middleware.auth_guard import admin_required

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "admin-monitor"
_counter = create_counter("admin_monitor_api", "Admin Monitor API counter")

@router.get("/all")
def get_all_monitors(current_user: Annotated[UserSchema, Depends(admin_required)], db: Session = Depends(get_db), family: Optional[str] = None):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_monitors(db, family)

@router.get("/{monitor_id}")
def get_monitor_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], monitor_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_monitor(monitor_id, db)

@router.post("")
def create_monitor(current_user: Annotated[UserSchema, Depends(admin_required)], payload: AdminMonitorSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return add_monitor(payload, db)

@router.put("/{monitor_id}")
def update_monitor_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], monitor_id: str, payload: AdminMonitorSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        return update_monitor(monitor_id, payload, db)

@router.delete("/{monitor_id}")
def delete_monitor(current_user: Annotated[UserSchema, Depends(admin_required)], monitor_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return remove_monitor(monitor_id, db)
