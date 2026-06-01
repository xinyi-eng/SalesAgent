"""
API v1 package
"""
from fastapi import APIRouter
from app.api.v1 import practice, auth, profile, history, knowledge

router = APIRouter()

# Include all API routers
router.include_router(practice.router)
router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(history.router)
router.include_router(knowledge.router)