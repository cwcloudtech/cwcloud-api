from typing import Annotated
from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse

from middleware.auth_guard import admin_required
from schemas.User import UserSchema
from schemas.Email import EmailAdminSchema

from utils.common import is_empty, is_true
from utils.logger import log_msg
from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.counter import create_counter, increment_counter
from utils.observability.traces import span_format
from utils.observability.enums import Method
from utils.mail import EMAIL_ADAPTER, send_templated_email

router = APIRouter()

_span_prefix = "adm-email"
_counter = create_counter("adm_email_api", "Admin email API counter")

@router.post("")
def send_email(current_user: Annotated[UserSchema, Depends(admin_required)], payload: EmailAdminSchema):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        if EMAIL_ADAPTER().is_disabled():
            return JSONResponse(content = {
                'status': 'ko',
                'i18n_code': 'disabled_email_service',
                'cid': get_current_cid()
            }, status_code = 405)
        
        if is_empty(payload.from_):
            payload.from_ = current_user.email

        email = payload.model_dump(by_alias=True)
        log_msg("DEBUG", "[api_admin_email] email = {}".format(email))

        return send_templated_email(email) if "templated" in email and is_true(email['templated']) else EMAIL_ADAPTER().send(email)
