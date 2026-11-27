from fastapi import Depends, APIRouter, BackgroundTasks
from typing import Annotated
from sqlalchemy.orm import Session

from schemas.User import UserSchema
from database.postgres_db import get_db
from schemas.Instance import InstanceProvisionSchema, InstanceAttachSchema, InstanceUpdateSchema, InstanceTypeUpdateSchema
from middleware.auth_guard import admin_required
from controllers.admin.admin_instance import admin_add_instance, admin_get_instance, admin_get_instances, admin_get_user_instances, admin_remove_instance, admin_update_instance, admin_update_instance_type, admin_refresh_instance, admin_attach_instance

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method

router = APIRouter()

_span_prefix = "adm-instance"
_counter = create_counter("adm_instance_api", "Admin instance API counter")

@router.post("/{provider}/{region}/{zone}/provision/{environment}")
def add_instance(bt: BackgroundTasks, current_user: Annotated[UserSchema, Depends(admin_required)], provider: str, region: str, zone: str, environment: str, payload: InstanceProvisionSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return admin_add_instance(current_user, payload, provider, region, zone, environment, db, bt)

@router.post("/{provider}/{region}/{zone}/attach/{project_id}")
def attach_instance(bt: BackgroundTasks, current_user: Annotated[UserSchema, Depends(admin_required)], provider: str, region: str, zone: str, project_id: str, payload: InstanceAttachSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST, Action.ATTACH)):
        increment_counter(_counter, Method.POST, Action.ATTACH)
        return admin_attach_instance(bt, current_user, provider, region, zone, project_id, payload, db)

@router.post("/refresh/{instance_id}")
def refresh_instance(current_user: Annotated[UserSchema, Depends(admin_required)], instance_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST, Action.REFRESH)):
        increment_counter(_counter, Method.POST, Action.REFRESH)
        return admin_refresh_instance(current_user, instance_id, db)

@router.get("/{instance_id}")
def get_instance_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], instance_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return admin_get_instance(current_user, instance_id, db)

@router.delete("/{instance_id}")
def delete_instance_by_id(bt: BackgroundTasks, current_user: Annotated[UserSchema, Depends(admin_required)], instance_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return admin_remove_instance(current_user, instance_id, db, bt)

@router.patch("/{instance_id}")
def update_instance_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], instance_id: str, payload: InstanceUpdateSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PATCH)):
        increment_counter(_counter, Method.PATCH)
        return admin_update_instance(current_user, instance_id, payload, db)

@router.patch("/{instance_id}/type")
def update_instance_type_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], instance_id: str, payload: InstanceTypeUpdateSchema, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PATCH)):
        increment_counter(_counter, Method.PATCH)
        return admin_update_instance_type(current_user, instance_id, payload, db)

@router.get("/{provider}/{region}/all")
def get_all_instances(current_user: Annotated[UserSchema, Depends(admin_required)], provider: str, region: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.ALL)):
        increment_counter(_counter, Method.GET, Action.ALL)
        return admin_get_instances(current_user, provider, region, db)

@router.get("/{provider}/{region}/{user_id}")
def get_user_instances(current_user: Annotated[UserSchema, Depends(admin_required)], provider: str, region: str, user_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.BYUSER)):
        increment_counter(_counter, Method.GET, Action.BYUSER)
        return admin_get_user_instances(current_user, provider, region, user_id, db)
