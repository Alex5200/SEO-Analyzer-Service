import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    data: Dict[str, Any]
    created_at: float

class Cache:
    def __init__(self, ttl_seconds: int = 300):
        self._storage: Dict[str, CacheEntry] = {}
        self._ttl = ttl_seconds
        logger.debug("Кэш создан с TTL=%d seconds", ttl_seconds)


    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self._storage:
            logger.debug("Кэш потерян для ключа: %s", key)
            return None

        entry = self._storage[key]

        if time.time() - entry.created_at >= self._ttl:
            logger.info("Кеш удален по ключу : %s ", key)
            del self._storage[key]
            return None

        return entry.data

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._storage[key] = CacheEntry(data=value, created_at=time.time())
        logger.info("Кеш установлен по ключу: %s ", key)


    def clear(self) -> None:
        self._storage.clear()
        logger.info("Cache cleared ")


cache = Cache(ttl_seconds=300)