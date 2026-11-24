from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from typing import Annotated, Optional

from middleware.faasapi_guard import faasapi_required
from database.postgres_db import get_db
from schemas.User import UserSchema
from schemas.faas.Trigger import Trigger, CompletedTrigger
from controllers.faas.triggers import add_trigger, clear_my_triggers, delete_trigger, get_my_triggers, get_trigger, override_trigger

from utils.common import is_false
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()

_span_prefix = "faas-trigger"
_counter = create_counter("faas_trigger_api", "FaaS trigger API counter")

@router.post("/trigger")
def create_trigger(payload: Trigger, response: Response, current_user: Annotated[UserSchema, Depends(faasapi_required)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        result = add_trigger(payload, current_user, db)
        response.status_code = result['code']
        return result

@router.put("/trigger/{id}")
def update_trigger(id: str, payload: CompletedTrigger, response: Response, current_user: Annotated[UserSchema, Depends(faasapi_required)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        result = override_trigger(id, current_user, payload, db)
        response.status_code = result['code']
        return result

@router.get("/trigger/{id}")
def find_trigger_by_id(id: str, response: Response, current_user: Annotated[UserSchema, Depends(faasapi_required)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        result = get_trigger(id, current_user, db)
        response.status_code = result['code']
        if is_false(result['status']):
            return result

        return result['entity']

@router.get("/triggers")
def find_my_triggers(response: Response, current_user: Annotated[UserSchema, Depends(faasapi_required)], kind: Optional[str] = None, start_index: int = 0, max_results: int = 10, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.ALL)):
        increment_counter(_counter, Method.GET, Action.ALL)
        results = get_my_triggers(db, current_user, kind, start_index, max_results)
        response.status_code = results['code']
        return results

@router.delete("/trigger/{id}")
def delete_trigger_by_id(id: str, response: Response, current_user: Annotated[UserSchema, Depends(faasapi_required)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        result = delete_trigger(id, current_user, db)
        response.status_code = result['code']
        return result

@router.delete("/triggers")
def delete_all_triggers(response: Response, current_user: Annotated[UserSchema, Depends(faasapi_required)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE, Action.ALL)):
        increment_counter(_counter, Method.DELETE, Action.ALL)
        result = clear_my_triggers(current_user, db)
        response.status_code = result['code']
        return result
