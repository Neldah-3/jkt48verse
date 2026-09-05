#!/usr/bin/env python3
"""Seeder PostgreSQL JKT48Verse (idempoten).

Menggantikan seeder lama berbasis MongoDB (scripts/seed_database.py) yang
tidak kompatibel dengan stack FastAPI + SQLAlchemy + PostgreSQL.

Data yang di-seed:
  --users      akun admin / moderator / fansdemo (email terverifikasi)
  --members    member kanonik dari frontend/data/members.json
  --setlists   setlist teater (tabel legacy yang masih dilayani)
  --content    encyclopedia, glossary, motivations, contributors
  --games      bank soal Quiz + Guess Member
  --all        semuanya (default bila tanpa flag)

Jalankan:
  export DATABASE_URL="postgresql://..."   # atau postgresql+asyncpg://
  python scripts/seed.py [--users] [--members] [--setlists] [--content] [--games] [--all]
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from src.database import database_instance  # noqa: E402
from src.models import (  # noqa: E402
    Contributor,
    Encyclopedia,
    Glossary,
    GuessQuestion,
    Member,
    Motivation,
    QuizQuestion,
    Setlist,
    User,
)

ROOT = Path(__file__).resolve().parent.parent


# =====================================================================
# USERS
# =====================================================================
# Password bawaan mengikuti DEPLOY.md — WAJIB diganti setelah deploy.
# Override via environment: ADMIN_PASSWORD / MODERATOR_PASSWORD / FANS_PASSWORD.
SEED_ACCOUNTS = [
    {
        "username": "admin",
        "role": "ADMIN",
        "email": "admin@jkt48verse.local",
        "name": "Administrator",
        "env": "ADMIN_PASSWORD",
        "default": "AdminJKT48verse2026",
    },
    {
        "username": "moderator",
        "role": "MODERATOR",
        "email": "moderator@jkt48verse.local",
        "name": "Moderator",
        "env": "MODERATOR_PASSWORD",
        "default": "ModeratorJKT48verse2026",
    },
    {
        "username": "fansdemo",
        "role": "MEMBER",
        "email": "fans@jkt48verse.local",
        "name": "Fans Demo",
        "env": "FANS_PASSWORD",
        "default": "FansDemoJKT48verse2026",
    },
]


async def seed_users(session) -> None:
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    for acc in SEED_ACCOUNTS:
        existing = (
            await session.execute(select(User).where(User.username == acc["username"]))
        ).scalar_one_or_none()
        password = os.environ.get(acc["env"], "") or acc["default"]
        if password == acc["default"] and os.environ.get("ENV") == "prod":
            print(f"  ⚠️  {acc['username']}: memakai password bawaan di PROD — set {acc['env']} & ganti segera!")
        if existing:
            existing.role = acc["role"]
            existing.is_email_verified = True
            print(f"  = user '{acc['username']}' sudah ada (role diset {acc['role']})")
            continue
        session.add(
            User(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                username=acc["username"],
                name=acc["name"],
                email=acc["email"],
                password=ctx.hash(password),
                provider="seed",
                role=acc["role"],
                is_email_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_active_at=datetime.now(timezone.utc),
            )
        )
        print(f"  + user '{acc['username']}' ({acc['role']}) dibuat")


# =====================================================================
# STAFF: 3 slot ADMIN + 10 slot MODERATOR (dari environment, all-or-nothing)
# =====================================================================
# Aturan: setiap slot butuh USERNAME + EMAIL + PASSWORD + ACCESS_CODE.
# Kalau satu saja kosong ⇒ slot = False (nonaktif) & akun tidak bisa login.
# Nilai dibaca persis (besar/kecil huruf & karakter dihitung).
async def seed_staff(session) -> None:
    from passlib.context import CryptContext

    from src.auth import staff_credentials

    staff_credentials.reload()  # baca ulang env setiap kali seeder dijalankan
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    print("  Slot kredensial (lengkap 4/4 = aktif, selain itu = false):")
    for slot in staff_credentials.report():
        if not slot["defined"]:
            mark = "·  false  "
        elif slot["active"]:
            mark = "✓  AKTIF  "
        else:
            mark = "✗  false  "
        print(f"    {mark} {slot['label']:<8} {slot['reason']}")

    active = staff_credentials.staff_credentials()
    created = updated = 0
    for cred in active:
        row = (
            await session.execute(
                select(User).where(
                    (User.username == cred.username) | (User.email == cred.email)
                )
            )
        ).scalar_one_or_none()
        if row:
            row.username = cred.username
            row.email = cred.email
            row.role = cred.role
            row.provider = staff_credentials.PROVIDER
            row.is_email_verified = True
            row.is_account_locked = False
            row.failed_login_attempts = 0
            if not row.password or not ctx.verify(cred.password, row.password):
                row.password = ctx.hash(cred.password)
            updated += 1
            print(f"  = {cred.label} → user '{cred.username}' disinkronkan ({cred.role})")
            continue
        session.add(
            User(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                username=cred.username,
                name=f"{'Admin' if cred.role == 'ADMIN' else 'Moderator'} {cred.slot}",
                email=cred.email,
                password=ctx.hash(cred.password),
                provider=staff_credentials.PROVIDER,
                role=cred.role,
                is_email_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_active_at=datetime.now(timezone.utc),
            )
        )
        created += 1
        print(f"  + {cred.label} → user '{cred.username}' dibuat ({cred.role})")

    # Nonaktifkan akun staff yang slot-nya sudah tidak lengkap / dihapus,
    # supaya benar-benar tidak bisa login (password dikosongkan).
    keep = {c.username for c in active} | {c.email for c in active}
    rows = (
        await session.execute(select(User).where(User.provider == staff_credentials.PROVIDER))
    ).scalars().all()
    disabled = 0
    for u in rows:
        if u.username in keep or (u.email or "") in keep:
            continue
        if u.password is not None:
            u.password = None
            disabled += 1
            print(f"  - user '{u.username}' DINONAKTIFKAN (slot kredensial tidak lengkap)")

    print(f"  staff: {created} baru, {updated} disinkronkan, {disabled} dinonaktifkan")


# =====================================================================
# MEMBERS (kanonik) — dari frontend/data/members.json
# =====================================================================
def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _parse_date(v) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


async def seed_members(session) -> None:
    data = _load_json(ROOT / "frontend" / "data" / "members.json")
    by_slug = {
        m.slug: m
        for m in (await session.execute(select(Member))).scalars().all()
    }
    next_id = (
        await session.execute(select(func.coalesce(func.max(Member.id), 0)))
    ).scalar() + 1
    inserted = updated = 0
    for row in data:
        slug = row.get("slug")
        if not slug:
            continue
        fields = dict(
            name=row.get("name") or slug,
            nickname=row.get("nickname") or row.get("name") or slug,
            generation=row.get("generation"),
            status=row.get("status") or "regular",
            team=row.get("team"),
            birth_date=_parse_date(row.get("birthDate")),
            height=row.get("height"),
            blood_type=row.get("bloodType"),
            horoscope=row.get("horoscope"),
            jikoshoukai=row.get("jikoshoukai"),
            hobbies=row.get("hobbies"),
            trivia=row.get("trivia"),
            socials=row.get("socials") or {},
            updated_at=datetime.now(timezone.utc),
        )
        m = by_slug.get(slug)
        if m:
            for k, v in fields.items():
                setattr(m, k, v)
            updated += 1
        else:
            session.add(Member(id=next_id, slug=slug, created_at=datetime.now(timezone.utc), **fields))
            next_id += 1
            inserted += 1
    print(f"  + members: {inserted} baru, {updated} diperbarui (total sumber: {len(data)})")


# =====================================================================
# SETLISTS (legacy, masih dilayani di /theater/setlists)
# =====================================================================
async def seed_setlists(session) -> None:
    path = ROOT / "scripts" / "setlists_seed.json"
    if not path.exists():
        print("  - setlists_seed.json tidak ada, dilewati")
        return
    data = _load_json(path)
    existing = set((await session.execute(select(Setlist.setlist_id))).scalars().all())
    inserted = 0
    for row in data:
        sid = row.get("setlistId")
        if not sid or sid in existing:
            continue
        session.add(
            Setlist(
                setlist_id=sid,
                image_url=row.get("imageUrl"),
                title=row.get("title") or sid,
                title_japanese=row.get("titleJapanese"),
                description=row.get("description") or "",
                type=row.get("type") or "setlist",
                active=bool(row.get("active", True)),
                songs=row.get("songs") or [],
            )
        )
        inserted += 1
    print(f"  + setlists: {inserted} baru")


# =====================================================================
# CONTENT: encyclopedia / glossary / motivations / contributors
# =====================================================================
ENCYCLOPEDIA = [
    {
        "slug": "jkt48",
        "title": "JKT48",
        "sort_order": 1,
        "content": (
            "# JKT48\n\n"
            "JKT48 adalah grup idola perempuan Indonesia yang dibentuk tahun 2011 sebagai "
            "sister group pertama AKB48 di luar Jepang. Teater mereka berada di fx Sudirman, "
            "Jakarta. Konsepnya \"idola yang dapat kamu temui\": pertunjukan teater rutin, "
            "handshake event, dan interaksi dekat dengan fans.\n\n"
            "## Generasi\n"
            "Rekrutmen dilakukan per generasi (Gen 1 tahun 2011 sampai generasi terbaru). "
            "Setiap generasi menjalani masa trainee sebelum dipromosikan menjadi member reguler.\n\n"
            "## Tim\n"
            "Member aktif terbagi dalam tim yang bergantian menampilkan setlist teater. "
            "Selain tim inti, ada pula formasi akademi/trainee.\n"
        ),
    },
    {
        "slug": "wota-culture",
        "title": "Wota Culture",
        "sort_order": 2,
        "content": (
            "# Wota Culture\n\n"
            "Wota (wotagei) adalah budaya fans idol Jepang yang menyebar ke 48 Group, termasuk "
            "JKT48: chants (sorakan nama member), lightstick, dan koreografi penonton saat lagu tertentu.\n\n"
            "## Istilah populer\n"
            "- **Oshi**: member favoritmu.\n"
            "- **Kami-oshi**: oshi tertinggi dari semua oshi.\n"
            "- **DD** (daredemo daisuki): suka semua member.\n"
            "- **Handshake event**: acara bersalaman memakai tiket handshake.\n"
        ),
    },
    {
        "slug": "teater-show",
        "title": "Pertunjukan Teater",
        "sort_order": 3,
        "content": (
            "# Pertunjukan Teater\n\n"
            "Setlist adalah daftar lagu yang dibawakan dalam satu pertunjukan teater (±2 jam, "
            "sekitar 13-16 lagu). Beberapa setlist legendaris JKT48: *Renai Kinshi Jourei*, "
            "*Theater no Megami*, *Sambil Menggandeng Erat Tanganku*, *Demi Seseorang*, "
            "*Pajama Drive*, *Tunas di Balik Seragam*, *Matahari Milikku*, *Bel Terakhir Berbunyi*, "
            "*Sekarang Sedang Jatuh Cinta*, dan *Pertaruhan Cinta*.\n\n"
            "Istilah penting: **shonichi** (hari pertama setlist) dan **senshuuraku** (pertunjukan terakhir).\n"
        ),
    },
    {
        "slug": "oshi",
        "title": "Oshi & DD",
        "sort_order": 4,
        "content": (
            "# Oshi & DD\n\n"
            "**Oshi** berasal dari kata *oshimen* — member yang paling kamu dukung. Fans boleh "
            "punya beberapa oshi; yang paling utama disebut **kami-oshi**. Fans yang menyukai "
            "semua member disebut **DD** (*daredemo daisuki*). Menentukan oshi biasanya dari "
            "penampilan, kepribadian, atau jikoshoukai yang berkesan.\n"
        ),
    },
]

GLOSSARY = [
    ("Oshi", "Member favorit yang paling kamu dukung."),
    ("Kami-oshi", "Oshi tertinggi/utama dari seluruh oshi-mu."),
    ("DD", "Daredemo daisuki — fans yang menyukai semua member."),
    ("Jikoshoukai", "Perkenalan diri khas member dengan slogan/catchphrase."),
    ("Handshake", "Acara bersalaman dengan member menggunakan tiket handshake."),
    ("Cheki", "Foto polaroid bersama member (two-shot)."),
    ("Shonichi", "Hari pertama sebuah setlist/pertunjukan baru."),
    ("Senshuuraku", "Pertunjukan terakhir sebuah setlist/rangkaian show."),
    ("Sousenkyo", "Pemilihan umum untuk menentukan senbatsu single."),
    ("Senbatsu", "Member terpilih yang membawakan sebuah single."),
    ("Undergirls", "Member di luar senbatsu yang membawakan coupling song."),
    ("Graduate/Sotsugyou", "Kelulusan member dari grup."),
    ("Trainee/Kenkyuusei", "Member muda dalam masa pelatihan sebelum promosi."),
    ("Wota/Wotagei", "Gaya sorakan dan chants khas fans idol."),
    ("Lightstick/Penlight", "Tongkat lampu yang dibawa fans saat live."),
    ("Setlist", "Daftar lagu dalam satu pertunjukan teater."),
]

MOTIVATIONS = [
    ("Usaha tidak akan mengkhianati hasil — teruslah berjuang seperti para trainee mengejar panggung.", None, "jkt48-red-white"),
    ("Satu langkah kecil setiap hari lebih baik daripada seribu langkah yang hanya direncanakan.", None, "jkt48-red-white"),
    ("Karena bertemu denganmu, aku jadi tahu apa itu mimpi.", "JKT48 — Karena Kita Pernah Bersama", "jkt48-red-white"),
    ("Tidak ada kata terlambat untuk mulai; yang ada hanyalah menyerah terlalu cepat.", None, "jkt48-red-white"),
    ("Berikan yang terbaik di setiap pertunjukan, sekecil apa pun panggungnya.", None, "jkt48-red-white"),
    ("Sungai yang tenang tidak menghasilkan pelaut yang tangguh.", None, "jkt48-red-white"),
]

CONTRIBUTORS = [
    ("Tim JKT48Verse", "Konsep & Pengembangan", "Membangun platform komunitas fans JKT48: dashboard, live tracker, games, dan AI search."),
    ("Komunitas Fans", "Data & Konten", "Kurasi data member, setlist, dan dokumentasi pertunjukan."),
]


async def seed_content(session) -> None:
    existing = {e.slug for e in (await session.execute(select(Encyclopedia))).scalars().all()}
    for i, art in enumerate(ENCYCLOPEDIA):
        if art["slug"] in existing:
            continue
        session.add(
            Encyclopedia(
                slug=art["slug"],
                title=art["title"],
                content=art["content"],
                sort_order=art.get("sort_order", i),
                updated_at=datetime.now(timezone.utc),
            )
        )
    existing_terms = {g.term.lower() for g in (await session.execute(select(Glossary))).scalars().all()}
    for term, meaning in GLOSSARY:
        if term.lower() in existing_terms:
            continue
        session.add(Glossary(term=term, meaning=meaning))
    existing_quotes = {m.quote for m in (await session.execute(select(Motivation))).scalars().all()}
    for quote, author, template in MOTIVATIONS:
        if quote in existing_quotes:
            continue
        session.add(Motivation(quote=quote, author=author, template=template))
    existing_contrib = {c.name for c in (await session.execute(select(Contributor))).scalars().all()}
    for name, role, contribution in CONTRIBUTORS:
        if name in existing_contrib:
            continue
        session.add(Contributor(name=name, role=role, contribution=contribution))
    print("  + encyclopedia, glossary, motivations, contributors siap")


# =====================================================================
# GAMES: quiz + guess member
# =====================================================================
QUIZ_BANK = [
    # (question, options, correct_index, level, category)
    ("Tahun berapa JKT48 pertama kali tampil di televisi Indonesia?", ["2010", "2011", "2012", "2013"], 1, "easy", "sejarah"),
    ("Di mana teater JKT48 berada?", ["Grand Indonesia", "fx Sudirman", "Plaza Senayan", "Kota Kasablanka"], 1, "easy", "umum"),
    ("JKT48 adalah sister group dari...", ["BNK48", "AKB48", "NMB48", "HKT48"], 1, "easy", "umum"),
    ("Apa sebutan member favorit fans?", ["Senbatsu", "Oshi", "Captain", "Center"], 1, "easy", "wota"),
    ("Istilah untuk hari pertama sebuah setlist adalah...", ["Senshuuraku", "Shonichi", "Sousenkyo", "Sotsugyou"], 1, "easy", "wota"),
    ("Apa itu jikoshoukai?", ["Tarian pembuka", "Perkenalan diri khas member", "Lagu encore", "Sesi foto"], 1, "easy", "wota"),
    ("Slogan konsep JKT48 yang terkenal adalah...", ["Idols you can meet", "Idols you can dance with", "Idols forever", "Idols of Jakarta"], 0, "easy", "umum"),
    ("Lightstick yang dibawa fans saat konser biasa disebut...", ["Penlight", "Microphone", "Uchiwa", "Tambourine"], 0, "easy", "wota"),
    ("Member yang lulus dari grup disebut...", ["Graduate", "Trainee", "Kenkyuusei", "Undergirl"], 0, "easy", "umum"),
    ("Acara bersalaman dengan member disebut...", ["Meet event", "Handshake event", "Photo session", "Fan meeting"], 1, "easy", "wota"),
    ("Setlist teater JKT48 biasanya berisi sekitar berapa lagu?", ["5-7", "8-10", "13-16", "20-25"], 2, "medium", "teater"),
    ("'Renai Kinshi Jourei' dalam bahasa Indonesia berarti...", ["Aturan Anti Cinta", "Cinta Pertama", "Dilarang Jatuh Cinta", "Surat Cinta"], 0, "medium", "teater"),
    ("Siapa yang menentukan urutan senbatsu lewat pemungutan suara fans?", ["Sousenkyo", "Janken", "Audisi", "Undian"], 0, "medium", "sejarah"),
    ("Masa pelatihan calon member disebut...", ["Kenkyuusei", "Sensei", "Kouhai", "Rookie show"], 0, "medium", "umum"),
    ("'Theater no Megami' adalah nama...", ["Single utama", "Setlist teater", "Konser anniversary", "Dokumenter"], 1, "medium", "teater"),
    ("Fans yang menyukai semua member disebut...", ["DD", "VVIP", "Oshi-ka", "Senpa"], 0, "medium", "wota"),
    ("Foto polaroid berdua dengan member disebut...", ["Cheki", "Selfie", "Instax", "Purikura"], 0, "medium", "wota"),
    ("Coupling song biasanya dibawakan oleh...", ["Senbatsu", "Undergirls", "Trainee", "Kapten tim"], 1, "medium", "umum"),
    ("Konsep 'idol yang dapat kamu temui' diterjemahkan dari bahasa Jepang...", ["Aitani ikeru idol", "Kimi to boku", "Yume no naka", "Hajimete no hoshi"], 0, "hard", "sejarah"),
    ("Setlist asli AKB48 yang menjadi dasar 'Demi Seseorang' adalah...", ["Dareka no Tame ni", "Team B Oshi", "Pajama Drive", "Seishun Girls"], 0, "hard", "teater"),
    ("'Sambil Menggandeng Erat Tanganku' berasal dari setlist AKB48...", ["Te wo Tsunaginagara", "Romance Kakurenbo", "Tadaima Renaichuu", "Saka Agari"], 0, "hard", "teater"),
    ("Pertunjukan terakhir sebuah setlist disebut...", ["Senshuuraku", "Shonichi", "Saishuu", "Omedetou"], 0, "hard", "wota"),
    ("48 Group pertama kali didirikan di kota...", ["Osaka", "Tokyo", "Nagoya", "Fukuoka"], 1, "hard", "sejarah"),
    ("Istilah chants/seruan khas penonton saat lagu tertentu adalah...", ["Wotagei", "Kabe-don", "Otagai", "Ren'ai"], 0, "hard", "wota"),
]


async def seed_games(session) -> None:
    existing_q = {q.question for q in (await session.execute(select(QuizQuestion))).scalars().all()}
    added = 0
    for question, options, idx, level, category in QUIZ_BANK:
        if question in existing_q:
            continue
        session.add(
            QuizQuestion(question=question, options=options, correct_index=idx, level=level, category=category)
        )
        added += 1
    print(f"  + quiz: {added} soal baru (bank total {len(QUIZ_BANK)})")

    # Guess Member: dibuat dari member aktif; hints = generasi, tim, zodiak
    members = (
        await session.execute(
            select(Member).where(Member.status.in_(["regular", "trainee"]))
        )
    ).scalars().all()
    existing_guess = {g.member_id for g in (await session.execute(select(GuessQuestion))).scalars().all()}
    added_g = 0
    for m in members:
        if m.id in existing_guess:
            continue
        hints = []
        if m.generation:
            hints.append(f"Dari Generasi {m.generation}")
        if m.team:
            hints.append(f"Termasuk {m.team}")
        if m.horoscope:
            hints.append(f"Zodiaknya {m.horoscope}")
        if m.height:
            hints.append(f"Tingginya {m.height}")
        session.add(GuessQuestion(member_id=m.id, hints=hints[:4]))
        added_g += 1
    print(f"  + guess member: {added_g} soal baru (dari {len(members)} member aktif)")


# =====================================================================
# MAIN
# =====================================================================
async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database JKT48Verse (idempoten)")
    parser.add_argument("--users", action="store_true")
    parser.add_argument("--staff", action="store_true")
    parser.add_argument("--members", action="store_true")
    parser.add_argument("--setlists", action="store_true")
    parser.add_argument("--content", action="store_true")
    parser.add_argument("--games", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    run_all = args.all or not any(
        [args.users, args.staff, args.members, args.setlists, args.content, args.games]
    )

    print("=" * 56)
    print("JKT48Verse Seeder (PostgreSQL) — idempoten, aman diulang")
    print("=" * 56)

    await database_instance.connect()
    try:
        async with database_instance.session_factory() as session:
            if run_all or args.users:
                print("[users] akun seed...")
                await seed_users(session)
            if run_all or args.staff:
                print("[staff] kredensial ADMIN_1..3 & MOD_1..10 dari environment...")
                await seed_staff(session)
            if run_all or args.members:
                print("[members] data member kanonik...")
                await seed_members(session)
            if run_all or args.setlists:
                print("[setlists] setlist teater...")
                await seed_setlists(session)
            if run_all or args.content:
                print("[content] encyclopedia/glossary/motivation/contributors...")
                await seed_content(session)
            if run_all or args.games:
                print("[games] bank soal quiz & guess member...")
                await seed_games(session)
            await session.commit()
        print("\n✅ Seeding selesai.")
        print("   Akun: admin / moderator / fansdemo — ganti password setelah deploy!")
    finally:
        await database_instance.close()


if __name__ == "__main__":
    asyncio.run(main())
