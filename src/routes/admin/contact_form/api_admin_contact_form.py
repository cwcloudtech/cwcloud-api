from typing import Annotated
from sqlalchemy.orm import Session
from controllers.admin.admin_contact_form import get_all_forms, get_form_by_id, add_form, update_form, remove_form
from fastapi import Depends, APIRouter

from schemas.ContactForm import AdminContactFormSchema
from schemas.User import UserSchema
from database.postgres_db import get_db
from middleware.auth_guard import admin_required

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "admin-contact-form"
_counter = create_counter("admin_contact_form_api", "Admin Contact Form API counter")

@router.get("/all")
def get_all_contact_forms(current_user: Annotated[UserSchema, Depends(admin_required)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_all_forms(db)

@router.get("/{contact_form_id}")
def get_monitor_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], contact_form_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_form_by_id(contact_form_id, db)

@router.post("")
def create_monitor(current_user: Annotated[UserSchema, Depends(admin_required)], payload: AdminContactFormSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return add_form(payload, db)
    
@router.put("/{contact_form_id}")
def update_monitor_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], contact_form_id: str, payload: AdminContactFormSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        return update_form(contact_form_id, payload, db)
    
@router.delete("/{contact_form_id}")
def delete_monitor(current_user: Annotated[UserSchema, Depends(admin_required)], contact_form_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return remove_form(contact_form_id, db)
