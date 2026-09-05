"""AI Search: mode database (intent) + mode LLM (OpenRouter & kompatibel OpenAI API)."""

import re
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import and_, asc, extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import config
from src.logging_config import create_logger
from src.models import Encyclopedia, Glossary, Member, Motivation, News, Schedule
from src.verse.helpers import wib_midnight, wib_parts

logger = create_logger("verse_ai", __name__)

MONTHS_ID = [
    "januari", "februari", "maret", "april", "mei", "juni",
    "juli", "agustus", "september", "oktober", "november", "desember",
]
DAYS_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

STOPWORDS = {
    "yang", "apa", "siapa", "adalah", "itu", "dan", "dari", "untuk", "dengan",
    "tentang", "kapan", "dimana", "di", "mana", "berita", "jadwal", "member",
}


def _fmt_date_long(d, with_day: bool = True) -> str:
    p = wib_parts(d)
    base = f"{p['day']} {MONTHS_ID[p['month'] - 1]} {p['year']}"
    return f"{DAYS_ID[p['weekday']]}, {base}" if with_day else base


def _fmt_time(d) -> str:
    p = wib_parts(d)
    return f"{p['hour']:02d}:{p['minute']:02d}"


def _stop(question: str) -> list[str]:
    q = question.lower()
    q = re.sub(r"[?!,.]", " ", q)
    return [w for w in q.split() if len(w) > 2 and w not in STOPWORDS]


