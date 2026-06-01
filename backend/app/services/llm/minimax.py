"""
MiniMax API Service - TTS, ASR, and LLM integration
"""
import os
import base64
import json
from typing import Optional, AsyncIterator
import httpx


class MiniMaxService:
    """MiniMax API service for Speech (TTS/ASR) and LLM (M2.7)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None
    ):
        """
        Initialize MiniMax service.

        Args:
            api_key: MiniMax API key (defaults to settings.MINIMAX_API_KEY)
            group_id: MiniMax Group ID (defaults to env MINIMAX_GROUP_ID)
        """
        # Import settings here to avoid circular imports and ensure env is loaded
        from app.config import settings
        self.api_key = api_key or settings.MINIMAX_API_KEY or os.getenv("MINIMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = "https://api.minimaxi.com/v1"

        if not self.api_key:
            print("Warning: MINIMAX_API_KEY not set")

    # ==================== TTS (Text-to-Speech) ====================

    async def text_to_speech(
        self,
        text: str,
        model: str = "speech-2.8-hd",
        voice: str = "male-qn-qingse",
        speed: float = 1.0,
        volume: float = 1.0,
        pitch: float = 1.0,
        format: str = "mp3"
    ) -> bytes:
        """
        Convert text to speech.

        Args:
            text: Text to synthesize
            model: TTS model (speech-2.8-hd for Token Plan Plus)
            voice: Voice name
            speed: Speech speed (0.5-2.0)
            volume: Volume (0-1)
            pitch: Pitch (0.5-2.0)
            format: Output format (mp3/wav/flac)

        Returns:
            Audio bytes
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/t2a_v2"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,  # speech-2.8-turbo or speech-2.8-hd
                    "text": text,
                    "stream": False,
                    "voice_setting": {
                        "voice_id": voice,
                        "speed": int(speed),
                        "vol": int(volume),
                        "pitch": int(pitch)
                    },
                    "audio_setting": {
                        "sample_rate": 32000,
                        "bitrate": 128000,
                        "format": format,
                        "channel": 1
                    }
                }
            )

            if response.status_code == 200:
                # Newer API returns audio directly as binary
                if response.headers.get("Content-Type", "").startswith("audio/"):
                    return response.content
                # Fallback to JSON with base64 audio
                data = response.json()
                audio_base64 = data.get("data", {}).get("audio", "")
                if audio_base64:
                    return base64.b64decode(audio_base64)
                raise Exception("No audio in response")
            else:
                raise Exception(f"TTS API error: {response.status_code} - {response.text}")

    async def text_to_speech_stream(
        self,
        text: str,
        model: str = "speech-2.8-hd",
        voice: str = "male-qn-qingse",
        on_chunk: Optional[callable] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream text to speech with callback for each chunk.

        Args:
            text: Text to synthesize
            model: TTS model
            voice: Voice name
            on_chunk: Optional callback for each audio chunk

        Yields:
            Audio chunks
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        # Use same endpoint but with stream: True - returns SSE
        url = f"{self.base_url}/t2a_v2"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "text": text,
                    "stream": True,
                    "voice_setting": {
                        "voice_id": voice,
                        "speed": 1,
                        "vol": 1,
                        "pitch": 1
                    },
                    "audio_setting": {
                        "format": "mp3",
                        "sample_rate": 32000,
                        "bitrate": 128000,
                        "channel": 1
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                audio_base64 = data.get("data", {}).get("audio", "")
                                if audio_base64:
                                    chunk = base64.b64decode(audio_base64)
                                    if on_chunk:
                                        on_chunk(chunk)
                                    yield chunk
                            except:
                                continue

    async def text_to_speech_incremental(
        self,
        text_iterator: AsyncIterator[str],
        model: str = "speech-2.8-hd",
        voice: str = "male-qn-qingse"
    ) -> AsyncIterator[bytes]:
        """
        Incremental TTS that processes LLM tokens as they arrive.
        Sends partial text to TTS when a good break point is reached.

        Args:
            text_iterator: Async iterator yielding text chunks (from LLM stream)
            model: TTS model
            voice: Voice name

        Yields:
            Audio chunks as they're generated
        """
        accumulated_text = ""
        break_points = [". ", "? ", "! ", "。", "？", "！", "，"]

        async for text_chunk in text_iterator:
            accumulated_text += text_chunk

            # Process when we have enough text (80+ chars) and find a break point
            while len(accumulated_text) >= 80:
                split_pos = -1
                for bp in break_points:
                    pos = accumulated_text[:80].rfind(bp)
                    if pos > 0:
                        split_pos = pos + len(bp)
                        break

                if split_pos < 0:
                    # No break point found, wait for more text
                    break

                partial_text = accumulated_text[:split_pos]
                accumulated_text = accumulated_text[split_pos:]

                # Stream the partial text
                async for chunk in self.text_to_speech_stream(partial_text, model, voice):
                    yield chunk

        # Process remaining text
        if accumulated_text.strip():
            async for chunk in self.text_to_speech_stream(accumulated_text, model, voice):
                yield chunk

    # ==================== ASR (Speech-to-Text) ====================

    async def speech_to_text(
        self,
        audio_data: bytes,
        model: str = "speech-2.8-asr",
        language_boost: Optional[str] = None,
        transcript_format: str = "text"
    ) -> str:
        """
        Convert speech to text.

        Args:
            audio_data: Audio bytes (mp3/wav/m4a)
            model: ASR model (speech-2.8-asr)
            language_boost: Language to boost (zh/cn/en/ja/ko)
            transcript_format: Output format (text/srt/vtt)

        Returns:
            Transcribed text
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/audio/transcriptions"

        # Encode audio to base64
        audio_base64 = base64.b64encode(audio_data).decode()

        payload = {
            "model": model,
            "audio_file": f"data:audio/mp3;base64,{audio_base64}",
            "language_boost": language_boost or "zh",
            "transcript_format": transcript_format
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("text", "")
            else:
                raise Exception(f"ASR API error: {response.status_code} - {response.text}")

    # ==================== LLM (M2.7) ====================

    async def chat(
        self,
        messages: list,
        model: str = "M2.7",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[list] = None
    ) -> str:
        """
        Chat with LLM (M2.7).

        Args:
            messages: List of message dicts [{"role": "user/assistant", "content": "..."}]
            model: LLM model (M2.7/M2.5)
            temperature: Temperature (0-1)
            max_tokens: Max response tokens
            stream: Enable streaming
            tools: List of tool definitions for function calling

        Returns:
            LLM response text, or JSON with tool_calls if function calling triggered
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": "MiniMax-M2.7",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    # Check if function calling was triggered
                    if "tool_calls" in message:
                        return json.dumps({
                            "type": "function_call",
                            "tool_calls": message.get("tool_calls", [])
                        })
                    return message.get("content", "")
                return ""
            else:
                raise Exception(f"LLM API error: {response.status_code} - {response.text}")

    async def chat_stream(
        self,
        messages: list,
        model: str = "MiniMax-M2.7",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """
        Stream chat with LLM.

        Args:
            messages: List of message dicts
            model: LLM model
            temperature: Temperature
            max_tokens: Max tokens

        Yields:
            Response chunks
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "MiniMax-M2.7",  # Fixed model name
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except:
                                continue

    async def chat_stream_with_tools(
        self,
        messages: list,
        tools: list = None,
        model: str = "MiniMax-M2.7",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator:
        """
        Stream chat with tool/function calling support.

        Args:
            messages: List of message dicts
            tools: List of tool definitions
            model: LLM model
            temperature: Temperature
            max_tokens: Max tokens

        Yields:
            Either string tokens (for regular content) or dicts with tool_calls
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": "MiniMax-M2.7",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        tool_calls_buffer = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})

                                    # Check for tool_calls in delta
                                    if "tool_calls" in delta:
                                        tool_calls = delta["tool_calls"]
                                        # Yield accumulated text first if any
                                        # But since we stream, we just collect tool_calls
                                        for tc in tool_calls:
                                            tool_calls_buffer.append(tc)
                                        continue

                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except:
                                continue

                # After stream ends, if we have tool calls, yield them
                if tool_calls_buffer:
                    yield {"tool_calls": tool_calls_buffer}

    # ==================== Voice Conversation (Voice-to-Voice) ====================

    async def voice_to_voice(
        self,
        audio_data: bytes,
        text: str = "",
        model: str = "speech-2.8",
        voice_id: str = "male-qn-qingse"
    ) -> dict:
        """
        Voice to voice conversation (ASR -> LLM -> TTS).

        Args:
            audio_data: Input audio bytes
            text: Optional text input (if empty, will transcribe audio)
            model: Model to use
            voice_id: Output voice

        Returns:
            dict with "text" (transcribed/response) and "audio" (audio bytes)
        """
        # Step 1: ASR - Convert speech to text
        if not text and audio_data:
            text = await self.speech_to_text(audio_data)

        # Step 2: LLM - Get response (would call actual LLM in production)
        # For now, return the transcribed text as echo
        response_text = f"AI回复: {text}"  # This would be the LLM response

        # Step 3: TTS - Convert response to speech
        audio_output = await self.text_to_speech(response_text, voice=voice_id)

        return {
            "text": text,
            "response_text": response_text,
            "audio": audio_output
        }


# Singleton instance
_minimax_service: Optional[MiniMaxService] = None


def get_minimax_service() -> MiniMaxService:
    """Get singleton MiniMax service instance."""
    global _minimax_service
    if _minimax_service is None:
        _minimax_service = MiniMaxService()
    return _minimax_service