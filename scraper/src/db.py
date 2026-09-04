"""PostgreSQL (Supabase) utility for JKT48 scraper."""
import json
import os
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg.types.json import Json


def _sync_database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required to sync scraper data")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Database:
    def __init__(self):
        self.uri = None
        self.conn = None

    def connect(self):
        try:
            self.uri = _sync_database_url()
            self.conn = psycopg.connect(self.uri)
            return True
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


def parse_date(date_value) -> datetime:
    if isinstance(date_value, datetime):
        return date_value
    if isinstance(date_value, str):
        try:
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            pass
        formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt)
            except ValueError:
                continue
    return datetime.now()


def upsert_members(db: Database, data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    sql = """
        INSERT INTO members (
            id, name, nickname, generation, jiko, active, href, img,
            birthdate, blood_type, horoscope, height, socials, member_type,
            member_code, created_at, updated_at
        ) VALUES (
            %(id)s, %(name)s, %(nickname)s, %(generation)s, %(jiko)s, %(active)s,
            %(href)s, %(img)s, %(birthdate)s, %(blood_type)s, %(horoscope)s,
            %(height)s, %(socials)s, %(member_type)s, %(member_code)s, NOW(), NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            nickname = EXCLUDED.nickname,
            generation = EXCLUDED.generation,
            jiko = EXCLUDED.jiko,
            active = EXCLUDED.active,
            href = EXCLUDED.href,
            img = EXCLUDED.img,
            birthdate = EXCLUDED.birthdate,
            blood_type = EXCLUDED.blood_type,
            horoscope = EXCLUDED.horoscope,
            height = EXCLUDED.height,
            socials = EXCLUDED.socials,
            member_type = EXCLUDED.member_type,
            member_code = EXCLUDED.member_code,
            updated_at = NOW()
        RETURNING (xmax = 0) AS inserted
    """
    with db.conn.cursor() as cur:
        for item in data_list:
            try:
                payload = {
                    "id": str(item.get("id")),
                    "name": item.get("name") or "",
                    "nickname": item.get("nickname"),
                    "generation": item.get("generation"),
                    "jiko": item.get("jiko"),
                    "active": bool(item.get("active", True)),
                    "href": item.get("href") or item.get("url"),
                    "img": item.get("img"),
                    "birthdate": item.get("birthdate"),
                    "blood_type": item.get("bloodType") or item.get("blood_type"),
                    "horoscope": item.get("horoscope"),
                    "height": item.get("height"),
                    "socials": Json(item.get("socials") or {}),
                    "member_type": item.get("member_type") or "JKT48",
                    "member_code": item.get("member_code"),
                }
                if not payload["id"]:
                    stats["errors"] += 1
                    continue
                cur.execute(sql, payload)
                inserted = cur.fetchone()[0]
                if inserted:
                    stats["inserted"] += 1
                else:
                    stats["updated"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ Error syncing member: {e}")
        db.conn.commit()
    return stats


def upsert_news(db: Database, data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    sql = """
        INSERT INTO news (
            news_id, title, category, link, background_image, is_published,
            valid_date_from, content_body, short_description
        ) VALUES (
            %(news_id)s, %(title)s, %(category)s, %(link)s, %(background_image)s,
            %(is_published)s, %(valid_date_from)s, %(content_body)s, %(short_description)s
        )
        ON CONFLICT (news_id) DO UPDATE SET
            title = EXCLUDED.title,
            category = EXCLUDED.category,
            link = EXCLUDED.link,
            background_image = EXCLUDED.background_image,
            is_published = EXCLUDED.is_published,
            valid_date_from = EXCLUDED.valid_date_from,
            content_body = EXCLUDED.content_body,
            short_description = EXCLUDED.short_description
        RETURNING (xmax = 0) AS inserted
    """
    with db.conn.cursor() as cur:
        for item in data_list:
            try:
                payload = {
                    "news_id": int(item.get("news_id")),
                    "title": item.get("title") or "",
                    "category": item.get("category") or "",
                    "link": item.get("link") or "",
                    "background_image": item.get("background_image"),
                    "is_published": bool(item.get("is_published", True)),
                    "valid_date_from": parse_date(item.get("valid_date_from")),
                    "content_body": item.get("content_body") or "",
                    "short_description": item.get("short_description"),
                }
                cur.execute(sql, payload)
                inserted = cur.fetchone()[0]
                if inserted:
                    stats["inserted"] += 1
                else:
                    stats["updated"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ Error syncing news: {e}")
        db.conn.commit()
    return stats


def upsert_events(db: Database, data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    event_sql = """
        INSERT INTO events (
            id, title, date, url, label, type, setlist_id, image_url, raw_data, created_at
        ) VALUES (
            %(id)s, %(title)s, %(date)s, %(url)s, %(label)s, %(type)s,
            %(setlist_id)s, %(image_url)s, %(raw_data)s, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            date = EXCLUDED.date,
            url = EXCLUDED.url,
            label = EXCLUDED.label,
            type = EXCLUDED.type,
            setlist_id = EXCLUDED.setlist_id,
            image_url = EXCLUDED.image_url,
            raw_data = EXCLUDED.raw_data
        RETURNING (xmax = 0) AS inserted
    """
    with db.conn.cursor() as cur:
        for item in data_list:
            try:
                event_id = str(item.get("id") or "")
                if not event_id:
                    stats["errors"] += 1
                    continue
                payload = {
                    "id": event_id,
                    "title": item.get("title") or "",
                    "date": parse_date(item.get("date")),
                    "url": item.get("url") or "",
                    "label": item.get("label") or "",
                    "type": item.get("type"),
                    "setlist_id": item.get("setlistId") or item.get("setlist_id"),
                    "image_url": item.get("imageUrl") or item.get("image_url"),
                    "raw_data": Json(item.get("raw_data") or {}),
                }
                cur.execute(event_sql, payload)
                inserted = cur.fetchone()[0]
                if inserted:
                    stats["inserted"] += 1
                else:
                    stats["updated"] += 1

                cur.execute("DELETE FROM event_members WHERE event_id = %s", (event_id,))
                for member_id in item.get("memberIds") or []:
                    cur.execute(
                        """
                        INSERT INTO event_members (event_id, member_id, role)
                        VALUES (%s, %s, 'member')
                        ON CONFLICT DO NOTHING
                        """,
                        (event_id, str(member_id)),
                    )
                for member_id in item.get("seitansaiIds") or []:
                    cur.execute(
                        """
                        INSERT INTO event_members (event_id, member_id, role)
                        VALUES (%s, %s, 'seitansai')
                        ON CONFLICT DO NOTHING
                        """,
                        (event_id, str(member_id)),
                    )
                for member_id in item.get("graduationIds") or []:
                    cur.execute(
                        """
                        INSERT INTO event_members (event_id, member_id, role)
                        VALUES (%s, %s, 'graduation')
                        ON CONFLICT DO NOTHING
                        """,
                        (event_id, str(member_id)),
                    )
            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ Error syncing event: {e}")
        db.conn.commit()
    return stats


def upsert_data(db: Database, collection_name: str, data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    if collection_name == "members":
        return upsert_members(db, data_list)
    if collection_name == "news":
        return upsert_news(db, data_list)
    if collection_name == "events":
        return upsert_events(db, data_list)
    raise ValueError(f"Unknown collection: {collection_name}")
