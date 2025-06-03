import base64
import json
from datetime import datetime
from fastapi.responses import JSONResponse

from entities.StorageKV import StorageKV
from entities.User import User
from database.redis_db import redis_client
from schemas.StorageKV import StorageKVUpdateRequest
from controllers.storage_kv import _store_in_database, _store_with_ttl
from utils.common import is_empty, is_not_empty
from utils.logger import log_msg
from utils.observability.cid import get_current_cid

def create_redis_key(user_id: int, key: str) -> str:
    combined_key = f"{user_id}_{key}"
    return base64.b64encode(combined_key.encode('utf-8')).decode('utf-8')

def get_all_storage_kvs(search: str = None, start_index: int = 0, max_results: int = 20, db = None):
    if search and search.strip():
        storage_kvs = StorageKV.searchStorageKVsByKey(search, db)
    else:
        storage_kvs = db.query(StorageKV).all()

    db_results = []
    for kv in storage_kvs:
        user = db.query(User).filter(User.id == kv.user_id).first()
        email = user.email if user else "Unknown"
        
        db_results.append({
            'id': str(kv.id),
            'key': kv.storage_key,
            'user_id': kv.user_id,
            'user_email': email,
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
            decoded_key = base64.b64decode(redis_key).decode('utf-8')
            if '_' in decoded_key:
                user_id_str, key = decoded_key.split('_', 1)
                try:
                    user_id = int(user_id_str)
                    user = db.query(User).filter(User.id == user_id).first()
                    email = user.email if user else "Unknown"

                    if search and search.strip() and search.lower() not in key.lower():
                        continue
                        
                    value = redis_client.get(redis_key)
                    if value:
                        current_time = datetime.now().isoformat()
                        ttl_seconds = redis_client.ttl(redis_key)
                        ttl_hours = round(ttl_seconds / 3600, 2) if ttl_seconds > 0 else None
                        
                        redis_results.append({
                            'id': f"redis_{redis_key}",
                            'key': key,
                            'user_id': user_id,
                            'user_email': email,
                            'payload': json.loads(value),
                            'created_at': current_time,
                            'updated_at': current_time,
                            'source': 'redis',
                            'ttl': ttl_hours
                        })
                except ValueError:
                    continue
        except Exception as e:
            log_msg("ERROR", f"Error processing Redis key {redis_key}: {str(e)}")
            continue

    combined_results = db_results + redis_results
    sorted_results = sorted(combined_results, key=lambda x: (x['user_id'], x['key']))
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

def get_user_storage_kvs(user_id: int, search: str = None, start_index: int = 0, max_results: int = 20, db = None):
    user = db.query(User).filter(User.id == user_id).first()
    if is_empty(user):
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"User with ID {user_id} not found",
            'i18n_code': 'user_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    if search and search.strip():
        storage_kvs = StorageKV.searchUserStorageKVsByKey(user_id, search, db)
    else:
        storage_kvs = StorageKV.getUserStorageKVs(user_id, db)

    db_results = []
    for kv in storage_kvs:
        db_results.append({
            'id': str(kv.id),
            'key': kv.storage_key,
            'user_id': kv.user_id,
            'user_email': user.email,
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
            decoded_key = base64.b64decode(redis_key).decode('utf-8')
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
                        'id': f"redis_{redis_key}",
                        'key': key,
                        'user_id': user_id,
                        'user_email': user.email,
                        'payload': json.loads(value),
                        'created_at': current_time,
                        'updated_at': current_time,
                        'source': 'redis',
                        'ttl': ttl_hours
                    })
        except Exception as e:
            log_msg("ERROR", f"Error processing Redis key {redis_key}: {str(e)}")
            continue

    combined_results = db_results + redis_results
    sorted_results = sorted(combined_results, key=lambda x: x['key'])
    total_count = len(sorted_results)
    paginated_results = sorted_results[start_index:start_index + max_results]
    
    return JSONResponse(content = {
        'status': 'ok',
        'items': paginated_results,
        'count': len(paginated_results),
        'total_count': total_count,
        'start_index': start_index,
        'max_results': max_results,
        'user_id': user_id,
        'user_email': user.email
    }, status_code = 200)

def get_storage_kv_by_id(kv_id: str, db = None):
    if kv_id.startswith("redis_"):
        try:
            redis_key = kv_id[6:]  #? Remove the "redis_" prefix
            value = redis_client.get(redis_key)
            if value:
                decoded_key = base64.b64decode(redis_key).decode('utf-8')
                if '_' in decoded_key:
                    user_id_str, key = decoded_key.split('_', 1)
                    try:
                        user_id = int(user_id_str)
                        user = db.query(User).filter(User.id == user_id).first()
                        email = user.email if user else "Unknown"
                        
                        current_time = datetime.now().isoformat()
                        ttl_seconds = redis_client.ttl(redis_key)
                        ttl_hours = round(ttl_seconds / 3600, 2) if ttl_seconds > 0 else None
                        
                        return JSONResponse(content = {
                            'status': 'ok',
                            'id': kv_id,
                            'key': key,
                            'user_id': user_id,
                            'user_email': email,
                            'payload': json.loads(value),
                            'created_at': current_time,
                            'updated_at': current_time,
                            'source': 'redis',
                            'ttl': ttl_hours
                        }, status_code = 200)
                    except ValueError:
                        pass
        except Exception as e:
            log_msg("ERROR", f"Error processing Redis key {kv_id}: {str(e)}")

    try:
        storage_kv = StorageKV.findStorageKVById(kv_id, db)
        if not storage_kv:
            return JSONResponse(content = {
                'status': 'ko',
                'error': f"Storage KV with ID {kv_id} not found",
                'i18n_code': 'storage_kv_not_found',
                'cid': get_current_cid()
            }, status_code = 404)
        
        user = db.query(User).filter(User.id == storage_kv.user_id).first()
        email = user.email if user else "Unknown"
        
        return JSONResponse(content = {
            'status': 'ok',
            'id': str(storage_kv.id),
            'key': storage_kv.storage_key,
            'user_id': storage_kv.user_id,
            'user_email': email,
            'payload': storage_kv.payload,
            'created_at': storage_kv.created_at.isoformat() if storage_kv.created_at else None,
            'updated_at': storage_kv.updated_at.isoformat() if storage_kv.updated_at else None,
            'source': 'database',
            'ttl': None
        }, status_code = 200)
    except Exception as e:
        log_msg("ERROR", f"Error retrieving Storage KV with ID {kv_id}: {str(e)}")
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Error retrieving Storage KV with ID {kv_id}",
            'i18n_code': 'storage_kv_error',
            'cid': get_current_cid()
        }, status_code = 500)

