import base64
import json
from datetime import datetime
from database.redis_db import redis_client
from utils.logger import log_msg

def create_redis_key(user_id: int, key: str) -> str:
    combined_key = f"{user_id}_{key}"
    return base64.b64encode(combined_key.encode('utf-8')).decode('utf-8')

def create_user_redis_pattern(user_id: int) -> str:
    prefix = f"{user_id}_"
    encoded_prefix = base64.b64encode(prefix.encode('utf-8')).decode('utf-8')
    return f"{encoded_prefix}*"

def get_redis_keys_for_user(user_id: int, search: str = None):
    pattern = create_user_redis_pattern(user_id)
    redis_results = []

    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
        
        for redis_key in keys:
            try:
                decoded_key = base64.b64decode(redis_key).decode('utf-8')
                if decoded_key.startswith(f"{user_id}_"):
                    key = decoded_key.split('_', 1)[1]

                    if search and search.strip() and search.lower() not in key.lower():
                        continue

                    pipe = redis_client.pipeline()
                    pipe.get(redis_key)
                    pipe.ttl(redis_key)
                    value, ttl_seconds = pipe.execute()
                    
                    if value:
                        current_time = datetime.now().isoformat()
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
        
        if cursor == 0:
            break
    
    return redis_results
