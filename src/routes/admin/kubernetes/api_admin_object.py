import json

from typing import Literal, Annotated
from pydantic import Json
from sqlalchemy.orm import Session
from fastapi import APIRouter, Form, UploadFile, File, Depends, WebSocket, WebSocketDisconnect

from database.postgres_db import get_db
from middleware.auth_guard import admin_required, admin_required_ws
from middleware.k8sapi_guard import k8sapi_required
from schemas.Kubernetes import ObjectAddSchema, ObjectSchema, PodLogsSchema
from schemas.User import UserSchema
from controllers.admin.admin_k8s_objects import add_object_to_cluster, delete_object, get_cluster_config_maps,get_object, get_cluster_services, get_cluster_ingresses ,update_object,get_chart_values,get_cluster_secrets,get_cluster_general_services,get_cluster_general_namespaces, get_cluster_ingress_classes, get_cluster_pods
from controllers.admin.admin_k8s_objects import get_pod_logs_stream, get_pod_terminal_stream

from entities.User import User
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method
from utils.logger import log_msg

router = APIRouter()

_span_prefix = "adm-k8s-object"
_counter = create_counter("adm_k8s_object_api", "Admin K8S object API counter")

@router.get("/cluster/{cluster_id}/services")
def get_services(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.SVC)):
        increment_counter(_counter, Method.GET, Action.SVC)
        return get_cluster_services(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/configMaps")
def get_config_maps(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.CM)):
        increment_counter(_counter, Method.GET, Action.CM)
        return get_cluster_config_maps(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/ingresses")
def get_ingresses(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, db: Session = Depends(get_db)):
   with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.INGRESS)):
    increment_counter(_counter, Method.GET, Action.INGRESS)
    return get_cluster_ingresses(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/secrets")
def get_secrets(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.SECRET)):
        increment_counter(_counter, Method.GET, Action.SECRET)
        return get_cluster_secrets(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/general/services")
def get_general_services(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.GENSVC)):
        increment_counter(_counter, Method.GET, Action.GENSVC)
        return get_cluster_general_services(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/general/namespaces")
def get_general_namespaces(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.NS)):
        increment_counter(_counter, Method.GET, Action.NS)
        return get_cluster_general_namespaces(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/general/ingressClasses")
def get_general_ingress_classes(current_user: Annotated[UserSchema, Depends(admin_required)],cluster_id:int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.INGRESSCLASS)):
        increment_counter(_counter, Method.GET, Action.INGRESSCLASS)
        return get_cluster_ingress_classes(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/pods")
def get_pods(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.POD)):
        increment_counter(_counter, Method.GET, Action.POD)
        return get_cluster_pods(current_user, cluster_id, db)

@router.get("/cluster/{cluster_id}/yaml")
def get_object_yaml(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], cluster_id:int, kind:str, name:str, namespace:str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_object(current_user, ObjectSchema(kind=kind, name=name, namespace=namespace,cluster_id=cluster_id), db)

@router.put("/cluster/yaml")
def update_object_yaml(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], object: Json = Form(...), yaml_file: UploadFile = File(...), db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        object = json.loads(json.dumps(object))
        return update_object(current_user,ObjectSchema(**object), yaml_file, db)

@router.delete("")
def delete_object_from_cluster(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], object: ObjectSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return delete_object(current_user, object, db)

@router.post("")
def add_object( current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], object: Json = Form(...), object_file: UploadFile = File(...), db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        python_dict = json.loads(json.dumps(object))
        return add_object_to_cluster(current_user, object_file, ObjectAddSchema(**python_dict), db)

@router.get("/templates/values")
def get_template_values(current_user: Annotated[UserSchema, Depends(admin_required)], k8s: Annotated[str, Depends(k8sapi_required)], kind:Literal[
    'service',
    'ingress',
    'configmap',
    'secret'
]):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.TEMPLATE)):
        increment_counter(_counter, Method.GET, Action.TEMPLATE)
        return get_chart_values(kind)

@router.websocket("/cluster/{cluster_id}/pods/{pod_name}/logs/ws")
async def websocket_pod_logs(websocket: WebSocket, cluster_id: int, pod_name: str, namespace: str, container_name: str = None, tail_lines: int = 100, db: Session = Depends(get_db), current_user: User = Depends(admin_required_ws)):
    subproto = getattr(websocket.state, "ws_subprotocol", None)
    await websocket.accept(subprotocol=subproto)

    pod_logs = PodLogsSchema(
        cluster_id=cluster_id,
        pod_name=pod_name,
        namespace=namespace,
        container_name=container_name,
        tail_lines=tail_lines,
        follow=True
    )

    try:
        await get_pod_logs_stream(websocket, current_user, pod_logs, db)
    except WebSocketDisconnect:
        log_msg("INFO", f"WebSocket disconnected: pod={pod_name}")

@router.websocket("/cluster/{cluster_id}/pods/{pod_name}/terminal/ws")
async def websocket_pod_terminal(websocket: WebSocket, cluster_id: int, pod_name: str, namespace: str, container_name: str = None, db: Session = Depends(get_db), current_user: User = Depends(admin_required_ws)):
    subproto = getattr(websocket.state, "ws_subprotocol", None)
    await websocket.accept(subprotocol=subproto)
    try:
        await get_pod_terminal_stream(websocket, current_user, cluster_id, pod_name, namespace, container_name, db)
    except WebSocketDisconnect:
        log_msg("INFO", f"WebSocket disconnected: pod={pod_name}")
