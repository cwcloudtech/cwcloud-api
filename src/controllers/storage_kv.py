import base64
import json
from datetime import datetime
import uuid
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from entities.StorageKV import StorageKV
from schemas.User import UserSchema
from schemas.StorageKV import StorageKVCreateRequest, StorageKVUpdateRequest
from database.redis_db import redis_client
from utils.common import is_empty, is_not_empty
from utils.logger import log_msg
from utils.observability.cid import get_current_cid

def create_redis_key(user_id: int, key: str) -> str:
    combined_key = f"{user_id}_{key}"
    return base64.b64encode(combined_key.encode('utf-8')).decode('utf-8')

def _store_with_ttl(user_id, key, payload, ttl, db):
    StorageKV.deleteUserStorageKV(user_id, key, db)

    redis_key = create_redis_key(user_id, key)
    ttl_seconds = ttl * 3600
    
    redis_client.setex(
        redis_key,
        ttl_seconds,
        json.dumps(payload)
    )
    
    return JSONResponse(content = {
        'status': 'ok',
        'message': 'Storage key successfully created/updated with TTL',
        'key': key,
        'payload': payload,
        'i18n_code': 'storage_kv_created',
        'cid': get_current_cid()
    }, status_code = 201)

def _store_in_database(user_id, key, payload, db, is_update):
    redis_key = create_redis_key(user_id, key)
    redis_client.delete(redis_key)

    existing_kv = StorageKV.findUserStorageKVByKey(user_id, key, db)

    if existing_kv and is_update:
        updated_kv = StorageKV.updateStorageKV(user_id, key, payload, db)
        if updated_kv:
            return JSONResponse(content = {
                'status': 'ok',
                'message': 'Storage key successfully updated',
                'key': key,
                'payload': payload,
                'i18n_code': 'storage_kv_updated',
                'cid': get_current_cid()
            }, status_code = 200)

    new_storage_kv = StorageKV(
        id=uuid.uuid4(),
        storage_key=key,
        user_id=user_id,
        payload=payload,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    try:
        new_storage_kv.save(db)
        return JSONResponse(content = {
            'status': 'ok',
            'message': 'Storage key successfully created',
            'key': key,
            'payload': payload,
            'i18n_code': 'storage_kv_created',
            'cid': get_current_cid()
        }, status_code = 201)
    except IntegrityError:
        db.rollback()
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Storage key '{key}' already exists",
            'i18n_code': 'storage_kv_conflict',
            'cid': get_current_cid()
        }, status_code = 409)

def create_kv(current_user: UserSchema, payload: StorageKVCreateRequest, db):
    user_id = current_user.id
    storage_key = payload.key

    existing_kv = StorageKV.findUserStorageKVByKey(user_id, storage_key, db)
    if existing_kv:
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Storage key '{storage_key}' already exists",
            'i18n_code': 'storage_kv_conflict',
            'cid': get_current_cid()
        }, status_code = 409)

    if is_not_empty(payload.ttl) and payload.ttl > 0:
        return _store_with_ttl(user_id, storage_key, payload.payload, payload.ttl, db)
    else:
        return _store_in_database(user_id, storage_key, payload.payload, db, False)

def update_kv(current_user: UserSchema, key: str, payload: StorageKVUpdateRequest, db):
    user_id = current_user.id

    existing_in_db = StorageKV.findUserStorageKVByKey(user_id, key, db)
    redis_key = create_redis_key(user_id, key)
    existing_in_redis = redis_client.exists(redis_key)
    
    if is_empty(existing_in_db) and not existing_in_redis:
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Storage key '{key}' not found",
            'i18n_code': 'storage_kv_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    if is_not_empty(payload.ttl) and payload.ttl > 0:
        return _store_with_ttl(user_id, key, payload.payload, payload.ttl, db)
    else:
        return _store_in_database(user_id, key, payload.payload, db, True)

