from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter

from schemas.User import UserSchema
from schemas.ContactForm import ContactFormSchema
from middleware.emailapi_guard import emailapi_required
from controllers.contact_form import get_all_forms, get_form_by_user_and_id, add_form, update_form, remove_form
from database.postgres_db import get_db

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "contact-form"
_counter = create_counter("contact_form_api", "Contact form API counter")

@router.get("/all")
def get_all_contact_forms(current_user: Annotated[UserSchema, Depends(emailapi_required)], db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_all_forms(current_user, db)

@router.get("/{contact_form_id}")
def get_contact_form_by_id(current_user: Annotated[UserSchema, Depends(emailapi_required)], contact_form_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_form_by_user_and_id(current_user, contact_form_id, db)

@router.post("")
def create_contact_form(current_user: Annotated[UserSchema, Depends(emailapi_required)], payload: ContactFormSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return add_form(current_user, payload, db)

@router.put("/{contact_form_id}")
def update_contact_form_by_id(current_user: Annotated[UserSchema, Depends(emailapi_required)], contact_form_id: str, payload: ContactFormSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        return update_form(current_user, contact_form_id, payload, db)
    
@router.delete("/{contact_form_id}")
def delete_contact_form(current_user: Annotated[UserSchema, Depends(emailapi_required)], contact_form_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return remove_form(current_user, contact_form_id, db)
