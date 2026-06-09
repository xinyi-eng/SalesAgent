"""
API v1 package
"""
from fastapi import APIRouter
from app.api.v1 import practice, auth, profile, history, knowledge, spin, tts, briefs, notifications

router = APIRouter()

# Include all API routers
router.include_router(practice.router)
router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(history.router)
router.include_router(knowledge.router)
router.include_router(spin.router)
router.include_router(tts.router)
router.include_router(briefs.router)
router.include_router(notifications.router)