def get_kv(current_user: UserSchema, key: str, db):
    user_id = current_user.id
    redis_key = create_redis_key(user_id, key)
    redis_value = redis_client.get(redis_key)
    
    if redis_value:
        ttl_seconds = redis_client.ttl(redis_key)
        ttl_hours = round(ttl_seconds / 3600, 2) if ttl_seconds > 0 else None
        
        return JSONResponse(content = {
            'status': 'ok',
            'key': key,
            'payload': json.loads(redis_value),
            'source': 'redis',
            'ttl': ttl_hours
        }, status_code = 200)

    storage_kv = StorageKV.findUserStorageKVByKey(user_id, key, db)
    
    if is_empty(storage_kv):
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Storage key '{key}' not found",
            'i18n_code': 'storage_kv_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    
    return JSONResponse(content = {
        'status': 'ok',
        'key': key,
        'payload': storage_kv.payload,
        'created_at': storage_kv.created_at.isoformat() if storage_kv.created_at else None,
        'updated_at': storage_kv.updated_at.isoformat() if storage_kv.updated_at else None,
        'source': 'database',
        'ttl': None
    }, status_code = 200)

def get_all_kvs(current_user: UserSchema, search: str = None, start_index: int = 0, max_results: int = 20, db = None):
    user_id = current_user.id
    storage_kvs_query = StorageKV.getUserStorageKVs(user_id, db)
    if search and search.strip():
        storage_kvs = StorageKV.searchUserStorageKVsByKey(user_id, search, db)
    else:
        storage_kvs = storage_kvs_query

    db_results = []
    for kv in storage_kvs:
        db_results.append({
            'key': kv.storage_key,
            'payload': kv.payload,
            'created_at': kv.created_at.isoformat() if kv.created_at else None,
            'updated_at': kv.updated_at.isoformat() if kv.updated_at else None,
            'source': 'database',
            'ttl': None
        })

    all_keys = redis_client.keys("*")
    redis_results = []
    
    for redis_key in all_keys:
        try:
            decoded_key = base64.b64decode(redis_key.decode('utf-8') if isinstance(redis_key, bytes) else redis_key).decode('utf-8')
            if decoded_key.startswith(f"{user_id}_"):
                key = decoded_key.split('_', 1)[1]
                if search and search.strip() and search.lower() not in key.lower():
                    continue
                    
                value = redis_client.get(redis_key)
                if value:
                    current_time = datetime.now().isoformat()
                    ttl_seconds = redis_client.ttl(redis_key)
                    ttl_hours = round(ttl_seconds / 3600, 2) if ttl_seconds > 0 else None
                    
                    redis_results.append({
                        'key': key,
                        'payload': json.loads(value),
                        'created_at': current_time,
                        'updated_at': current_time,
                        'source': 'redis',
                        'ttl': ttl_hours
                    })
        except Exception as e:
            log_msg("ERROR", f"Error processing Redis key {redis_key}: {str(e)}")
            continue

    combined_results = {}
    for item in db_results:
        combined_results[item['key']] = item

    for item in redis_results:
        combined_results[item['key']] = item

    sorted_results = sorted(list(combined_results.values()), key=lambda x: x['key'])
    total_count = len(sorted_results)
    paginated_results = sorted_results[start_index:start_index + max_results]
    
    return JSONResponse(content = {
        'status': 'ok',
        'items': paginated_results,
        'count': len(paginated_results),
        'total_count': total_count,
        'start_index': start_index,
        'max_results': max_results
    }, status_code = 200)

def delete_kv(current_user: UserSchema, key: str, db):
    user_id = current_user.id
    redis_key = create_redis_key(user_id, key)
    redis_deleted = redis_client.delete(redis_key) > 0
    db_deleted = StorageKV.deleteUserStorageKV(user_id, key, db)

    if is_empty(redis_deleted) and is_empty(db_deleted):
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Storage key '{key}' not found",
            'i18n_code': 'storage_kv_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    
    return JSONResponse(content = {
        'status': 'ok',
        'message': f"Key '{key}' successfully deleted",
        'key': key,
        'i18n_code': 'storage_kv_deleted'
    }, status_code = 200)
