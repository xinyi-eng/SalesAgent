"""
Industry Brief API endpoints.

- GET    /api/v1/briefs                      — list briefs (paginated, newest first)
- POST   /api/v1/briefs/generate             — generate a new brief via REAL RSS + LLM summary
- GET    /api/v1/briefs/today                — today's briefs grouped by industry
- GET    /api/v1/briefs/subscriptions        — get current user's subscriptions
- PUT    /api/v1/briefs/subscriptions        — update current user's subscriptions
- POST   /api/v1/briefs/refresh              — manually trigger fetch+push for user
- GET    /api/v1/briefs/{brief_id}           — full brief details
- GET    /api/v1/briefs/{brief_id}/pdf       — render brief as PDF
- DELETE /api/v1/briefs/{brief_id}           — remove a brief
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models import IndustryBrief, User, Notification
from app.schemas.practice import (
    BriefDetail,
    BriefGenerateRequest,
    BriefItem,
    BriefSummary,
    BriefSubscriptionsUpdate,
    TodayBriefs,
)
from app.services.real_brief import generate_real_brief
from app.services.industry_brief import generate_brief  # legacy fallback
from app.services.report_pdf import render_report_pdf

router = APIRouter(prefix="/briefs", tags=["briefs"])


def _to_summary(b: IndustryBrief) -> BriefSummary:
    return BriefSummary(
        id=b.id,
        title=b.title,
        industry=b.industry,
        keywords=b.keywords,
        item_count=len(b.items or []),
        takeaway_count=len(b.key_takeaways or []),
        status=b.status or "ready",
        created_at=b.created_at or datetime.utcnow(),
    )


def _to_detail(b: IndustryBrief) -> BriefDetail:
    items_data = b.items or []
    items = [BriefItem(**it) for it in items_data if isinstance(it, dict)]
    return BriefDetail(
        id=b.id,
        title=b.title,
        industry=b.industry,
        keywords=b.keywords,
        item_count=len(items),
        takeaway_count=len(b.key_takeaways or []),
        status=b.status or "ready",
        created_at=b.created_at or datetime.utcnow(),
        summary=b.summary,
        items=items,
        key_takeaways=list(b.key_takeaways or []),
        error=b.error,
    )


@router.get("", response_model=List[BriefSummary])
async def list_briefs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """List industry briefs, newest first."""
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    rows = (
        db.query(IndustryBrief)
        .order_by(desc(IndustryBrief.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [_to_summary(r) for r in rows]


@router.post("/generate", response_model=BriefDetail, status_code=status.HTTP_201_CREATED)
async def generate_briefendpoint(
    request: BriefGenerateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    生成新简报（v2：真实 RSS 源 + LLM 摘要润色）。

    真实数据流：
      1. news_fetcher.fetch_industry_news(industry, keywords)
         → 拉 Google News RSS + 36kr/虎嗅/IT之家/财新
      2. LLM 对每条新闻做 1-2 句事实摘要（限 token）
      3. 存 DB
      4. 推站内通知"你有 1 份新简报"
    """
    try:
        data = await generate_real_brief(
            industry=request.industry,
            keywords=request.keywords,
            max_news=8,
            hours=48,
        )
    except Exception as e:
        print(f"[briefs] real fetch failed: {e}, falling back to legacy")
        try:
            legacy = await generate_brief(
                industry=request.industry,
                keywords=request.keywords,
                title=request.title,
            )
            data = {
                **legacy,
                "is_legacy_ai": True,
                "news_count": len(legacy.get("items", [])),
            }
        except Exception as e2:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"简报生成失败: {e2}",
            )

    brief = IndustryBrief(
        title=data["title"],
        industry=data.get("industry") or request.industry,
        keywords=data.get("keywords") or (request.keywords or ""),
        summary=data.get("summary") or "",
        items=data.get("items") or [],
        key_takeaways=data.get("key_takeaways") or [],
        news_count=data.get("news_count", 0),
        is_legacy_ai=bool(data.get("is_legacy_ai", False)),
        brief_date=datetime.utcnow(),
        status="ready",
        generated_by=current_user.id if current_user else None,
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)

    if current_user:
        notif = Notification(
            user_id=current_user.id,
            type="brief_ready",
            title=f"📰 新简报：{data.get('industry')}",
            body=f"已生成 {data.get('news_count', 0)} 条 {data.get('industry')} 行业新闻",
            link=f"/briefs/{brief.id}",
        )
        db.add(notif)
        db.commit()

    return _to_detail(brief)


