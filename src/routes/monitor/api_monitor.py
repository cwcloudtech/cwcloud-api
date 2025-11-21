from typing import Annotated, Optional
from sqlalchemy.orm import Session
from controllers.monitor import add_monitor, get_monitor, get_monitors, remove_monitor, update_monitor
from fastapi import Depends, APIRouter

from schemas.User import UserSchema
from database.postgres_db import get_db
from schemas.Monitor import MonitorSchema
from middleware.monitorapi_guard import monitorapi_required

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "monitor"
_counter = create_counter("monitor_api", "Monitor API counter")

@router.get("/all")
def get_all_monitors(current_user: Annotated[UserSchema, Depends(monitorapi_required)], db: Session = Depends(get_db), family: Optional[str] = None):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_monitors(current_user, db, family)

@router.get("/{monitor_id}")
def get_monitor_by_id(current_user: Annotated[UserSchema, Depends(monitorapi_required)], monitor_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_monitor(current_user, monitor_id, db)

@router.post("")
def create_monitor(current_user: Annotated[UserSchema, Depends(monitorapi_required)], payload: MonitorSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return add_monitor(current_user, payload, db)

@router.put("/{monitor_id}")
def update_monitor_by_id(current_user: Annotated[UserSchema, Depends(monitorapi_required)], monitor_id: str, payload: MonitorSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        return update_monitor(current_user, monitor_id, payload, db)

@router.delete("/{monitor_id}")
def delete_monitor(current_user: Annotated[UserSchema, Depends(monitorapi_required)], monitor_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return remove_monitor(current_user, monitor_id, db)
