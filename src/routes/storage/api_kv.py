from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter, Query

from schemas.User import UserSchema
from schemas.StorageKV import StorageKVCreateRequest, StorageKVUpdateRequest
from database.postgres_db import get_db
from middleware.storageapi_guard import storageapi_required
from controllers.storage_kv import create_kv, get_kv, get_all_kvs, delete_kv, update_kv

from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

router = APIRouter()

_span_prefix = "storage_kv"
_counter = create_counter("storage_kv_api", "Storage KV API counter")

@router.post("")
def create_storage_kv(current_user: Annotated[UserSchema, Depends(storageapi_required)], payload: StorageKVCreateRequest, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.POST)):
        increment_counter(_counter, Method.POST)
        return create_kv(current_user, payload, db)

@router.get("/{key}")
def get_storage_kv(current_user: Annotated[UserSchema, Depends(storageapi_required)], key: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_kv(current_user, key, db)

@router.get("")
def get_all_storage_kvs(current_user: Annotated[UserSchema, Depends(storageapi_required)], search: str = Query(None, description="Search term to find in storage keys"), start_index: int = Query(0, ge=0), max_results: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        return get_all_kvs(current_user, search, start_index, max_results, db)

@router.put("/{key}")
def update_storage_kv(current_user: Annotated[UserSchema, Depends(storageapi_required)], key: str, payload: StorageKVUpdateRequest, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.PUT)):
        increment_counter(_counter, Method.PUT)
        return update_kv(current_user, key, payload, db)

@router.delete("/{key}")
def delete_storage_kv(current_user: Annotated[UserSchema, Depends(storageapi_required)], key: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.DELETE)):
        increment_counter(_counter, Method.DELETE)
        return delete_kv(current_user, key, db)
