"""
Notifications API — 站内通知中心
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models import User, Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: List[NotificationItem]
    unread_count: int


def _to_item(n: Notification) -> NotificationItem:
    return NotificationItem(
        id=n.id,
        type=n.type,
        title=n.title,
        body=n.body,
        link=n.link,
        is_read=bool(n.is_read),
        created_at=n.created_at or datetime.utcnow(),
    )


@router.get("", response_model=NotificationList)
async def list_notifications(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的最新通知。"""
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(desc(Notification.created_at))
        .limit(max(1, min(100, limit)))
        .all()
    )
    unread = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa
        .count()
    )
    return NotificationList(
        items=[_to_item(r) for r in rows],
        unread_count=unread,
    )


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    n.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa
    ).update({Notification.is_read: True})
    db.commit()
    return {"ok": True}
