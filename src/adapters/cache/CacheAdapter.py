from abc import ABC, abstractmethod

class CacheAdapter(ABC):
    @abstractmethod
    def get(self, key):
        pass

    @abstractmethod
    def put(self, key, value, ttl, unit = "hours"):
        pass

    @abstractmethod
    def delete(self, key):
        pass
