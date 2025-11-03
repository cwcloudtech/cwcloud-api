from datetime import datetime
from enum import Enum
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from utils.common import is_empty
from utils.logger import quiet_log_msg
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method
from utils.observability.tracker import TRACKER_IMAGE_PATH, get_client_host_from_request, get_infos_from_ip, init_tracker_img, parse_user_agent

router = APIRouter()

_span_prefix = "tracker"
_counter = create_counter("tracker_api", "Tracker API counter")
    
class TrackerFormat(str, Enum):
    img = "img"
    json = "json"

@router.get("/{format}/{website}")
def track(request: Request, format: TrackerFormat, website: str):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        init_tracker_img()

        host = get_client_host_from_request(request)
        user_agent = request.headers.get("User-Agent")
        referrer = request.headers.get("Referer", "None")
        vdate = datetime.now()
        parsed_ua = parse_user_agent(user_agent)

        payload = {
            "status": "ok",
            "type": "tracker",
            "time": vdate.isoformat(),
            "host": host,
            "user_agent": user_agent,
            "referrer": referrer,
            "website": website,
            "device": parsed_ua['device'],
            "browser": parsed_ua['browser'],
            "os": parsed_ua['os'],
            "details": parsed_ua['details'],
            "infos": get_infos_from_ip(host)
        }

        quiet_log_msg("INFO", payload)

        return FileResponse(TRACKER_IMAGE_PATH, media_type="image/png", headers = {
            "x-cwcloud-client-host": host,
            "x-cwcloud-user-agent": user_agent,
            "x-cwcloud-website": website,
            "x-cwcloud-referrer": referrer,
            "x-cwcloud-time": vdate.isoformat()
        }) if format is TrackerFormat.img else payload
