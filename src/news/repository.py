import math
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import News


class NewsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_news(self, item: dict):
        news_id = int(item["news_id"])
        result = await self.session.execute(select(News).where(News.news_id == news_id))
        news = result.scalar_one_or_none()
        payload = {
            "title": item.get("title", ""),
            "category": item.get("category", ""),
            "link": item.get("link", ""),
            "background_image": item.get("background_image"),
            "is_published": item.get("is_published", True),
            "valid_date_from": item.get("valid_date_from"),
            "content_body": item.get("content_body", ""),
            "short_description": item.get("short_description"),
        }
        if news:
            for k, v in payload.items():
                setattr(news, k, v)
        else:
            news = News(news_id=news_id, **payload)
            self.session.add(news)
        await self.session.flush()
        return news

    async def get_news(
        self,
        page: int = 1,
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        skip = (page - 1) * limit
        stmt = select(News)
        count_stmt = select(func.count()).select_from(News)
        if start_date:
            stmt = stmt.where(News.valid_date_from >= start_date)
            count_stmt = count_stmt.where(News.valid_date_from >= start_date)
        if end_date:
            stmt = stmt.where(News.valid_date_from <= end_date)
            count_stmt = count_stmt.where(News.valid_date_from <= end_date)

        stmt = stmt.order_by(News.valid_date_from.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        items = [n.to_dict() for n in result.scalars().all()]
        total = int((await self.session.execute(count_stmt)).scalar() or 0)
        total_page = math.ceil(total / limit) if limit > 0 else 0
        return {
            "data": items,
            "meta": {
                "page": page,
                "limit_per_page": limit,
                "total_page": total_page,
                "count_per_page": len(items),
                "count_total": total,
            },
        }

    async def get_news_by_link(self, link: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(select(News).where(News.link == link))
        news = result.scalar_one_or_none()
        return news.to_dict() if news else None
