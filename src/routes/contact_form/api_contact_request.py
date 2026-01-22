from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter, Request
from fastapi.responses import JSONResponse

from schemas.ContactForm import ContactFormRequestSchema
from controllers.contact_form import get_form_by_id
from database.postgres_db import get_db

from utils.common import is_empty, is_false
from utils.mail import send_contact_form_request
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.tracker import get_client_host_from_request
from utils.security import is_not_email_valid
from utils.observability.cid import get_current_cid
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "contact-request"
_counter = create_counter("contact_request", "Contact requests API counter")

@router.post("")
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

        body = {
            'message': message,
            'host': get_client_host_from_request(request),
            'name': payload.name,
            'firstname': payload.firstname,
            'phone': payload.phone,
            'form_id': form.id,
            'form_name': form.name
        }

        result = send_contact_form_request(form.mail_from, email, form.mail_to, body, subject, form.copyright_name, form.logo_url)
        if is_false(result['status']):
            return JSONResponse(content = {
                'status': 'ko',
                'error': result['error'],
                'i18n_code': result['i18n_code'],
                'cid': result['cid']
            }, status_code = result['http_code'])
        else:
            return JSONResponse(content = {
                'status': 'ok',
                'message': 'successfully sent contact email'
            }, status_code = 200)
