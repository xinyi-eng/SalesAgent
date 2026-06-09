"""
TTS API v1 - 语音合成预览
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.services.llm import get_minimax_service

router = APIRouter(prefix="/tts", tags=["tts"])


class TTSPreviewRequest(BaseModel):
    """TTS预览请求"""
    voice_id: str = Field(..., description="声线ID")
    text: str = Field(default="您好，我是您的AI模拟客户。让我来了解一下您的产品。", description="预览文本")
    emotion: Optional[str] = Field(
        default="neutral",
        description="情绪: neutral/happy/sad/angry/fearful/disgusted/surprised",
    )
    speed: Optional[float] = Field(default=1.0, description="语速 0.5-2.0")


@router.post("/preview")
async def tts_preview(request: TTSPreviewRequest):
    """
    TTS声线预览接口
    返回音频数据用于前端播放

    支持情绪参数 (speech-2.8-hd/turbo)：
    neutral / happy / sad / angry / fearful / disgusted / surprised
    """
    try:
        minimax = get_minimax_service()
        if not minimax.api_key:
            raise HTTPException(status_code=500, detail="LLM API未配置")

        audio_data = await minimax.text_to_speech(
            text=request.text,
            model="speech-2.8-hd",
            voice=request.voice_id,
            speed=request.speed or 1.0,
            volume=1.0,
            pitch=1.0,
            format="mp3",
            emotion=request.emotion or "neutral",
        )

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
