"""
SalesAgent Application Entry Point
"""
import os
import re
import json
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import settings
from app.api.v1 import router as api_v1_router
from app.websocket.manager import manager, session_manager
from app.database import engine, Base, SessionLocal
from app.models.practice import PracticeMessage
from app.services.llm import get_minimax_service
from app.services.knowledge.service import get_knowledge_service

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Sales Agent - 话术对练、行业简报、SPIN拜访准备、PPT生成、商务文件"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok"}


# WebSocket endpoint for practice sessions
@app.websocket("/ws/practice/{session_id}")
async def practice_websocket(websocket: WebSocket, session_id: str):
    """
    Enhanced WebSocket endpoint for streaming voice conversations

    Client → Server Messages:
    - user_message: {"type": "user_message", "content": "...", "audio_data": "base64"}
    - stop_playback: {"type": "stop_playback"}
    - voice_start: {"type": "voice_start"}
    - voice_end: {"type": "voice_end"}

    Server → Client Messages:
    - ai_message: {"type": "ai_message", "content": "...", "audio_data": "base64"}
    - ai_streaming_start: {"type": "ai_streaming_start", "content_prefix": "..."}
    - audio_chunk: (binary) - raw audio bytes for streaming playback
    - ai_streaming_end: {"type": "ai_streaming_end", "content": "full text"}
    - status_update: {"type": "status_update", "state": "idle|user_speaking|ai_speaking|processing"}
    - backchannel: {"type": "backchannel", "content": "嗯"}
    """
    from app.websocket.manager import ConversationState
    from app.services.audio.backchannel import backchannel_manager

    await manager.connect(websocket, session_id)

    # Initialize session manager - load role_config from database if available
    session_info = session_manager.get_session_info(session_id)
    if not session_info:
        # Try to load role_config from database
        role_config = {}
        scenario_id = ""
        try:
            from app.database import get_db
            from app.models.practice import PracticeSession
            db = next(get_db())
            db_session = db.query(PracticeSession).filter(PracticeSession.id == session_id).first()
            if db_session:
                role_config = db_session.role_config or {}
                scenario_id = db_session.scenario_id or ""
        except Exception as e:
            print(f"[DEBUG] Failed to load session from database: {e}")

        session_manager.create_session(session_id, scenario_id, role_config)

    minimax = get_minimax_service()

    # Streaming control flags
    is_streaming_audio = False
    streaming_task = None

    async def send_audio_chunk(chunk: bytes):
        """Send audio chunk to client as binary"""
        await websocket.send_bytes(chunk)

    async def send_ai_audio(text: str, emotion: str = "neutral"):
        """Generate TTS audio for AI response and send to client"""
        nonlocal is_streaming_audio
        try:
            is_streaming_audio = True

            # Generate TTS audio with emotion
            audio_bytes = await minimax.text_to_speech(
                text=text,
                model="speech-2.8-hd",
                voice="male-qn-qingse",
                speed=1.0,
                volume=1.0,
                pitch=1.0,
                format="mp3",
                emotion=emotion
            )

            # Send audio as binary
            await manager.send_audio_chunk(session_id, audio_bytes)
            print(f"[DEBUG] Sent TTS audio: {len(audio_bytes)} bytes")

        except Exception as e:
            print(f"[DEBUG] TTS error: {e}")
        finally:
            is_streaming_audio = False

    def save_message_to_db(session_id: str, role: str, content: str):
        """Save message to database for persistence"""
        try:
            db = SessionLocal()
            message = PracticeMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            db.add(message)
            db.commit()
            db.close()
        except Exception as e:
            print(f"[DEBUG] Failed to save message to database: {e}")

    async def handle_user_message(content: str, audio_data: str = None):
        """Process user message with ASR/LLM/TTS pipeline - with knowledge base integration"""
        nonlocal streaming_task
        print(f"[DEBUG] handle_user_message called with content: {content[:50]}...")

        # Update state to processing
        await manager.send_status(session_id, ConversationState.PROCESSING)
        print(f"[DEBUG] Sent processing status")

        # ASR: If audio provided, transcribe it
        user_text = content
        if audio_data:
            try:
                audio_bytes = base64.b64decode(audio_data)
                user_text = await minimax.speech_to_text(audio_bytes)
            except Exception as e:
                print(f"ASR error: {e}")
                user_text = content

        session_manager.add_message(session_id, "user", user_text)
        save_message_to_db(session_id, "user", user_text)
        print(f"[DEBUG] Added user message to session, text: {user_text[:50]}...")

        # LLM: Generate response with knowledge base integration
        print(f"[DEBUG] minimax.api_key = {bool(minimax.api_key)}")
        if minimax.api_key:
            context = session_manager.get_context(session_id)

            # Build conversation messages WITH system prompt for role-play
            from app.services.conversation.handler import get_conversation_handler
            handler = get_conversation_handler()
            session_info = session_manager.get_session_info(session_id)
            role_config = session_info.get("role_config", {}) if session_info else {}

            # Map frontend's personality/decision_style to customer_type
            # Frontend uses: rational->analytical, emotional->expressive, hesitant->amiable, decisive->assertive
            personality_map = {
                "rational": "analytical",
                "emotional": "expressive",
                "hesitant": "amiable",
                "decisive": "assertive"
            }
            personality = role_config.get("personality", "decisive")
            customer_type = personality_map.get(personality, "assertive")

            scenario = session_info.get("scenario_id", "general") if session_info else "general"

            try:
                # Build conversation messages WITH system prompt for role-play
                # Use conversation handler which has knowledge base integration
                conversation_history = context[-10:]
                # Map "ai" role to "assistant" for MiniMax API compatibility
                for msg in conversation_history:
                    if msg.get("role") == "ai":
                        msg["role"] = "assistant"

                result = await handler.handle_message(
                    user_message=user_text,
                    conversation_history=conversation_history,
                    customer_type=customer_type,
                    scenario=scenario
                )
                full_response = result.get("response", "")
                knowledge_used = result.get("knowledge_used", [])
                if knowledge_used:
                    print(f"[DEBUG] Knowledge base used: {knowledge_used}")
                print(f"[DEBUG] handler.handle_message returned: {full_response[:200]}...")

                if full_response:
                    # Strip AI thinking tags from response before sending to frontend
                    clean_response = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()

                    session_manager.add_message(session_id, "ai", clean_response)
                    save_message_to_db(session_id, "ai", clean_response)
                    # Send the response
                    await manager.send_message(session_id, {
                        "type": "ai_message",
                        "content": clean_response
                    })

                    # Update phase based on message count
                    msg_count = session_manager.sessions.get(session_id, {}).get("message_count", 0)
                    phase = "opening"
                    if msg_count >= 12:
                        phase = "closing"
                    elif msg_count >= 9:
                        phase = "proposal"
                    elif msg_count >= 6:
                        phase = "needs"
                    elif msg_count >= 3:
                        phase = "discovery"

                    current_phase = session_manager.get_phase(session_id)
                    if phase != current_phase:
                        session_manager.update_phase(session_id, phase)
                        await manager.send_message(session_id, {
                            "type": "phase_complete",
                            "data": {"phase": phase}
                        })
                        print(f"[DEBUG] Phase transitioned to: {phase}")

                    # Send TTS audio to client (blocking to ensure delivery)
                    try:
                        emotion = result.get("emotion", "neutral")
                        await send_ai_audio(clean_response, emotion)
                    except Exception as e:
                        print(f"[DEBUG] Failed to send TTS: {e}")
                else:
                    await manager.send_message(session_id, {
                        "type": "ai_message",
                        "content": "抱歉，我现在无法回答。请稍后再试。"
                    })

            except Exception as e:
                print(f"LLM error: {e}")
                import traceback
                traceback.print_exc()
                # Fall back to mock response on error
                mock_response = "抱歉，我现在无法回答。请确保API密钥已正确配置。"
                try:
                    await manager.send_message(session_id, {
                        "type": "ai_message",
                        "content": mock_response
                    })
                    session_manager.add_message(session_id, "ai", mock_response)
                    save_message_to_db(session_id, "ai", mock_response)
                    await manager.send_status(session_id, ConversationState.IDLE)
                except Exception as send_err:
                    print(f"Failed to send error response: {send_err}")
        else:
            # Mock response without API key
            mock_response = "抱歉，我现在无法回答。请确保API密钥已正确配置。"
            try:
                await manager.send_message(session_id, {
                    "type": "ai_message",
                    "content": mock_response
                })
                session_manager.add_message(session_id, "ai", mock_response)
                save_message_to_db(session_id, "ai", mock_response)
                await manager.send_status(session_id, ConversationState.IDLE)
            except Exception as send_err:
                print(f"Failed to send mock response: {send_err}")

    try:
        while True:
            # Try to receive JSON message first
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                print(f"[DEBUG] Received WebSocket message type: {msg_type}, data: {data}")
            except Exception as e:
                print(f"[DEBUG] Error receiving JSON: {e}")
                # May receive binary data
                msg_type = None
                data = {}

            if msg_type == "user_message":
                await handle_user_message(
                    content=data.get("content", ""),
                    audio_data=data.get("audio_data", "")
                )

            elif msg_type == "stop_playback":
                # User interrupted AI speech
                is_streaming_audio = False
                await manager.send_status(session_id, ConversationState.IDLE)
                await manager.send_message(session_id, {
                    "type": "playback_stopped"
                })

            elif msg_type == "voice_start":
                await manager.send_status(session_id, ConversationState.USER_SPEAKING)

            elif msg_type == "voice_end":
                await manager.send_status(session_id, ConversationState.IDLE)
                # Check for backchannel opportunity
                if session_manager.should_insert_backchannel(session_id):
                    backchannel_text = backchannel_manager.generate_backchannel_text()
                    await manager.send_message(session_id, {
                        "type": "backchannel",
                        "content": backchannel_text
                    })

            # Check for summary trigger
            if session_manager.should_trigger_summary(session_id):
                await manager.send_message(session_id, {
                    "type": "summary_trigger",
                    "message": "建议进行阶段性总结"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        session_manager.end_session(session_id)


# Standalone TTS endpoint for testing
from pydantic import BaseModel as PydanticBaseModel

class TTSRequest(PydanticBaseModel):
    text: str
    voice: str = "male-qn-qingse"

@app.post("/api/v1/tts")
async def text_to_speech(request: TTSRequest):
    """
    Text-to-Speech endpoint using MiniMax Speech 2.8

    Args:
        text: Text to synthesize
        voice: Voice ID (male-qn-qingse, female-yuwen, etc.)

    Returns:
        Audio file (MP3)
    """
    minimax = get_minimax_service()

    if not minimax.api_key:
        return {"error": "MINIMAX_API_KEY not configured"}

    try:
        audio_bytes = await minimax.text_to_speech(text=request.text, voice=request.voice)
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mp3",
            headers={"Content-Disposition": "attachment; filename=tts.mp3"}
        )
    except Exception as e:
        return {"error": str(e)}


# Standalone ASR endpoint for testing
@app.post("/api/v1/asr")
async def speech_to_text(audio: UploadFile = File(...)):
    """
    Speech-to-Text endpoint using MiniMax Speech 2.8 ASR

    Args:
        audio: Audio file (mp3/wav/m4a)

    Returns:
        Transcribed text
    """
    minimax = get_minimax_service()

    if not minimax.api_key:
        return {"error": "MINIMAX_API_KEY not configured"}

    try:
        audio_data = await audio.read()
        text = await minimax.speech_to_text(audio_data)
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}


# Standalone LLM chat endpoint for testing
from typing import List, Dict
from pydantic import BaseModel

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "M2.7"

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint using MiniMax M2.7

    Args:
        messages: List of message dicts [{"role": "user/assistant", "content": "..."}]
        model: LLM model (M2.7/M2.5)

    Returns:
        LLM response text
    """
    minimax = get_minimax_service()

    if not minimax.api_key:
        return {"error": "MINIMAX_API_KEY not configured"}

    try:
        response = await minimax.chat(messages=request.messages, model=request.model)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)