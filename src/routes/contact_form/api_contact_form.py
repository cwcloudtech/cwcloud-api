from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter, Request
from fastapi.responses import JSONResponse

from schemas.User import UserSchema
from schemas.ContactForm import ContactFormSchema, ContactFormRequestSchema
from middleware.emailapi_guard import emailapi_required
from controllers.contact_form import get_all_forms, get_form_by_id, get_form_by_user_and_id, add_form, update_form, remove_form
from database.postgres_db import get_db

from utils.common import is_empty, is_not_empty
from utils.mail import send_contact_form_request
from utils.observability.tracker import get_client_host_from_request
from utils.security import is_not_email_valid
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method
from utils.observability.cid import get_current_cid

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

@router.post("/send")
def send_email(request: Request, payload: ContactFormRequestSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)

        form = get_form_by_id(payload.id, db)
        if not form:
           return JSONResponse(content = {
                'status': 'ko',
                'error': 'Contact form not found', 
                'i18n_code': 'contact_form_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        email = payload.email
        subject = payload.subject
        message = payload.message
        if is_empty(email) or is_empty(subject) or is_empty(message):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'missing informations', 
                'i18n_code': 'missing_info',
                'cid': get_current_cid()
            }, status_code = 400)

        if is_not_email_valid(email):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid email', 
                'i18n_code': 'invalid_email',
                'cid': get_current_cid()
            }, status_code = 400)

        body = "This email is from the following expeditor:" \
        "<ul>" \
        f"<li><b>Email: </b>{email}</li>" \
        f"<li><b>Name: </b>{payload.name}</li>" if is_not_empty(payload.name) else "" \
        f"<li><b>Surname: </b>{payload.surname}</li>" if is_not_empty(payload.surname) else "" \
        f"<li><b>Host: </b>{get_client_host_from_request(request)}</li>" \
        f"<li><b>Object: </b>{subject}</li>" \
        f"</ul><br /><hr />{message}"

        send_contact_form_request(form.to_email, email, form.to_email, body, subject, form.copyright_name, form.logo_url)
        return JSONResponse(content = {
            'status': 'ok',
            'message': 'successfully sent contact email'
        }, status_code = 200)
