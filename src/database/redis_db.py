import os
import redis

from utils.common import is_disabled
from utils.redis_config import get_host_and_port_from_env

_host, _port = get_host_and_port_from_env()
_redis_password = os.getenv('REDIS_PASSWORD')
redis_client = redis.StrictRedis(_host, _port, encoding="utf-8", decode_responses=True, password = None if is_disabled(_redis_password) else _redis_password)
