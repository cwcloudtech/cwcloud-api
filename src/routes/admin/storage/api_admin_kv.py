from typing import Annotated
from fastapi import Depends, APIRouter, Query
from sqlalchemy.orm import Session

from database.postgres_db import get_db
from middleware.auth_guard import admin_required
from schemas.StorageKV import StorageKVUpdateRequest
from schemas.User import UserSchema
from controllers.admin.storage.admin_kv import delete_user_kv, get_all_storage_kvs, get_user_storage_kvs, get_storage_kv_by_id, update_user_kv

from utils.observability.otel import get_otel_tracer
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "admin-storage-kv"
_counter = create_counter("admin_storage_kv_api", "Admin Storage KV API counter")

@router.get("/all")
def get_all_kvs(current_user: Annotated[UserSchema, Depends(admin_required)], search: str = Query(None, description="Search term to find in storage keys"), start_index: int = Query(0, ge=0), max_results: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.GET}"):
        increment_counter(_counter, Method.GET)
        return get_all_storage_kvs(search, start_index, max_results, db)

@router.get("/user/{user_id}")
def get_user_kvs(current_user: Annotated[UserSchema, Depends(admin_required)], user_id: int, search: str = Query(None, description="Search term to find in storage keys"), start_index: int = Query(0, ge=0), max_results: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.GET}"):
        increment_counter(_counter, Method.GET)
        return get_user_storage_kvs(user_id, search, start_index, max_results, db)

@router.get("/{kv_id}")
def get_kv_by_id(current_user: Annotated[UserSchema, Depends(admin_required)], kv_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.GET}"):
        increment_counter(_counter, Method.GET)
        return get_storage_kv_by_id(kv_id, db)

@router.delete("/user/{user_id}/storage/{key}")
def delete_storage_kv(current_user: Annotated[UserSchema, Depends(admin_required)], user_id: int, key: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.DELETE}"):
        increment_counter(_counter, Method.DELETE)
        return delete_user_kv(user_id, key, db)

@router.put("/user/{user_id}/storage/{key}")
def update_user_storage_kv(current_user: Annotated[UserSchema, Depends(admin_required)], user_id: int, key: str, payload: StorageKVUpdateRequest, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(f"{_span_prefix}-{Method.PUT}"):
        increment_counter(_counter, Method.PUT)
        return update_user_kv(user_id, key, payload, db)