@router.get("/today", response_model=TodayBriefs)
async def get_today_briefs(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """今日（按 UTC 日期）所有生成的简报，按行业分组。"""
    today = datetime.utcnow().date()
    rows = (
        db.query(IndustryBrief)
        .filter(IndustryBrief.brief_date >= datetime(today.year, today.month, today.day))
        .order_by(desc(IndustryBrief.created_at))
        .all()
    )
    by_industry: dict = {}
    for r in rows:
        ind = r.industry or "其他"
        by_industry.setdefault(ind, []).append(_to_summary(r))
    return TodayBriefs(date=today.isoformat(), industries=by_industry)


@router.get("/subscriptions", response_model=BriefSubscriptionsUpdate)
async def get_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return BriefSubscriptionsUpdate(
        subscriptions=current_user.brief_subscriptions or []
    )


@router.put("/subscriptions", response_model=BriefSubscriptionsUpdate)
async def update_subscriptions(
    payload: BriefSubscriptionsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valid_industries = {
        "制造业", "科技软件", "金融", "医疗健康",
        "教育培训", "零售电商", "建筑工程", "物流运输",
        "能源化工", "通用",
    }
    for sub in payload.subscriptions:
        if sub.industry not in valid_industries:
            raise HTTPException(
                status_code=400,
                detail=f"未知行业: {sub.industry}。有效值: {list(valid_industries)}"
            )

    import json as _json
    new_value = [s.model_dump() for s in payload.subscriptions]
    # SQLAlchemy JSON column on SQLite needs explicit mutation flag
    current_user.brief_subscriptions = new_value
    db.add(current_user)
    db.flush()
    # 强制序列化/反序列化触发 SQLAlchemy 检测到变化
    db.commit()
    db.refresh(current_user)
    # 再次确认 DB 已存
    db.close()
    return BriefSubscriptionsUpdate(subscriptions=current_user.brief_subscriptions or [])


@router.post("/refresh", response_model=List[BriefSummary])
async def refresh_briefs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subs = current_user.brief_subscriptions or []
    if not subs:
        return []

    created: List[BriefSummary] = []
    for sub in subs:
        industry = sub.get("industry", "通用")
        keywords = sub.get("keywords", "")
        try:
            data = await generate_real_brief(
                industry=industry, keywords=keywords, max_news=8, hours=48,
            )
            brief = IndustryBrief(
                title=data["title"],
                industry=industry,
                keywords=keywords,
                summary=data.get("summary", ""),
                items=data.get("items", []),
                key_takeaways=data.get("key_takeaways", []),
                news_count=data.get("news_count", 0),
                brief_date=datetime.utcnow(),
                status="ready",
                generated_by=current_user.id,
            )
            db.add(brief)
            db.commit()
            db.refresh(brief)
            created.append(_to_summary(brief))
        except Exception as e:
            print(f"[briefs.refresh] {industry} failed: {e}")
            continue

    if created:
        notif = Notification(
            user_id=current_user.id,
            type="brief_ready",
            title=f"📰 {len(created)} 份新简报已生成",
            body=f"今日行业动态已更新，含 {sum(b.item_count for b in created)} 条新闻",
            link="/briefs",
        )
        db.add(notif)
        db.commit()

    return created


@router.get("/{brief_id}", response_model=BriefDetail)
async def get_brief(
    brief_id: str,
    db: Session = Depends(get_db),
):
    row = db.query(IndustryBrief).filter(IndustryBrief.id == brief_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简报不存在")
    return _to_detail(row)


@router.delete("/{brief_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brief(
    brief_id: str,
    db: Session = Depends(get_db),
):
    row = db.query(IndustryBrief).filter(IndustryBrief.id == brief_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简报不存在")
    db.delete(row)
    db.commit()


@router.get("/{brief_id}/pdf")
async def export_brief_pdf(
    brief_id: str,
    db: Session = Depends(get_db),
):
    row = db.query(IndustryBrief).filter(IndustryBrief.id == brief_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简报不存在")

    items = row.items or []
    knowledge_refs = []
    for it in items:
        if not isinstance(it, dict):
            continue
        knowledge_refs.append({
            "category": "industry",
            "source": it.get("source") or "行业情报",
            "chapter": it.get("source_level") or "L3",
            "section": it.get("published_at") or "",
            "excerpt": (it.get("title", "") + ((" — " + it["summary"]) if it.get("summary") else ""))[:200],
            "relevance": 0.8,
            "url": it.get("url", ""),
        })

    summary = {
        "session_id": row.id,
        "scenario_name": row.title,
        "role_config": {},
        "overall_score": 0,
        "situation_score": 0,
        "problem_score": 0,
        "implication_score": 0,
        "need_payoff_score": 0,
        "key_strengths": list(row.key_takeaways or []),
        "areas_for_improvement": [],
        "next_practice_focus": row.summary or "",
        "knowledge_refs": knowledge_refs,
        "raw_evaluation": row.summary or "",
        "context": [],
    }
    pdf_bytes = render_report_pdf(summary)
    filename = f"industry-brief-{brief_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
