from urllib.error import HTTPError
from fastapi import Depends, APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.postgres_db import get_db
from schemas.Control import ControlDeleteInstanceSchema, ControlUpdateInstanceSchema

from utils.client_ips import get_client_ips
from utils.common import is_not_empty
from utils.gitlab import delete_runner, get_project_runners
from utils.dynamic_name import rehash_dynamic_name
from utils.instance import delete_instance, update_instance_status, get_virtual_machine
from utils.logger import log_msg
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method
from utils.observability.cid import get_current_cid

router = APIRouter()

_span_prefix = "control"
_counter = create_counter("control_api", "Control API counter")

@router.post("/instance/{instance_id}")
def handle_instance_error_creation(request: Request, bt: BackgroundTasks, instance_id: str, payload: ControlDeleteInstanceSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        log_msg("ERROR", "[api_control] Cloud init failed for instance #{}: {}".format(instance_id, payload.error))

        from entities.Instance import Instance
        userInstance = Instance.findInstanceById(instance_id, db)
        if not userInstance:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'No server found with this name',
                'cid': get_current_cid()
            }, status_code = 404)

        client_ips = get_client_ips(request)
        instance_ip = userInstance.ip_address
        if not any(is_not_empty(ip) and ip == instance_ip for ip in client_ips):
            log_msg("ERROR", "[api_control] post instance 403: not the expected instance_ip = {} not in client_ips = {}".format(instance_ip, client_ips))
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Access denied for this ip address',
                'cid': get_current_cid()
            }, status_code = 403)

        server = get_virtual_machine(userInstance.provider, userInstance.region, userInstance.zone, rehash_dynamic_name(userInstance.name, userInstance.hash))

        if not server:
            return JSONResponse(content = {
                'status': 'ko',
                'error': f'No server found with this name',
                'cid': get_current_cid()
            }, status_code = 404)

        server_state = server["state"]

        if not server_state == "running" and not server_state == "stopped":
            return JSONResponse(content = {
                'status': 'ko',
                'error': "You can't delete the instance while it is {}".format(server_state),
                'cid': get_current_cid()
            }, status_code = 404)

        try:
            bt.add_task(delete_instance, userInstance.hash, userInstance.name, userInstance.user.email)
            runners = get_project_runners(userInstance.project.id, userInstance.project.gitlab_host, userInstance.project.access_token)
            filtered_runners = [runner for runner in runners if runner["ip_address"] == userInstance.ip_address]
            if len(filtered_runners) > 0:
                delete_runner(filtered_runners[0]["id"], userInstance.project.gitlab_host, userInstance.project.access_token)
            Instance.updateStatus(userInstance.id, "deleted", db)

            return JSONResponse(content = {
                'status': 'ok',
                'message': 'instance successfully deleted', 
                'i18n_code': 'instance_deleted'
            }, status_code = 200)
        except HTTPError as e:
            return JSONResponse(content = {
                'status': 'ko',
                'error': e.msg, 
                'i18n_code': e.headers['i18n_code'],
                'cid': get_current_cid()
            }, status_code = e.code)

@router.patch("/instance/{instance_id}")
def update_instance(request: Request, instance_id: str, payload: ControlUpdateInstanceSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PATCH)):
        increment_counter(_counter, Method.PATCH)
        action = payload.status
        from entities.Instance import Instance
        userInstance = Instance.findInstanceById(instance_id, db)
        if not userInstance:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'No server found with this name',
                'cid': get_current_cid()
            }, status_code = 404)

        client_ips = get_client_ips(request)
        instance_ip = userInstance.ip_address
        if not any(is_not_empty(ip) and ip == instance_ip for ip in client_ips):
            log_msg("ERROR", "[api_control] patch instance 403: not the expected instance_ip = {} not in client_ips = {}".format(instance_ip, client_ips))
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Access denied for this ip address',
                'cid': get_current_cid()
            }, status_code = 403)

        server = get_virtual_machine(userInstance.provider, userInstance.region, userInstance.zone, rehash_dynamic_name(userInstance.name, userInstance.hash))

        if not server:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'No server found with this name',
                'cid': get_current_cid()
            }, status_code = 404)

        target_server_id = server["id"]

        if not action == "activate":
            return JSONResponse(content = {
                'status': 'ko',
                'error': "This action doesn't exist",
                'cid': get_current_cid()
            }, status_code = 400)

        try:
            if userInstance.status == "active" and action == "activate":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'instance already active',
                    'cid': get_current_cid()
                }, status_code = 400)
            update_instance_status(userInstance, target_server_id, action, db)
            return JSONResponse(content = {
                'status': 'ok',
                'message': 'instance successfully updated',
                'i18n_code': 'instance_updated'
            }, status_code = 200)
        except HTTPError as e:
            return JSONResponse(content = {
                'status': 'ko',
                'error': e.msg, 
                'i18n_code': e.headers['i18n_code'],
                'cid': get_current_cid()
            }, status_code = e.code)
