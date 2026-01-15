from adapters.cache.CacheAdapter import CacheAdapter
from utils.logger import log_msg

class LogAdapter(CacheAdapter):
    def get(self, key):
        log_msg("INFO", "[cache][LogAdapater][get] key = {}".format(key))
        return None

    def put(self, key, value, ttl, unit = "hours"):
        log_msg("INFO", "[cache][LogAdapater][put] key = {}, value = {}, ttl = {}, unit = {}".format(key, value, ttl, unit))
    
    def delete(self, key):
        log_msg("INFO", "[cache][LogAdapater][delete] key = {}".format(key))
