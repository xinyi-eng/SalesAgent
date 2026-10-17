"""Offline regression tests for practice-chat text streaming."""
import unittest
from unittest.mock import AsyncMock, patch

from app.services.conversation import streaming


class _FakeMiniMax:
    """A deterministic LLM/TTS double that never makes network calls."""

    def __init__(self, tokens=("您好，", "我正在", "整理您的", "需求。")):
        self.stream_finished = False
        self._tokens = tokens

    async def chat_stream(self, messages, model):
        del messages, model
        for token in self._tokens:
            yield token
        self.stream_finished = True

    async def text_to_speech_stream(self, **kwargs):
        del kwargs
        if False:
            yield b""

    async def text_to_speech(self, **kwargs):
        del kwargs
        return b""


class StreamingTextUpdateTests(unittest.IsolatedAsyncioTestCase):
    async def test_sends_text_update_before_llm_stream_finishes(self):
        """The UI must receive cumulative text while the LLM is still yielding."""
        minimax = _FakeMiniMax()
        events = []

        async def websocket_send(event):
            events.append((event, minimax.stream_finished))

        async def websocket_send_binary(chunk):
            del chunk

        assembled = {
            "messages": [{"role": "system", "content": "test"}],
            "emotion": "neutral",
            "voice_modify": {},
            "breath_tag": "",
            "knowledge_refs": [],
        }

        with patch.object(
            streaming, "parallel_context_assembly", new=AsyncMock(return_value=assembled)
        ), patch(
            "app.websocket.manager.session_manager.get_session_info", return_value={}
        ):
            result = await streaming.stream_pipeline(
                websocket_send=websocket_send,
                websocket_send_binary=websocket_send_binary,
                session_id="test-session",
                user_text="请介绍一下产品",
                user_audio_data=None,
                user_audio_mime=None,
                client_id=None,
                minimax=minimax,
                handler=object(),
            )

        updates = [event for event, _ in events if event["type"] == "ai_streaming_update"]
        update_states = [finished for event, finished in events if event["type"] == "ai_streaming_update"]

        self.assertTrue(updates)
        self.assertIn(False, update_states)
        self.assertEqual(updates[-1]["content"], "您好，我正在整理您的需求。")
        self.assertEqual(result["full_response"], "您好，我正在整理您的需求。")
        self.assertEqual(events[-1][0]["type"], "ai_streaming_end")

    async def test_does_not_stream_reasoning_when_think_tag_is_split_across_tokens(self):
        """Split reasoning tags must not expose their contents in incremental updates."""
        minimax = _FakeMiniMax(("<thi", "nk>internal reasoning</think>", "您好"))
        events = []

        async def websocket_send(event):
            events.append(event)

        assembled = {
            "messages": [{"role": "system", "content": "test"}],
            "emotion": "neutral",
            "voice_modify": {},
            "breath_tag": "",
            "knowledge_refs": [],
        }

        with patch.object(
            streaming, "parallel_context_assembly", new=AsyncMock(return_value=assembled)
        ), patch(
            "app.websocket.manager.session_manager.get_session_info", return_value={}
        ):
            result = await streaming.stream_pipeline(
                websocket_send=websocket_send,
                websocket_send_binary=None,
                session_id="test-session",
                user_text="请介绍一下产品",
                user_audio_data=None,
                user_audio_mime=None,
                client_id=None,
                minimax=minimax,
                handler=object(),
            )

        updates = [event["content"] for event in events if event["type"] == "ai_streaming_update"]
        self.assertTrue(updates)
        self.assertTrue(all("internal reasoning" not in content for content in updates))
        self.assertEqual(updates[-1], "您好")
        self.assertEqual(result["full_response"], "您好")


if __name__ == "__main__":
    unittest.main()
