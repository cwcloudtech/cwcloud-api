import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from schemas.Contact import ContactSchema

from utils.common import is_empty, is_false
from utils.mail import EMAIL_EXPEDITOR, send_contact_email
from utils.security import is_not_email_valid
from utils.observability.tracker import get_client_host_from_request
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method
from utils.observability.cid import get_current_cid

router = APIRouter()

_span_prefix = "contact"
_counter = create_counter("contact_api", "Contact API counter")

RECEIVER_CONTACTS_EMAIL = os.getenv('RECEIVER_CONTACTS_EMAIL', EMAIL_EXPEDITOR)

@router.post("")
def contact_with_us(request: Request, payload: ContactSchema):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
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
            'host': get_client_host_from_request(request)
        }

        result = send_contact_email(email, RECEIVER_CONTACTS_EMAIL, body, subject)
        if is_false(result['status']):
            return JSONResponse(content = {
                'status': 'ko',
                'error': result['error'],
                'i18n_code': result['i18n_code'],
                'cid': result['cid']
            }, status_code = result['http_code'])
        return JSONResponse(content = {
            'status': 'ok',
            'message': 'successfully sent contact email'
        }, status_code = 200)
