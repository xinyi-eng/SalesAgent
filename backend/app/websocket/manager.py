"""
WebSocket connection manager for real-time practice sessions
"""
from typing import Dict, Optional
from fastapi import WebSocket
import json
import uuid
from datetime import datetime
from enum import Enum


class ConversationState(str, Enum):
    """Conversation state indicators"""
    IDLE = "idle"
    USER_SPEAKING = "user_speaking"
    AI_SPEAKING = "ai_speaking"
    PROCESSING = "processing"


class ConnectionManager:
    """Manages WebSocket connections for practice sessions"""

    def __init__(self):
        # Map of session_id to active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        # Map of websocket to session_id for reverse lookup
        self.connection_sessions: Dict[WebSocket, str] = {}
        # Track conversation states
        self.session_states: Dict[str, ConversationState] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.connection_sessions[websocket] = session_id
        self.session_states[session_id] = ConversationState.IDLE

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        session_id = self.connection_sessions.pop(websocket, None)
        if session_id:
            self.active_connections.pop(session_id, None)
            self.session_states.pop(session_id, None)

    async def send_message(self, session_id: str, message: dict):
        """Send a message to a specific session"""
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json(message)

    async def send_audio_chunk(self, session_id: str, chunk: bytes):
        """Send binary audio chunk to client"""
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_bytes(chunk)

    async def send_status(self, session_id: str, state: ConversationState, metadata: dict = None):
        """Send state update to client"""
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json({
                "type": "status_update",
                "state": state.value,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            })
        self.session_states[session_id] = state

    async def broadcast(self, session_id: str, message: dict):
        """Broadcast message to all connections in a session (for multi-party)"""
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json(message)

    def get_active_session_ids(self) -> list:
        """Get list of all active session IDs"""
        return list(self.active_connections.keys())

    def get_state(self, session_id: str) -> ConversationState:
        """Get current conversation state for session"""
        return self.session_states.get(session_id, ConversationState.IDLE)


# Global connection manager instance
manager = ConnectionManager()


class PracticeSessionManager:
    """Manages practice session state and AI interaction"""

    def __init__(self):
        # Session state storage (in production, use Redis)
        self.sessions: Dict[str, dict] = {}

    def create_session(self, session_id: str, scenario_id: str, role_config: dict):
        """Create a new practice session state"""
        self.sessions[session_id] = {
            "id": session_id,
            "scenario_id": scenario_id,
            "role_config": role_config,
            "message_count": 0,
            "last_activity": datetime.utcnow().isoformat(),
            "context": [],
            "current_phase": "opening"
        }

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to session context"""
        if session_id in self.sessions:
            self.sessions[session_id]["context"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            })
            self.sessions[session_id]["message_count"] += 1
            self.sessions[session_id]["last_activity"] = datetime.utcnow().isoformat()

    def get_context(self, session_id: str) -> list:
        """Get conversation context for a session"""
        if session_id in self.sessions:
            return self.sessions[session_id]["context"]
        return []

    def should_trigger_summary(self, session_id: str) -> bool:
        """Check if summary should be triggered (every 3 rounds)"""
        if session_id in self.sessions:
            return self.sessions[session_id]["message_count"] > 0 and \
                   self.sessions[session_id]["message_count"] % 6 == 0  # 3 user + 3 AI = 6
        return False

    def should_insert_backchannel(self, session_id: str) -> bool:
        """Check if backchannel should be inserted based on user pause"""
        if session_id in self.sessions:
            context = self.sessions[session_id]["context"]
            if not context:
                return False
            last_msg = context[-1]
            if last_msg["role"] != "user":
                return False
            last_time = datetime.fromisoformat(last_msg["timestamp"])
            silence_seconds = (datetime.utcnow() - last_time).total_seconds()
            # Insert backchannel when user pauses 1.5-4 seconds
            return 1.5 <= silence_seconds <= 4.0
        return False

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get session information"""
        return self.sessions.get(session_id)

    def update_phase(self, session_id: str, phase: str):
        """Update the current phase of a session"""
        if session_id in self.sessions:
            self.sessions[session_id]["current_phase"] = phase

    def get_phase(self, session_id: str) -> str:
        """Get the current phase of a session"""
        if session_id in self.sessions:
            return self.sessions[session_id].get("current_phase", "opening")
        return "opening"

    def end_session(self, session_id: str):
        """End a practice session"""
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "completed"
            self.sessions[session_id]["ended_at"] = datetime.utcnow().isoformat()


# Global session manager instance
session_manager = PracticeSessionManager()