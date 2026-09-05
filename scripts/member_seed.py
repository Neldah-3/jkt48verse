"""Translate the checked-in scraper snapshot into canonical Member fields."""

import re
import unicodedata
from datetime import date
from urllib.parse import parse_qs, urlparse

MONTHS_ID = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}


def birth_date(value: str | None) -> date | None:
    if not value:
        return None
    match = re.fullmatch(r"(\d{1,2})\s+(\w+)\s+(\d{4})", value.strip())
    try:
        if match:
            day, month, year = match.groups()
            return date(int(year), MONTHS_ID[month.lower()], int(day))
        return date.fromisoformat(value[:10])
    except (KeyError, ValueError):
        raise ValueError(f"Invalid member birth date: {value!r}") from None


def member_fields(row: dict) -> dict:
    name = str(row.get("name") or "").strip()
    external_id = str(row.get("id") or "").strip()
    if not name or not external_id:
        raise ValueError("A member seed row needs a name and external id")
    href = row.get("href") or ""
    source_slug = (parse_qs(urlparse(href).query).get("member") or [""])[0]
    slug = re.sub(r"-\d+$", "", source_slug)
    if not slug:
        text = unicodedata.normalize("NFKD", name)
        text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
        slug = re.sub(r"[\s_]+", "-", text)
    if not slug or len(slug) > 80:
        raise ValueError(f"Invalid member slug for {name!r}")
    member_type = row.get("member_type") or ""
    active = row.get("active") is True
    status = "trainee" if member_type == "TRAINEE" else "regular"
    if not active:
        status = "graduated"
    generation = str(row.get("generation") or "").strip()
    return {
        "external_id": external_id,
        "slug": slug,
        "name": name,
        "nickname": row.get("nickname") or name.split()[0],
        "generation": int(generation) if generation else None,
        "status": status,
        "team": member_type
        if member_type not in ("", "JKT48", "EXMEMBER", "TRAINEE")
        else None,
        "birth_date": birth_date(row.get("birthdate")),
        "height": row.get("height"),
        "blood_type": row.get("bloodType"),
        "horoscope": row.get("horoscope"),
        "jikoshoukai": row.get("jiko"),
        "socials": row.get("socials") or {},
    }
