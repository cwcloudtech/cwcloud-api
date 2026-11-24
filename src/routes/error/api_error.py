from fastapi import APIRouter

from exceptions.CwHTTPException import CwHTTPException

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()

_span_prefix = "error"
_counter = create_counter("error_api", "Error API counter")

@router.get("/400")
def generate_functional_ex():
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.FUNC)):
        increment_counter(_counter, Method.GET, Action.FUNC)
        raise CwHTTPException(message = {"error": "functional error test", "i18n_code": "functional_error"}, status_code = 400)

@router.get("/500")
def generate_technical_ex():
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.TECH)):
        increment_counter(_counter, Method.GET, Action.TECH)
        raise RuntimeError("technical error test")
