import base64
import json
from datetime import datetime
from binascii import Error as Base64Error
from fastapi.responses import JSONResponse
from typing import List, Dict

from entities.StorageKV import StorageKV
from entities.User import User
from database.redis_db import redis_client
from schemas.StorageKV import StorageKVUpdateRequest
from controllers.storage_kv import _store_in_database, _store_with_ttl
from utils.common import is_empty, is_not_empty
from utils.logger import log_msg
from utils.observability.cid import get_current_cid
from utils.redis import create_redis_key, get_redis_keys_for_user

def get_redis_keys_all_users(search: str = None):
    redis_results = []
    user_cache = {}
    
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor=cursor, count=100)
        valid_keys = []
        
        for redis_key in keys:
            try:
                decoded_key = base64.b64decode(redis_key).decode('utf-8')
            except (Base64Error, UnicodeDecodeError) as e:
                log_msg("debug", f"Failed to decode Redis key {redis_key}: {e}")
                continue
            
            if '_' not in decoded_key:
                continue
                
            user_id_str, key = decoded_key.split('_', 1)
            try:
                user_id = int(user_id_str)
            except ValueError:
                log_msg("debug", f"Invalid user_id format in key {decoded_key}")
                continue
            
            if search and search.strip() and search.lower() not in key.lower():
                continue
                
            valid_keys.append((redis_key, user_id, key))

        if valid_keys:
            pipe = redis_client.pipeline()
            for redis_key, _, _ in valid_keys:
                pipe.get(redis_key)
                pipe.ttl(redis_key)
            
            try:
                results = pipe.execute()
            except Exception as e:
                log_msg("error", f"Redis pipeline execution failed: {e}")
                continue
            
            for i, (redis_key, user_id, key) in enumerate(valid_keys):
                value = results[i * 2]
                ttl_seconds = results[i * 2 + 1]
                
                if value:
                    if user_id not in user_cache:
                        user_cache[user_id] = None
                    
                    current_time = datetime.now().isoformat()
                    ttl_hours = round(ttl_seconds / 3600, 2) if ttl_seconds > 0 else None
                    
                    try:
                        payload = json.loads(value)
                    except (json.JSONDecodeError, TypeError) as e:
                        log_msg("warning", f"Failed to parse JSON for key {key}: {e}")
                        continue
                    
                    redis_results.append({
                        'id': f"redis_{redis_key.decode() if isinstance(redis_key, bytes) else redis_key}",
                        'key': key,
                        'user_id': user_id,
                        'user_email': None,
                        'payload': payload,
                        'created_at': current_time,
                        'updated_at': current_time,
                        'source': 'redis',
                        'ttl': ttl_hours
                    })
        
        if cursor == 0:
            break
    
    return redis_results, user_cache

def populate_user_emails(results: List[Dict], user_cache: Dict, db):
    user_ids = set(user_cache.keys())
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        for user in users:
            user_cache[user.id] = user.email

    for result in results:
        if 'user_id' in result:
            result['user_email'] = user_cache.get(result['user_id'], "Unknown")

def get_all_storage_kvs(search: str = None, start_index: int = 0, max_results: int = 20, db = None):
    if search and search.strip():
        storage_kvs = StorageKV.searchStorageKVsByKey(search, db)
    else:
        storage_kvs = db.query(StorageKV).limit(1000).all()

    user_ids = list(set(kv.user_id for kv in storage_kvs))
    users_dict = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_dict = {user.id: user.email for user in users}

    db_results = []
    for kv in storage_kvs:
        email = users_dict.get(kv.user_id, "Unknown")
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

    redis_results, user_cache = get_redis_keys_all_users(search)
    populate_user_emails(redis_results, user_cache, db)

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

    redis_results = get_redis_keys_for_user(user_id, search)

    for result in redis_results:
        result.update({
            'id': f"redis_{create_redis_key(user_id, result['key'])}",
            'user_id': user_id,
            'user_email': user.email
        })

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
        return _store_in_database(user_id, key, payload.payload, db, True, True)
