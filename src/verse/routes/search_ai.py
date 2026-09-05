"""AI Search endpoints (kuota harian WIB + feedback)."""


from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import config
from src.database import get_session
from src.models import AISearchHistory
from src.verse import ai
from src.verse.deps import get_viewer
from src.verse.helpers import wib_midnight, wib_parts

router = APIRouter()


class AISearchIn(BaseModel):
    mode: str = "db"  # db | llm
    question: str


@router.post("/ai/search")
async def ai_search(
    data: AISearchIn,
    request: Request,
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    q = data.question.strip()[:200]
    if len(q) < 3:
        return {"ok": False, "error": "Pertanyaan terlalu pendek."}
    limit = (
        config.ai_search_daily_limit_user if viewer.get("userId") else config.ai_search_daily_limit_guest
    )
    client_key = request.headers.get("x-client-key") or (request.client.host if request.client else "anon")
    p = wib_parts()
    since = wib_midnight(p["year"], p["month"], p["day"])
    user_filter = (
        AISearchHistory.user_seq == viewer["userId"]
        if viewer.get("userId")
        else AISearchHistory.client_key == client_key[:64]
    )
    used = (
        await session.execute(
            select(func.count())
            .select_from(AISearchHistory)
            .where(and_(user_filter, AISearchHistory.created_at >= since))
        )
    ).scalar() or 0
    if used >= limit:
        return {"ok": False, "error": f"Kuota harian habis ({limit}/{limit}). Reset pukul 00:00 WIB.", "code": "RATE_LIMIT"}

    answer = (
        await ai.llm_search(session, q)
        if data.mode == "llm"
        else await ai.database_search(session, q)
    )
    if data.mode == "db" and answer["confidence"] < 0.5:
        # fallback otomatis ke LLM bila tersedia
        if ai.llm_configured():
            llm_ans = await ai.llm_search(session, q)
            llm_ans["fallback"] = True
            answer = llm_ans

    remaining = max(0, limit - used - 1)
    session.add(
        AISearchHistory(
            user_seq=viewer.get("userId"),
            client_key=client_key[:64],
            mode=data.mode,
            query=q,
            answer=answer.get("answer", "")[:2000],
        )
    )
    return {"ok": True, "data": {**answer, "remaining": remaining}}


class FeedbackIn(BaseModel):
    query: str
    value: int  # 1 | -1


@router.post("/ai/feedback")
async def ai_feedback(
    data: FeedbackIn,
    request: Request,
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    client_key = request.headers.get("x-client-key") or (request.client.host if request.client else "anon")
    row = (
        await session.execute(
            select(AISearchHistory)
            .where(
                AISearchHistory.query == data.query[:200],
                AISearchHistory.user_seq == viewer["userId"]
                if viewer.get("userId")
                else AISearchHistory.client_key == client_key[:64],
            )
            .order_by(AISearchHistory.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row:
        row.feedback = 1 if data.value > 0 else -1
    return {"ok": True}


@router.get("/ai/configured")
async def ai_configured():
    """Status AI: cukup 1 key saja yang dibutuhkan; sisanya jadi cadangan anti-limit."""
    from src.verse.llm_router import get_router

    router = get_router()
    return {
        "configured": router.configured,
        "keys": router.key_count,
        "model": config.llm_model,
        "baseUrl": config.llm_base_url,
        "moderation": ai.moderation_enabled(),
    }
