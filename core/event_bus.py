"""
Event Bus — pub/sub abstraction.
Uses Redis if USE_REDIS=true, otherwise in-memory async queue.
Both interfaces are identical so agents don't care which is used.
"""

import asyncio
from typing import Callable, Dict, List, Any
from config import settings


# ── In-Memory Event Bus ───────────────────────────────────

class InMemoryEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[Dict] = []

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Dict[str, Any]):
        self._history.append({"event_type": event_type, "payload": payload})
        handlers = self._subscribers.get(event_type, [])
        results = []
        for handler in handlers:
            result = await handler(payload)
            results.append(result)
        return results

    def get_history(self, limit: int = 50) -> List[Dict]:
        return self._history[-limit:]


# ── Redis Event Bus ───────────────────────────────────────

class RedisEventBus:
    def __init__(self):
        import redis.asyncio as aioredis
        self._redis = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Dict[str, Any]):
        import json
        await self._redis.publish(event_type, json.dumps(payload))
        handlers = self._subscribers.get(event_type, [])
        results = []
        for handler in handlers:
            result = await handler(payload)
            results.append(result)
        return results

    def get_history(self, limit: int = 50) -> List[Dict]:
        return []


# ── Factory ───────────────────────────────────────────────

_bus = None


def get_event_bus():
    global _bus
    if _bus is None:
        if settings.use_redis:
            try:
                _bus = RedisEventBus()
                print("Event bus: Redis")
            except Exception:
                print("Redis unavailable, falling back to in-memory")
                _bus = InMemoryEventBus()
        else:
            _bus = InMemoryEventBus()
            print("Event bus: In-Memory")
    return _bus