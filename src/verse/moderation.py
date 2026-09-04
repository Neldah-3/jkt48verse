"""Moderasi konten: filter kata terlarang + whitelist emoji (port lib/moderation.ts)."""

import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import BannedWord
from src.database import get_session

EMOJI_WHITELIST = [
    "😃", "😀", "😱", "😎", "😑", "🤫", "🙃", "🤔", "😉", "😊", "😆", "😍", "🥰",
    "🤩", "😂", "🥳", "🤗", "🤓", "😭", "👌", "💪", "☝", "🙏", "👏", "🤲", "🤝", "👍",
]

LEET = {"4": "a", "@": "a", "3": "e", "1": "i", "!": "i", "0": "o", "5": "s", "$": "s", "7": "t"}

DEFAULT_BANNED = [
    "anjing", "bangsat", "kontol", "memek", "goblok", "tolol",
    "bajingan", "ngentot", "babi", "asu",
]

_words_cache: dict = {"words": None, "at": 0.0}


def normalize_text(s: str) -> str:
    out = s.lower()
    out = re.sub(r"[4@31!05$7]", lambda c: LEET.get(c.group(0), c.group(0)), out)
    out = re.sub(r"[^a-z\s]", "", out)
    out = re.sub(r"(.)\1{2,}", r"\1\1", out)
    return out


async def banned_words(session: AsyncSession) -> list[str]:
    import time

    now = time.monotonic()
    if _words_cache["words"] is not None and now - _words_cache["at"] < 60:
        return _words_cache["words"]
    result = await session.execute(select(BannedWord))
    words = [row.word.lower() for row in result.scalars()]
    if not words:
        words = DEFAULT_BANNED[:]
    _words_cache["words"] = words
    _words_cache["at"] = now
    return words


async def check_text(session: AsyncSession, text: str) -> tuple[bool, Optional[str]]:
    """Layer 1: filter kata. Return (blocked, matched_word)."""
    words = await banned_words(session)
    n = normalize_text(text)
    compact = re.sub(r"\s+", "", n)
    for w in words:
        if w in n or w in compact:
            return True, w
    return False, None


def check_emoji(text: str) -> tuple[bool, Optional[str]]:
    """Layer 2: hanya emoji whitelist yang boleh."""
    for ch in text:
        if ord(ch[0]) > 0x2000 and ch not in EMOJI_WHITELIST:
            # izinkan karakter tulisan biasa & tanda baca umum
            if not re.match(r"[\w\s.,!?()\-+*/=:;'\"@#%&$\u0000-\u2000]", ch):
                return False, ch
    return True, None


def rate_key(viewer: dict) -> str:
    return f"chat:{viewer.get('userId') or viewer.get('staffId') or 'guest'}"