async def database_search(session: AsyncSession, question: str) -> dict[str, Any]:
    q = question.lower()
    sources: list[dict] = []
    now_p = wib_parts()

    # Intent: birthday
    if re.search(r"ulang tahun|ultah|birthday|lahir", q):
        month = now_p["month"]
        for i, m in enumerate(MONTHS_ID):
            if m in q:
                month = i + 1
                break
        if re.search(r"hari ini", q):
            rows = (
                await session.execute(
                    select(Member).where(
                        Member.show_birthday.is_(True),
                        extract("month", Member.birth_date) == now_p["month"],
                        extract("day", Member.birth_date) == now_p["day"],
                    )
                )
            ).scalars().all()
            for m in rows:
                sources.append({"label": m.name, "href": f"/member/{m.slug}", "kind": "member"})
            sources.append({"label": "Birthday Today", "href": "/birthday", "kind": "birthday"})
            answer = (
                f"Hari ini ({_fmt_date_long(None, False)}) ada {len(rows)} member yang berulang tahun: "
                + ", ".join(m.name for m in rows)
                + ". Kirim ucapanmu lewat halaman Birthday!"
                if rows
                else f"Tidak ada member yang berulang tahun hari ini ({_fmt_date_long(None, False)})."
            )
            return {"mode": "db", "question": question, "confidence": 0.97, "sources": sources, "answer": answer}
        rows = (
            await session.execute(
                select(Member)
                .where(Member.show_birthday.is_(True), extract("month", Member.birth_date) == month)
                .order_by(asc(extract("day", Member.birth_date)))
            )
        ).scalars().all()
        for m in rows[:8]:
            sources.append({"label": m.name, "href": f"/member/{m.slug}", "kind": "member"})
        sources.append({"label": "Kalender Birthday", "href": f"/birthday?tab=calendar&month={month}", "kind": "birthday"})
        answer = (
            f"Member yang berulang tahun di bulan {MONTHS_ID[month - 1]}: "
            + ", ".join(f"{m.name} ({m.birth_date.day} {MONTHS_ID[month - 1][:3]})" for m in rows)
            if rows
            else f"Belum ada data ulang tahun member di bulan {MONTHS_ID[month - 1]}."
        )
        return {"mode": "db", "question": question, "confidence": 0.95, "sources": sources, "answer": answer}

    # Intent: generation
    gen = re.search(r"generasi\s*(\d{1,2})|gen\s*(\d{1,2})", q)
    if gen:
        g = int(gen.group(1) or gen.group(2))
        rows = (
            await session.execute(
                select(Member)
                .where(Member.generation == g, Member.status.in_(["regular", "trainee"]))
                .order_by(asc(Member.name))
            )
        ).scalars().all()
        for m in rows[:10]:
            sources.append({"label": m.name, "href": f"/member/{m.slug}", "kind": "member"})
        sources.append({"label": f"Katalog Gen {g}", "href": f"/member?gen={g}", "kind": "member"})
        answer = (
            f"Generasi {g} JKT48 memiliki {len(rows)} member aktif: "
            + ", ".join(f"{m.name} ({m.nickname})" for m in rows)
            if rows
            else f"Tidak ditemukan member aktif dari generasi {g} di database."
        )
        return {"mode": "db", "question": question, "confidence": 0.96 if rows else 0.5, "sources": sources, "answer": answer}

    # Intent: schedule
    if re.search(r"jadwal|theater|show|konser|event|minggu (depan|ini)|besok|hari ini", q):
        start = wib_midnight(now_p["year"], now_p["month"], now_p["day"])
        end = start + timedelta(days=7)
        label = "7 hari ke depan"
        if re.search(r"besok", q):
            start = start + timedelta(days=1)
            end = start + timedelta(days=1)
            label = "besok"
        elif re.search(r"hari ini", q):
            end = start + timedelta(days=1)
            label = "hari ini"
        elif re.search(r"minggu depan", q):
            start = start + timedelta(days=(7 - now_p["weekday"]))
            end = start + timedelta(days=7)
            label = "minggu depan"
        type_filter = None
        if re.search(r"theater", q):
            type_filter = "theater"
        elif re.search(r"konser", q):
            type_filter = "concert"
        elif re.search(r"event|m&g|meet", q):
            type_filter = "event"
        conds = [Schedule.start_at >= start, Schedule.start_at < end]
        if type_filter:
            conds.append(Schedule.type == type_filter)
        rows = (
            await session.execute(
                select(Schedule).where(and_(*conds)).order_by(asc(Schedule.start_at)).limit(8)
            )
        ).scalars().all()
        for s in rows:
            sources.append({"label": s.title, "href": f"/schedule/{s.id}", "kind": "schedule"})
        sources.append({"label": "Kalender Jadwal", "href": "/schedule", "kind": "schedule"})
        answer = (
            f"Jadwal {type_filter or 'agenda'} {label}: "
            + "; ".join(
                f"{s.title} — {_fmt_date_long(s.start_at, False)} {_fmt_time(s.start_at)} WIB di {s.location or '-'}"
                for s in rows
            )
            if rows
            else f"Belum ada jadwal {type_filter or ''} untuk {label}."
        )
        return {"mode": "db", "question": question, "confidence": 0.93, "sources": sources, "answer": answer}

    # Fuzzy: glossary → member → news → encyclopedia → motivation
    terms = _stop(question)
    likes = [f"%{t}%" for t in terms]

    def any_like(*cols):
        return or_(*[col.ilike(l) for l in likes for col in cols])

    if likes:
        gl = (
            await session.execute(select(Glossary).where(any_like(Glossary.term)).limit(3))
        ).scalars().all()
        if gl:
            sources.append({"label": "Wota Culture", "href": "/encyclopedia/wota-culture", "kind": "encyclopedia"})
            return {
                "mode": "db", "question": question, "confidence": 0.94, "sources": sources,
                "answer": " ".join(f"{g.term}: {g.meaning}" for g in gl),
            }
        mem = (
            await session.execute(
                select(Member).where(any_like(Member.name, Member.nickname)).limit(3)
            )
        ).scalars().all()
        if mem:
            for m in mem:
                sources.append({"label": m.name, "href": f"/member/{m.slug}", "kind": "member"})
            m = mem[0]
            born = f", lahir {_fmt_date_long(str(m.birth_date) + 'T00:00:00+07:00', False)}" if m.birth_date else ""
            height = f", tinggi {m.height}" if m.height else ""
            return {
                "mode": "db", "question": question, "confidence": 0.9, "sources": sources,
                "answer": f"{m.name} ({m.nickname}) adalah member JKT48 generasi {m.generation or '-'} "
                          f"berstatus {m.status.upper()}{born}{height}. Jikoshoukai: \u201c{m.jikoshoukai or '-'}\u201d.",
            }
        nw = (
            await session.execute(
                select(News).where(any_like(News.title, News.body)).limit(3)
            )
        ).scalars().all()
        if nw:
            for n in nw:
                sources.append({"label": n.title, "href": f"/news/{n.slug}", "kind": "news"})
            return {
                "mode": "db", "question": question, "confidence": 0.88, "sources": sources,
                "answer": " ".join(f"{n.title}: {n.summary}" for n in nw),
            }
        enc = (
            await session.execute(
                select(Encyclopedia).where(any_like(Encyclopedia.title, Encyclopedia.content)).limit(2)
            )
        ).scalars().all()
        if enc:
            for e in enc:
                sources.append({"label": e.title, "href": f"/encyclopedia/{e.slug}", "kind": "encyclopedia"})
            e = enc[0]
            content = e.content or ""
            idx = content.lower().find(terms[0])
            if idx < 0:
                idx = 0
            snippet = content[max(0, idx - 80) : idx + 260]
            snippet = snippet.replace("#", "").replace("*", "").strip()
            return {
                "mode": "db", "question": question, "confidence": 0.82, "sources": sources,
                "answer": f"Dari Encyclopedia \u201c{e.title}\u201d: …{snippet}…",
            }
        mo = (
            await session.execute(select(Motivation).where(any_like(Motivation.quote)).limit(1))
        ).scalars().all()
        if mo:
            sources.append({"label": "Motivation", "href": "/motivation", "kind": "motivation"})
            return {
                "mode": "db", "question": question, "confidence": 0.8, "sources": sources,
                "answer": f"\u201c{mo[0].quote}\u201d — {mo[0].author or 'JKT48Verse'}",
            }

    return {
        "mode": "db", "question": question, "confidence": 0.2, "sources": [],
        "answer": "Aku belum menemukan jawaban di database JKT48Verse. Coba gunakan mode LLM AI Search untuk penjelasan lebih luas, atau ubah kata kuncimu.",
    }