def delete_user_kv(user_id: int, key: str, db):
    redis_key = create_redis_key(user_id, key)
    redis_deleted = redis_client.delete(redis_key) > 0
    db_deleted = StorageKV.deleteUserStorageKV(user_id, key, db)

    if is_empty(redis_deleted) and is_empty(db_deleted):
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Storage key '{key}' for user {user_id} not found",
            'i18n_code': 'storage_kv_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    
    return JSONResponse(content = {
        'status': 'ok',
        'message': f"Key '{key}' for user {user_id} successfully deleted",
        'key': key,
        'user_id': user_id,
        'i18n_code': 'admin_storage_kv_deleted'
    }, status_code = 200)

def update_user_kv(user_id: int, key: str, payload: StorageKVUpdateRequest, db):
    user = db.query(User).filter(User.id == user_id).first()
    if is_empty(user):
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"User with ID {user_id} not found",
            'i18n_code': 'user_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    existing_in_db = StorageKV.findUserStorageKVByKey(user_id, key, db)
    redis_key = create_redis_key(user_id, key)
    existing_in_redis = redis_client.exists(redis_key)
    
    if is_empty(existing_in_db) and not existing_in_redis:
        return JSONResponse(content = {
            'status': 'ko',
            'error': f"Storage key '{key}' not found for user ID {user_id}",
            'i18n_code': 'storage_kv_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    if is_not_empty(payload.ttl) and payload.ttl > 0:
        return _store_with_ttl(user_id, key, payload.payload, payload.ttl, db)
    else:
        return _store_in_database(user_id, key, payload.payload, db, True)
