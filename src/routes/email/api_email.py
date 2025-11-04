from typing import Annotated
from fastapi.responses import JSONResponse
from fastapi import Request, Depends, APIRouter

from middleware.auth_guard import get_current_active_user
from middleware.emailapi_guard import emailapi_required
from schemas.User import UserSchema
from schemas.Email import EmailSchema

from utils.common import is_empty
from utils.logger import log_msg
from utils.mail import EMAIL_ADAPTER
from utils.observability.cid import get_current_cid
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method
from utils.observability.tracker import track_log

router = APIRouter()

_span_prefix = "email"
_counter = create_counter("email_api", "Email API counter")

@router.post("")
def send_email(request: Request, current_user: Annotated[UserSchema, Depends(get_current_active_user)], email_api: Annotated[str, Depends(emailapi_required)], payload: EmailSchema):
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

        email = payload.model_dump(by_alias = True)
        log_msg("INFO", "[api_email] from = {}, user = {}".format(email, current_user.email))
        track_log(request, "api_email", current_user.email)

        return EMAIL_ADAPTER().send(email)