def llm_configured() -> bool:
    return bool(config.llm_api_key)


async def llm_search(session: AsyncSession, question: str) -> dict[str, Any]:
    db_ctx = await database_search(session, question)
    if not llm_configured():
        return {
            "mode": "llm",
            "question": question,
            "confidence": db_ctx["confidence"],
            "sources": db_ctx["sources"],
            "fallback": True,
            "model": "belum dikonfigurasi",
            "answer": (
                "Mode LLM belum aktif di server ini (atur LLM_API_KEY, LLM_BASE_URL, LLM_MODEL "
                f"di file .env; default provider: OpenRouter). Sementara itu, hasil dari Database AI: {db_ctx['answer']}"
            ),
        }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{config.llm_base_url.rstrip('/')}/chat/completions",
                headers={
                    "content-type": "application/json",
                    "authorization": f"Bearer {config.llm_api_key}",
                },
                json={
                    "model": config.llm_model,
                    "temperature": config.llm_temperature,
                    "messages": [
                        {"role": "system", "content": config.llm_system_prompt},
                        {
                            "role": "user",
                            "content": f"Konteks database (mungkin kosong): {db_ctx['answer']}\n\nPertanyaan: {question}",
                        },
                    ],
                },
            )
            data = res.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
            if not text:
                raise RuntimeError((data.get("error") or {}).get("message", "Respon kosong"))
            return {
                "mode": "llm", "question": question, "confidence": 0.7,
                "sources": db_ctx["sources"], "model": config.llm_model, "answer": text,
            }
    except Exception as e:
        logger.warning(f"LLM search gagal: {e}")
        return {
            "mode": "llm", "question": question, "confidence": 0.3,
            "sources": db_ctx["sources"], "model": config.llm_model, "fallback": True,
            "answer": f"LLM tidak dapat dihubungi ({e}). Hasil Database AI: {db_ctx['answer']}",
        }
