"""
Redis Pub/Sub for voice processing tasks
Handles decoupling between ASR/TTS services and WebSocket sessions
"""
import asyncio
import json
from typing import Optional, AsyncIterator
import redis.asyncio as redis
from app.config import settings


class RedisPubSubManager:
    """Manages Redis pub/sub for voice processing"""

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None

    async def connect(self):
        """Initialize Redis connection"""
        self._client = redis.from_url(self.redis_url, decode_responses=False)
        self._pubsub = self._client.pubsub()

    async def disconnect(self):
        """Close Redis connection"""
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.close()

    async def enqueue_task(self, session_id: str, task: dict) -> str:
        """Enqueue a voice processing task"""
        task_json = json.dumps(task)
        await self._client.rpush(f"voice:task:{session_id}", task_json)
        return task.get("task_id", "")

    async def dequeue_task(self, session_id: str, timeout: int = 0) -> Optional[dict]:
        """Dequeue a voice processing task (blocking if timeout > 0)"""
        result = await self._client.blpop(f"voice:task:{session_id}", timeout=timeout)
        if result:
            _, task_json = result
            return json.loads(task_json)
        return None

    async def publish_status(self, session_id: str, status: dict):
        """Publish status update to subscribers"""
        channel = f"voice:status:{session_id}"
        await self._client.publish(channel, json.dumps(status))

    async def subscribe_status(self, session_id: str) -> AsyncIterator[dict]:
        """Subscribe to status updates"""
        channel = f"voice:status:{session_id}"
        await self._pubsub.subscribe(channel)
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await self._pubsub.unsubscribe(channel)

    async def publish_audio_chunk(self, session_id: str, chunk: bytes):
        """Publish audio chunk to subscribers"""
        channel = f"voice:audio:{session_id}"
        await self._client.publish(channel, chunk)

    async def subscribe_audio(self, session_id: str) -> AsyncIterator[bytes]:
        """Subscribe to audio chunks stream"""
        channel = f"voice:audio:{session_id}"
        await self._pubsub.subscribe(channel)
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    yield message["data"]
        finally:
            await self._pubsub.unsubscribe(channel)

    async def set_session_state(self, session_id: str, state: str):
        """Set session state in Redis"""
        await self._client.set(f"voice:state:{session_id}", state, ex=3600)

    async def get_session_state(self, session_id: str) -> Optional[str]:
        """Get session state from Redis"""
        state = await self._client.get(f"voice:state:{session_id}")
        return state.decode() if state else None


# Global instance
redis_pubsub = RedisPubSubManager()