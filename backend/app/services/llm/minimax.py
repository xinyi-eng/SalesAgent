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
        model: str = "speech-2.8-turbo",
        voice: str = "male-qn-qingse",
        speed: float = 1.0,
        volume: float = 1.0,
        pitch: float = 1.0,
        format: str = "mp3",
        emotion: str = "neutral",
        voice_modify: dict = None
    ) -> bytes:
        """
        Convert text to speech using MiniMax TTS API.
        Supports emotion tags (laughs, sighs, etc.) and voice_modify for pitch/intensity/timbre.

        Args:
            text: Text to synthesize (can include emotion tags like (laughs), (sighs), (breath))
            model: TTS model (speech-2.8-hd for Token Plan Plus)
            voice: Voice name
            speed: Speech speed (0.5-2.0)
            volume: Volume (0-1)
            pitch: Pitch (0.5-2.0)
            format: Output format (mp3/wav/flac/pcm)
            emotion: Speech emotion (neutral, happy, sad, angry, fearful, disgusted, surprised)
            voice_modify: Voice modification dict with keys:
                - pitch: int (-100 to 100, lower=deeper, higher=brighter)
                - intensity: int (-100 to 100, lower=softer, higher=stronger)
                - timbre: int (-100 to 100, lower=rounder, higher=clearer)
                - sound_effects: str (spacious_echo, auditorium_echo, lofi_telephone, robotic)

        Returns:
            Audio bytes (standard MP3/WAV format playable by browsers)
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
                    "model": model,
                    "text": text,
                    "stream": False,
                    "output_format": "url",
                    "voice_setting": {
                        "voice_id": voice,
                        "speed": int(speed),
                        "vol": int(volume),
                        "pitch": int(pitch),
                        "emotion": emotion if emotion != "neutral" else None
                    },
                    "audio_setting": {
                        "sample_rate": 32000,
                        "bitrate": 128000,
                        "format": format,
                        "channel": 1
                    },
                    "voice_modify": voice_modify or {}
                }
            )

            if response.status_code == 200:
                data = response.json()
                audio_url = data.get("data", {}).get("audio", "")
                if audio_url:
                    # Download audio from URL using a new client
                    async with httpx.AsyncClient(timeout=60.0) as download_client:
                        audio_resp = await download_client.get(audio_url)
                        if audio_resp.status_code == 200:
                            return audio_resp.content
                raise Exception("No audio URL in response")
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
        Stream text to speech using MiniMax WebSocket API.
        Returns proper MP3 audio with ID3 header - standard browser-playable format.

        Args:
            text: Text to synthesize
            model: TTS model (speech-2.8-hd recommended)
            voice: Voice name
            on_chunk: Optional callback for each audio chunk

        Yields:
            Audio chunks (standard MP3 format playable by browsers)
        """
        import websockets
        import ssl

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with websockets.connect(url, additional_headers=headers, ssl=ssl_context) as ws:
            # Wait for connection confirmation
            conn_resp = json.loads(await ws.recv())
            if conn_resp.get("event") != "connected_success":
                raise Exception("WebSocket connection failed")

            # Start task with audio settings for MP3 format
            start_msg = {
                "event": "task_start",
                "model": model,
                "voice_setting": {
                    "voice_id": voice,
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 1
                }
            }
            await ws.send(json.dumps(start_msg))

            # Wait for task_started confirmation
            task_resp = json.loads(await ws.recv())
            if task_resp.get("event") != "task_started":
                raise Exception(f"Task start failed: {task_resp}")

            # Send text for synthesis
            await ws.send(json.dumps({
                "event": "task_continue",
                "text": text
            }))

            # Receive audio chunks (hex-encoded MP3)
            while True:
                try:
                    response = json.loads(await ws.recv())

                    if "data" in response and "audio" in response["data"]:
                        audio_hex = response["data"]["audio"]
                        if audio_hex:
                            # Convert hex to bytes - this is proper MP3 data
                            audio_bytes = bytes.fromhex(audio_hex)
                            if on_chunk:
                                on_chunk(audio_bytes)
                            yield audio_bytes

                    if response.get("is_final"):
                        break

                except websockets.exceptions.ConnectionClosed:
                    break

            # Clean finish
            try:
                await ws.send(json.dumps({"event": "task_finish"}))
            except:
                pass

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
        transcript_format: str = "text",
        audio_mime: str = "audio/webm"
    ) -> str:
        """
        Convert speech to text.

        Args:
            audio_data: Audio bytes
            model: ASR model (speech-2.8-asr)
            language_boost: Language to boost (zh/cn/en/ja/ko)
            transcript_format: Output format (text/srt/vtt)
            audio_mime: MIME of the audio bytes — must match the actual
                format. The browser MediaRecorder typically produces
                `audio/webm` (Opus codec) — pass that through instead
                of hardcoding mp3 or the API will reject the file.

        Returns:
            Transcribed text
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/audio/transcriptions"

        # Encode audio to base64
        audio_base64 = base64.b64encode(audio_data).decode()

        # IMPORTANT: mime must match the actual bytes. Default to webm
        # because the browser's MediaRecorder produces webm/opus by
        # default — sending an mp3 mime prefix on webm data causes the
        # ASR to return empty text.
        payload = {
            "model": model,
            "audio_file": f"data:{audio_mime};base64,{audio_base64}",
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

    # ==================== Cloud ASR via Realtime API ====================

    async def speech_to_text_realtime(
        self,
        audio_data: bytes,
        audio_mime: str = "audio/webm"
    ) -> str:
        """Transcribe audio via the MiniMax Realtime WebSocket API.

        This is the most accurate path. It:
        1. Decodes the user's webm/opus recording to 24kHz mono PCM via ffmpeg
        2. Opens a WebSocket to wss://api.minimaxi.com/ws/v1/realtime
        3. Configures a transcription-only session with the asr-01 model
        4. Streams the audio chunks
        5. Triggers a response; the model's text reply IS the transcript
        6. Strips a leading "你好" greeting that the model sometimes adds

        Returns the transcribed Chinese text, or empty string on failure.
        """
        import asyncio
        import os
        import re
        import ssl
        import subprocess
        import tempfile
        import websockets

        # Step 1: convert any input → 24kHz mono PCM wav
        ext_map = {
            "audio/webm": ".webm",
            "audio/webm;codecs=opus": ".webm",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/mp3": ".mp3",
            "audio/mpeg": ".mp3",
            "audio/m4a": ".m4a",
        }
        ext = ext_map.get(audio_mime.split(";")[0].strip().lower(), ".webm")
        src_path = tempfile.mktemp(suffix=ext)
        with open(src_path, "wb") as f:
            f.write(audio_data)
        pcm_path = src_path + ".pcm"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", src_path,
                    "-ar", "24000", "-ac", "1",
                    "-f", "s16le", pcm_path,
                ],
                check=True, capture_output=True, timeout=30,
            )
        except Exception as ffmpeg_err:
            print(f"[ASR-Realtime] ffmpeg convert failed: {ffmpeg_err}")
            try:
                os.unlink(src_path)
            except Exception:
                pass
            return ""

        with open(pcm_path, "rb") as f:
            pcm_bytes = f.read()
        try:
            os.unlink(src_path)
            os.unlink(pcm_path)
        except Exception:
            pass

        # Step 2-5: WS to Realtime API
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        url = "wss://api.minimaxi.com/ws/v1/realtime"
        # Strong prompt that suppresses greetings and explanations
        instruction = (
            "你是一个语音转写机器。请把听到的中文原样输出。"
            "只输出你听到的文字，不加问候语，不加任何解释，不加标点修改。"
            "如果你听不清，就输出你听到的最接近的内容。"
        )

        try:
            async with websockets.connect(
                url,
                additional_headers={"Authorization": f"Bearer {self.api_key}"},
                ssl=ssl_ctx,
                max_size=10 * 1024 * 1024,
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=10)  # session.created

                await ws.send(json.dumps({
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "input_audio_format": "pcm16",
                        "input_audio_transcription": {"model": "asr-01"},
                        "instructions": instruction,
                    },
                }))
                await asyncio.wait_for(ws.recv(), timeout=10)  # session.updated

                # Stream audio in 100ms chunks
                chunk_size = 4800
                chunks = [pcm_bytes[i:i+chunk_size]
                          for i in range(0, len(pcm_bytes), chunk_size)]
                for ch in chunks:
                    await ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(ch).decode(),
                    }))
                    await asyncio.sleep(0.02)
                await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                # Force the model to actually run and return the transcript
                await ws.send(json.dumps({
                    "type": "response.create",
                    "response": {"modalities": ["text"]},
                }))

                # Collect the response text
                collected = ""
                final_text = ""
                for _ in range(60):
                    msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    data = json.loads(msg)
                    etype = data.get("type", "?")
                    if etype == "response.text.delta":
                        collected += data.get("delta", "")
                    elif etype == "response.text.done":
                        final_text = data.get("text", "")
                    elif etype == "response.done":
                        for o in data.get("response", {}).get("output", []):
                            for c in o.get("content", []):
                                if c.get("type") == "text":
                                    final_text = c.get("text", final_text)
                        break
                    elif etype == "error":
                        print(f"[ASR-Realtime] error: {data.get('error')}")
                        break

                # Prefer the response.done snapshot; fall back to streamed text
                result = final_text or collected

                # Step 6: clean up the model output
                # The model sometimes adds "你好" or "好的，我听到了：" prefix
                # Strip any greeting or preamble up to the first actual content
                # We use a simple heuristic: remove "你好" or "好的" at the start
                result = re.sub(r'^\s*你好[，,。\s]*', '', result)
                result = re.sub(r'^\s*好的[，,。\s]*', '', result)
                result = re.sub(r'^\s*我听到(?:了|的是)[：:，,。\s]*', '', result)
                result = result.strip()

                # Step 7: detect "non-transcript" replies. The model is a chat
                # model — when audio is too noisy/short, it may just say
                # "我明白了" / "好的" / "请继续" instead of transcribing. We
                # need to recognise these as a failed transcription so the
                # caller can fall back to local Whisper.
                non_transcript_patterns = [
                    r'^(我明白|好的|好|嗯|是|请继续|您请|听到|是的|你请|请说|好的我|好的您)[了呀呢啊]?',
                    r'^[，。？！“”\s]*$',  # only punctuation
                ]
                is_non_transcript = any(
                    re.match(p, result) for p in non_transcript_patterns
                ) if result else True
                if is_non_transcript:
                    print(
                        f"[ASR-Realtime] {len(audio_data)}B {audio_mime} → "
                        f"non-transcript reply {result!r}, signal failure"
                    )
                    return ""

                print(
                    f"[ASR-Realtime] {len(audio_data)}B {audio_mime} → "
                    f"text={result!r}"
                )
                return result

        except Exception as e:
            print(f"[ASR-Realtime] WS error: {e}")
            return ""

    # ==================== Local ASR (faster-whisper fallback) ====================

    async def speech_to_text_local(
        self,
        audio_data: bytes,
        audio_mime: str = "audio/webm"
    ) -> str:
        """Transcribe audio using a local faster-whisper model.

        The MiniMax cloud `/audio/transcriptions` endpoint is not available on
        the current API key, so we fall back to a fully-local Whisper model
        for the user's voice input. This is the only way the AI can actually
        understand what the user said.

        Args:
            audio_data: Raw audio bytes (webm/opus from the browser).
            audio_mime: The MIME type the bytes were sent as — used to write
                them to disk so ffmpeg can decode them.

        Returns:
            Transcribed text, or empty string on failure.
        """
        import asyncio
        import os
        import ssl
        import subprocess
        import tempfile
        from faster_whisper import WhisperModel

        # Make sure hf-mirror is the source (Windows SSL workaround).
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        _orig_ctx = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context

        # faster-whisper / ffmpeg need a real file. Write to a temp file with
        # the right extension so the decoder picks the right format.
        ext_map = {
            "audio/webm": ".webm",
            "audio/webm;codecs=opus": ".webm",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/mp3": ".mp3",
            "audio/mpeg": ".mp3",
            "audio/m4a": ".m4a",
            "audio/x-m4a": ".m4a",
        }
        ext = ext_map.get(audio_mime.split(";")[0].strip().lower(), ".webm")

        # Load model once and cache on the instance. Use 'small' for
        # significantly better Chinese accuracy. 'base' makes too many
        # Chinese character errors on browser-recorded audio.
        try:
            if not hasattr(self, "_whisper_model") or self._whisper_model is None:
                print("[ASR-Local] Loading faster-whisper 'small' model...")
                self._whisper_model = WhisperModel(
                    "small", device="cpu", compute_type="int8"
                )
                print("[ASR-Local] Model ready.")
            model = self._whisper_model
        finally:
            ssl._create_default_https_context = _orig_ctx

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        # Pre-process: normalize the audio so whisper sees a louder, cleaner
        # signal. The browser's MediaRecorder produces very quiet audio when
        # the user speaks at normal volume into a typical laptop mic — this
        # is the single biggest reason small/base whisper returns garbled
        # Chinese. We:
        #  1. convert webm/opus → 16kHz mono wav via ffmpeg
        #  2. apply a high-pass filter to cut low-frequency rumble
        #  3. apply dynamic normalization so the mean volume is around -20dB
        #  4. apply a final volume boost (volume=2.0 ~ +6dB) to make sure
        #     quiet speech is loud enough for whisper
        # NOTE: avoid silenceremove here — browser recordings of normal
        # speech through speakers are often below -40dB and the filter
        # would wipe them out.
        wav_path = tmp_path + ".wav"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", tmp_path,
                    "-af", "highpass=f=80,lowpass=f=8000,dynaudnorm=p=0.95:m=10:s=12,volume=2.0",
                    "-ar", "16000", "-ac", "1", "-f", "wav",
                    wav_path,
                ],
                check=True, capture_output=True, timeout=30,
            )
        except Exception as ffmpeg_err:
            print(f"[ASR-Local] ffmpeg preprocess failed: {ffmpeg_err}, falling back to raw input")
            wav_path = tmp_path

        # Keep the last audio file for inspection.
        try:
            import shutil
            debug_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "asr_debug"
            )
            os.makedirs(debug_dir, exist_ok=True)
            shutil.copy(wav_path, os.path.join(debug_dir, f"last_user_audio_processed.wav"))
        except Exception as e:
            print(f"[ASR-Local] debug save failed: {e}")

        try:
            # Run transcription in a thread so we don't block the event loop
            def _run():
                # Use VAD with very low threshold so quiet voices are kept.
                # beam_size=5 gives noticeably better Chinese accuracy than
                # beam_size=1 at the cost of a bit more compute.
                segments, info = model.transcribe(
                    wav_path,
                    language="zh",
                    beam_size=5,
                    # Don't use VAD — for short browser recordings, the
                    # voice-activity detector often mistakes quiet speech
                    # for silence. Whisper's own decoder will skip silence
                    # naturally; we just want every millisecond analyzed.
                    vad_filter=False,
                    initial_prompt=(
                        "以下是销售对练的对话，销售员与客户之间的中文交流。"
                        "常见的词汇包括：检测设备、工业制造、汽车、精度、"
                        "交货周期、售后、价格、报价、技术演示、产能、维护成本。"
                    ),
                    condition_on_previous_text=False,
                )
                parts = [seg.text.strip() for seg in segments]
                return " ".join(p for p in parts if p), info

            text, info = await asyncio.to_thread(_run)
            print(
                f"[ASR-Local] {len(audio_data)}B {audio_mime} → "
                f"lang={info.language}({info.language_probability:.2f}) "
                f"text={text!r}"
            )
            return text
        except Exception as e:
            print(f"[ASR-Local] error: {e}")
            return ""
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            try:
                if wav_path != tmp_path:
                    os.unlink(wav_path)
            except Exception:
                pass

    # ==================== LLM (M2.7) ====================

    async def chat(
        self,
        messages: list,
        model: str = "MiniMax-M3",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[list] = None,
        reasoning_split: bool = True,
    ) -> str:
        """
        Chat with LLM (M2.7 highspeed by default).

        Args:
            messages: List of message dicts [{"role": "user/assistant", "content": "..."}]
            model: LLM model (default MiniMax-M3 with thinking disabled)
            temperature: Temperature (0-1)
            max_tokens: Max response tokens
            stream: Enable streaming
            tools: List of tool definitions for function calling
            reasoning_split: If True, send `reasoning_split=True` so the server
                returns the model's <think>...</think> block in a separate
                `reasoning_content` field instead of polluting `content`. This
                keeps the streaming pipeline's user-visible text clean.

        Returns:
            LLM response text, or JSON with tool_calls if function calling triggered
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if reasoning_split:
            # 官方文档查证（https://platform.minimaxi.com/docs/api-reference/text-anthropic-api）：
            # - M3 默认 thinking 关闭，可通过 `thinking: {"type": "adaptive"}` 开启
            # - M2.x thinking 不可关闭（即使传 disabled 也无效，仍 6-10s）
            # - reasoning_split 把 <think> 块搬到独立字段，content 干净
            # 实测：M3 + thinking disabled + reasoning_split = TTFT 2.6s，content 干净
            payload["reasoning_split"] = True
            # M3 走 anthropic 兼容协议时，thinking 控制用 `thinking: {"type": "disabled"}`
            # M2.x 传这个参数会忽略，但不影响（顶层有 reasoning_split）
            payload["thinking"] = {"type": "disabled"}

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
        model: str = "MiniMax-M3",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        reasoning_split: bool = True,
    ) -> AsyncIterator[str]:
        """
        Stream chat with LLM.

        Args:
            messages: List of message dicts
            model: LLM model (default MiniMax-M3 with thinking disabled)
            temperature: Temperature
            max_tokens: Max tokens
            reasoning_split: Default True — sends `reasoning_split=True` so the
                server's <think>...</think> block is moved to a separate
                `reasoning_content` field, keeping `content` clean for the
                streaming pipeline.

        Yields:
            Response chunks (only `content` — reasoning_content is filtered out)
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if reasoning_split:
            # 官方文档查证（https://platform.minimaxi.com/docs/api-reference/text-anthropic-api）：
            # - M3 默认 thinking 关闭，可通过 `thinking: {"type": "adaptive"}` 开启
            # - M2.x thinking 不可关闭（即使传 disabled 也无效，仍 6-10s）
            # - reasoning_split 把 <think> 块搬到独立字段，content 干净
            # 实测：M3 + thinking disabled + reasoning_split = TTFT 2.6s，content 干净
            payload["reasoning_split"] = True
            # M3 走 anthropic 兼容协议时，thinking 控制用 `thinking: {"type": "disabled"}`
            # M2.x 传这个参数会忽略，但不影响（顶层有 reasoning_split）
            payload["thinking"] = {"type": "disabled"}

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
                                    # Only yield `content`. Skip `reasoning_content`
                                    # so the streaming pipeline never sees the
                                    # <think>...</think> chain-of-thought block.
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except:
                                continue

    async def chat_stream_with_tools(
        self,
        messages: list,
        tools: list = None,
        model: str = "MiniMax-M3",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        reasoning_split: bool = True,
    ) -> AsyncIterator:
        """
        Stream chat with tool/function calling support.

        Args:
            messages: List of message dicts
            tools: List of tool definitions
            model: LLM model (default MiniMax-M3 with thinking disabled)
            temperature: Temperature
            max_tokens: Max tokens
            reasoning_split: Default True — keeps `content` free of <think> blocks.

        Yields:
            Either string tokens (for regular content) or dicts with tool_calls
        """
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if reasoning_split:
            # 官方文档查证（https://platform.minimaxi.com/docs/api-reference/text-anthropic-api）：
            # - M3 默认 thinking 关闭，可通过 `thinking: {"type": "adaptive"}` 开启
            # - M2.x thinking 不可关闭（即使传 disabled 也无效，仍 6-10s）
            # - reasoning_split 把 <think> 块搬到独立字段，content 干净
            # 实测：M3 + thinking disabled + reasoning_split = TTFT 2.6s，content 干净
            payload["reasoning_split"] = True
            # M3 走 anthropic 兼容协议时，thinking 控制用 `thinking: {"type": "disabled"}`
            # M2.x 传这个参数会忽略，但不影响（顶层有 reasoning_split）
            payload["thinking"] = {"type": "disabled"}

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

    # ==================== Web Search (eSearch) ====================

    async def web_search(
        self,
        query: str,
        num_results: int = 5
    ) -> list:
        """
        Search the web using MiniMax eSearch API.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results with title, url, snippet
        """
        if not self.api_key:
            return []

        url = f"{self.base_url}/e_search"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "MiniMax-Search",
                    "query": query,
                    "num_results": num_results
                }
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("results", [])
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("snippet", ""),
                        "date": r.get("date", "")
                    }
                    for r in results
                ]
            else:
                print(f"Search API error: {response.status_code} - {response.text}")
                return []


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