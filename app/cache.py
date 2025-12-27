import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class CacheEntry:
    data: Dict[str, Any]
    created_at: float

class Cache:
    def __init__(self, ttl_seconds: int = 300):
        self._storage: Dict[str, CacheEntry] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self._storage:
            return None

        entry = self._storage[key]

        if time.time() - entry.created_at > self._ttl:
            del self._storage[key]
            return None

        return entry.data

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._storage[key] = CacheEntry(data=value, created_at=time.time())

    def clear(self) -> None:
        self._storage.clear()


cache = Cache(ttl_seconds=300)