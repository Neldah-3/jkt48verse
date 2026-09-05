"""PostgreSQL (Supabase) utility for JKT48 scraper."""
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


def parse_date(date_value) -> Optional[datetime]:
    """Parse berbagai format tanggal; selalu tz-aware UTC. None bila kosong."""
    if date_value in (None, ""):
        return None
    if isinstance(date_value, datetime):
        return date_value if date_value.tzinfo else date_value.replace(tzinfo=timezone.utc)
    if isinstance(date_value, str):
        try:
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            pass
        formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


# =====================================================================
# Sync ke SCHEMA KANONIK JKT48Verse (migration 002 + 003).
# Kunci upsert: kolom external id (members.external_id, news.source_id,
# schedules.source_id) — sehingga FK dari fitur komunitas tetap utuh.
# =====================================================================
MONTHS_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11,
    "desember": 12,
}


def _slugify(text: str) -> str:
    import re
    import unicodedata

    s = unicodedata.normalize("NFKD", text or "")
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s).strip().lower()
    return re.sub(r"[\s_]+", "-", s)


def _parse_indo_date(value) -> Optional[datetime]:
    """'06 Agustus 2008' → datetime UTC (fallback ISO)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    import re

    text = str(value).strip()
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", text)
    if m:
        day, mon, year = int(m.group(1)), MONTHS_ID.get(m.group(2).lower()), int(m.group(3))
        if mon:
            try:
                return datetime(year, mon, day, tzinfo=timezone.utc)
            except ValueError:
                return None
    return parse_date(text)


def _slug_from_href(href: str, name: str) -> str:
    """href '/member/detail?member=abigail-rachel-1&type=PASSION' → 'abigail-rachel'."""
    import re
    from urllib.parse import parse_qs, urlparse

    slug = None
    if href:
        try:
            qs = parse_qs(urlparse(href).query)
            cand = (qs.get("member") or [""])[0]
            slug = re.sub(r"-\d+$", "", cand) or None
        except Exception:
            slug = None
    return slug or _slugify(name)


def upsert_members(db: Database, data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    with db.conn.cursor() as cur:
        # ambil peta slug & external_id yang sudah ada
        cur.execute("SELECT id, slug, external_id FROM members")
        slug_to_row = {}
        ext_to_id = {}
        max_id = 0
        for mid, slug, ext in cur.fetchall():
            slug_to_row[slug] = mid
            if ext:
                ext_to_id[str(ext)] = mid
            max_id = max(max_id, mid)

        for item in data_list:
            try:
                external_id = str(item.get("id") or "").strip()
                name = item.get("name") or ""
                if not external_id and not name:
                    stats["errors"] += 1
                    continue
                slug = _slug_from_href(item.get("href") or item.get("url") or "", name)
                generation = None
                gen_raw = item.get("generation")
                if gen_raw is not None:
                    digits = "".join(ch for ch in str(gen_raw) if ch.isdigit())
                    generation = int(digits) if digits else None
                active = bool(item.get("active", True))
                payload = {
                    "external_id": external_id or None,
                    "slug": slug,
                    "name": name or slug,
                    "nickname": item.get("nickname") or name or slug,
                    "generation": generation,
                    "status": "regular" if active else "graduated",
                    "team": item.get("member_type") if item.get("member_type") not in (None, "", "JKT48") else None,
                    "birth_date": _parse_indo_date(item.get("birthdate")),
                    "blood_type": item.get("bloodType") or item.get("blood_type"),
                    "horoscope": item.get("horoscope"),
                    "height": item.get("height"),
                    "jikoshoukai": item.get("jiko"),
                    "socials": Json(item.get("socials") or {}),
                }

                row_id = ext_to_id.get(external_id) if external_id else None
                if row_id is None:
                    row_id = slug_to_row.get(slug)

                if row_id is not None:
                    cur.execute(
                        """
                        UPDATE members SET
                            external_id = COALESCE(%(external_id)s, external_id),
                            name = %(name)s,
                            nickname = %(nickname)s,
                            generation = %(generation)s,
                            status = CASE
                                WHEN %(status)s = 'graduated' THEN 'graduated'
                                ELSE members.status
                            END,
                            team = COALESCE(%(team)s, members.team),
                            birth_date = COALESCE(%(birth_date)s, members.birth_date),
                            blood_type = COALESCE(%(blood_type)s, members.blood_type),
                            horoscope = COALESCE(%(horoscope)s, members.horoscope),
                            height = COALESCE(%(height)s, members.height),
                            jikoshoukai = COALESCE(%(jikoshoukai)s, members.jikoshoukai),
                            socials = CASE
                                WHEN %(socials)s::jsonb = '{}'::jsonb THEN members.socials
                                ELSE COALESCE(members.socials, '{}'::jsonb) || %(socials)s::jsonb
                            END,
                            updated_at = NOW()
                        WHERE id = %(row_id)s
                        """,
                        {**payload, "row_id": row_id},
                    )
                    stats["updated"] += 1
                else:
                    max_id += 1
                    # hindari tabrakan slug dengan baris lain
                    base_slug, n = slug, 2
                    while base_slug in slug_to_row:
                        base_slug = f"{slug}-{n}"
                        n += 1
                    payload["slug"] = base_slug
                    payload["id"] = max_id
                    cur.execute(
                        """
                        INSERT INTO members (
                            id, slug, name, nickname, generation, status, team,
                            birth_date, blood_type, horoscope, height, jikoshoukai,
                            socials, external_id, show_birthday, created_at, updated_at
                        ) VALUES (
                            %(id)s, %(slug)s, %(name)s, %(nickname)s, %(generation)s,
                            %(status)s, %(team)s, %(birth_date)s, %(blood_type)s,
                            %(horoscope)s, %(height)s, %(jikoshoukai)s, %(socials)s,
                            %(external_id)s, TRUE, NOW(), NOW()
                        )
                        """,
                        payload,
                    )
                    slug_to_row[base_slug] = max_id
                    if external_id:
                        ext_to_id[external_id] = max_id
                    stats["inserted"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ Error syncing member: {e}")
        db.conn.commit()
    return stats


_NEWS_CATEGORY_MAP = [
    ("theater", "theater"), ("teater", "theater"),
    ("event", "event"), ("acara", "event"),
    ("release", "release"), ("single", "release"), ("album", "release"),
    ("birthday", "birthday"), ("ulang tahun", "birthday"),
]


def _news_category(raw: str) -> str:
    text = (raw or "").lower()
    for keyword, cat in _NEWS_CATEGORY_MAP:
        if keyword in text:
            return cat
    return "other"


def upsert_news(db: Database, data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    with db.conn.cursor() as cur:
        cur.execute("SELECT source_id FROM news WHERE source_id IS NOT NULL")
        known_source = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT slug FROM news")
        used_slugs = {row[0] for row in cur.fetchall()}

        for item in data_list:
            try:
                source_id = str(item.get("news_id") or "").strip()
                if not source_id:
                    stats["errors"] += 1
                    continue
                title = item.get("title") or ""
                if not title:
                    stats["errors"] += 1
                    continue
                base_slug = _slugify(title)[:150] or f"news-{source_id}"
                slug, n = base_slug, 2
                while slug in used_slugs:
                    slug = f"{base_slug}-{n}"
                    n += 1
                payload = {
                    "source_id": source_id,
                    "slug": slug,
                    "title": title,
                    "summary": item.get("short_description") or "",
                    "body": item.get("content_body") or "",
                    "category": _news_category(item.get("category")),
                    "published_at": parse_date(item.get("valid_date_from")) or datetime.now(timezone.utc),
                    "source_url": item.get("link") or None,
                }
                if source_id in known_source:
                    cur.execute(
                        """
                        UPDATE news SET
                            title = %(title)s,
                            summary = %(summary)s,
                            body = %(body)s,
                            category = %(category)s,
                            published_at = %(published_at)s,
                            source_url = COALESCE(%(source_url)s, source_url)
                        WHERE source_id = %(source_id)s
                        """,
                        payload,
                    )
                    stats["updated"] += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO news (
                            slug, title, summary, body, category, is_highlighted,
                            views, published_at, source_id, source_url
                        ) VALUES (
                            %(slug)s, %(title)s, %(summary)s, %(body)s, %(category)s,
                            FALSE, 0, %(published_at)s, %(source_id)s, %(source_url)s
                        )
                        """,
                        payload,
                    )
                    known_source.add(source_id)
                    used_slugs.add(slug)
                    stats["inserted"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ Error syncing news: {e}")
        db.conn.commit()
    return stats


_EVENT_TYPE_MAP = {
    "THEATER": "theater",
    "CONCERT": "concert",
    "KONSER": "concert",
    "EVENT": "event",
    "EXCLUSIVE": "event",
    "MEDIA": "media",
}


def upsert_events(db: Database, data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    """Sync jadwal/teater jkt48.com → tabel `schedules` + `schedule_members`."""
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    with db.conn.cursor() as cur:
        # peta source_id → schedule.id
        cur.execute("SELECT source_id, id FROM schedules WHERE source_id IS NOT NULL")
        src_to_id = {row[0]: row[1] for row in cur.fetchall()}
        # peta external_id jkt48 → members.id (untuk schedule_members)
        cur.execute("SELECT external_id, id FROM members WHERE external_id IS NOT NULL")
        ext_to_member = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM schedules")
        max_id = cur.fetchone()[0]

        for item in data_list:
            try:
                source_id = str(item.get("id") or "").strip()
                title = item.get("title") or ""
                if not source_id or not title:
                    stats["errors"] += 1
                    continue
                start_at = parse_date(item.get("date"))
                if start_at is None:
                    stats["errors"] += 1
                    print(f"  ⚠️  Event tanpa tanggal valid dilewati: {title[:60]}")
                    continue
                raw_type = str(item.get("type") or "EVENT").upper()
                sched_type = _EVENT_TYPE_MAP.get(raw_type, "event")
                label = item.get("label") or ""
                url = item.get("url") or ""
                description_bits = [b for b in [label, url] if b]
                payload = {
                    "source_id": source_id,
                    "title": title[:200],
                    "type": sched_type,
                    "start_at": start_at,
                    "setlist": item.get("setlistId") or item.get("setlist_id"),
                    "description": " · ".join(description_bits) or None,
                }
                if source_id in src_to_id:
                    sched_id = src_to_id[source_id]
                    cur.execute(
                        """
                        UPDATE schedules SET
                            title = %(title)s,
                            type = %(type)s,
                            start_at = %(start_at)s,
                            setlist = COALESCE(%(setlist)s, setlist),
                            description = COALESCE(%(description)s, description)
                        WHERE id = %(id)s
                        """,
                        {**payload, "id": sched_id},
                    )
                    stats["updated"] += 1
                else:
                    max_id += 1
                    sched_id = max_id
                    cur.execute(
                        """
                        INSERT INTO schedules (
                            id, title, type, start_at, setlist, description,
                            ticket_status, source_id, created_at
                        ) VALUES (
                            %(id)s, %(title)s, %(type)s, %(start_at)s, %(setlist)s,
                            %(description)s, 'unknown', %(source_id)s, NOW()
                        )
                        """,
                        {**payload, "id": sched_id},
                    )
                    src_to_id[source_id] = sched_id
                    stats["inserted"] += 1

                # lineup member: id eksternal jkt48 → members.id
                member_ids = item.get("memberIds") or []
                if member_ids:
                    cur.execute("DELETE FROM schedule_members WHERE schedule_id = %s", (sched_id,))
                    for mid in member_ids:
                        member_pk = ext_to_member.get(str(mid))
                        if member_pk is None:
                            continue
                        cur.execute(
                            """
                            INSERT INTO schedule_members (schedule_id, member_id)
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                            """,
                            (sched_id, member_pk),
                        )
            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ Error syncing schedule: {e}")
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
