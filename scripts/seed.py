"""Seeder database JKT48Verse (idempoten).

Menjalankan:  .venv/bin/python -m scripts.seed

Port dari frontend/db/seed.ts + pembuatan akun admin/moderator/demo.
"""

import asyncio
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.config import config  # noqa: E402
from src.models import (  # noqa: E402
    ActivityLog, AppMeta, BannedWord, Base, ChatMessage, Contributor,
    Encyclopedia, GameScore, Glossary, GuessQuestion, LiveSession, Member,
    Motivation, News, Notification, QuizQuestion, Schedule, ScheduleMember,
    User,
)

ROOT = Path(__file__).resolve().parent.parent
WIB = timezone(timedelta(hours=7))

HOBBIES = ["Menyanyi & menari", "Menggambar", "Membaca novel", "Bermain game", "Memasak", "Fotografi", "Menonton anime", "Bermain gitar", "Olahraga", "Menulis jurnal"]
TRIVIA = [
    "Suka minum es teh manis setelah show.",
    "Punya koleksi boneka di kamar.",
    "Paling semangat kalau setlist favoritnya dimainkan.",
    "Sering bikin fans tertawa lewat MC theater.",
    "Hafal hampir semua chant setlist.",
    "Selalu bawa lightstick mini di tas.",
]


def wib_now() -> datetime:
    return datetime.now(WIB)


def at_wib(day_offset: int, hour: int, minute: int = 0) -> datetime:
    now = wib_now()
    d = datetime(now.year, now.month, now.day, hour, minute, tzinfo=WIB) + timedelta(days=day_offset)
    return d.astimezone(timezone.utc)


def hours_ago(h: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=h)


async def main() -> None:
    engine = create_async_engine(config.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        members_count = (
            await session.execute(select(func.count()).select_from(Member))
        ).scalar() or 0
        if members_count > 0 and "--force" not in sys.argv:
            print(f"members sudah ada ({members_count}) — seeder dilewati. Pakai --force untuk paksa.")
            return

        # ---------- MEMBERS ----------
        raw = json.loads((ROOT / "frontend/data/members.json").read_text(encoding="utf-8"))
        inserted: list[Member] = []
        for i, m in enumerate(raw):
            team = m.get("team")
            team = None if team == "TRAINEE" else ("VIRTUAL" if team == "JKT48_VIRTUAL" else team)
            mem = Member(
                slug=m["slug"],
                name=m["name"],
                nickname=m.get("nickname") or m["name"],
                generation=m.get("generation"),
                status="trainee" if m.get("team") == "TRAINEE" else (m.get("status") or "regular"),
                team=team,
                birth_date=date.fromisoformat(m["birthDate"]) if m.get("birthDate") else None,
                height=m.get("height"),
                blood_type=m.get("bloodType"),
                horoscope=m.get("horoscope"),
                jikoshoukai=m.get("jikoshoukai"),
                hobbies=f"{HOBBIES[i % len(HOBBIES)]}, {HOBBIES[(i + 3) % len(HOBBIES)]}",
                trivia=TRIVIA[i % len(TRIVIA)],
                socials=m.get("socials") or {},
            )
            session.add(mem)
            inserted.append(mem)

        for extra in [
            dict(slug="shani-indira-natio", name="Shani Indira Natio", nickname="Shani", generation=3,
                 status="graduated", birth_date=date(1998, 10, 7), height="160cm",
                 jikoshoukai="Hai, aku Shani!", hobbies="Bermain game", trivia="Mantan kapten JKT48."),
            dict(slug="melody-nurramdhani-laksani", name="Melody Nurramdhani Laksani", nickname="Melody",
                 generation=1, status="graduated", birth_date=date(1992, 3, 24), height="158cm",
                 jikoshoukai="Hai, aku Melody!", hobbies="Berkebun", trivia="General Manager JKT48 pasca lulus."),
        ]:
            mem = Member(socials={}, **extra)
            session.add(mem)
            inserted.append(mem)
        await session.flush()
        print(f"members: {len(inserted)}")

        by_gen = lambda g: [m for m in inserted if m.generation == g]  # noqa: E731

        # ---------- SCHEDULES ----------
        theater = "Theater JKT48, fX Sudirman Lt. 4, Jakarta"
        map_url = "https://maps.google.com/?q=fX+Sudirman"
        sched_rows = [
            dict(title="Pajama Drive", type="theater", start_at=at_wib(0, 19), end_at=at_wib(0, 21), location=theater, map_url=map_url, setlist="Pajama Drive", ticket_status="sold_out", flag=None, description="Pertunjukan reguler setlist Pajama Drive."),
            dict(title="Aturan Anti Cinta", type="theater", start_at=at_wib(1, 19), end_at=at_wib(1, 21), location=theater, map_url=map_url, setlist="Aturan Anti Cinta", ticket_status="available", flag="shonichi", description="Shonichi setlist Aturan Anti Cinta (Renai Kinshi Jourei)."),
            dict(title="Cara Meminum Ramune", type="theater", start_at=at_wib(2, 14), end_at=at_wib(2, 16), location=theater, map_url=map_url, setlist="Cara Meminum Ramune", ticket_status="available", flag=None, description="Show siang akhir pekan."),
            dict(title="Meet & Greet Gen 12", type="event", start_at=at_wib(3, 13), end_at=at_wib(3, 17), location="Mall Kota Kasablanka, Jakarta", map_url="https://maps.google.com/?q=Kota+Kasablanka", setlist=None, ticket_status="available", flag=None, description="Sesi Meet & Greet member generasi 12."),
            dict(title="JKT48 Summer Festival", type="concert", start_at=at_wib(9, 18), end_at=at_wib(9, 22), location="Istora Senayan, Jakarta", map_url="https://maps.google.com/?q=Istora+Senayan", setlist=None, ticket_status="closed", flag=None, description="Konser besar musim panas dengan seluruh member."),
            dict(title="Talkshow Radio Prambors", type="media", start_at=at_wib(4, 16), end_at=at_wib(4, 17), location="Prambors FM", map_url=None, setlist=None, ticket_status="unknown", flag=None, description="Bincang santai bersama member di radio."),
            dict(title="2-Shot Session Online", type="event", start_at=at_wib(6, 10), end_at=at_wib(6, 15), location="Online (Video Call)", map_url=None, setlist=None, ticket_status="sold_out", flag=None, description="Sesi foto berdua secara daring."),
            dict(title="Fly Away", type="theater", start_at=at_wib(8, 19), end_at=at_wib(8, 21), location=theater, map_url=map_url, setlist="Fly Away", ticket_status="available", flag="senshuuraku", description="Senshuuraku setlist Fly Away."),
            dict(title="Ingin Bertemu", type="theater", start_at=at_wib(-1, 19), end_at=at_wib(-1, 21), location=theater, map_url=map_url, setlist="Ingin Bertemu", ticket_status="closed", flag=None, description="Show kemarin."),
            dict(title="Handshake Festival", type="event", start_at=at_wib(15, 10), end_at=at_wib(15, 18), location="JIExpo Kemayoran, Jakarta", map_url="https://maps.google.com/?q=JIExpo", setlist=None, ticket_status="available", flag=None, description="Festival jabat tangan seluruh member."),
            dict(title="Boku no Taiyou", type="theater", start_at=at_wib(12, 19), end_at=at_wib(12, 21), location=theater, map_url=map_url, setlist="Boku no Taiyou", ticket_status="available", flag=None, description="Pertunjukan reguler."),
            dict(title="Anniversary Concert 14th", type="concert", start_at=at_wib(30, 19), end_at=at_wib(30, 22), location="Tennis Indoor Senayan", map_url="https://maps.google.com/?q=Tennis+Indoor+Senayan", setlist=None, ticket_status="unknown", flag=None, description="Perayaan ulang tahun grup."),
        ]
        sched_objs = []
        for row in sched_rows:
            s = Schedule(**row)
            session.add(s)
            sched_objs.append(s)
        await session.flush()

        for i, s in enumerate(sched_objs):
            gen = [10, 11, 12, 13][i % 4]
            group = by_gen(gen) or inserted
            if s.type == "concert":
                chosen = inserted[:16]
            elif "Gen 12" in s.title:
                chosen = by_gen(12)
            else:
                chosen = group[i % 3 : i % 3 + 8] or group[:8]
            for m in chosen:
                session.add(ScheduleMember(schedule_id=s.id, member_id=m.id))
        print(f"schedules: {len(sched_objs)}")

        # ---------- NEWS ----------
        m0 = inserted[0].name
        m1 = inserted[5].name
        news_rows = [
            dict(slug="shonichi-aturan-anti-cinta", title="Shonichi Setlist \u201cAturan Anti Cinta\u201d Resmi Diumumkan", summary="Setlist legendaris kembali ke panggung Theater JKT48 dengan lineup generasi terbaru.", body=f"Theater JKT48 mengumumkan shonichi (hari pertama) setlist Aturan Anti Cinta. Pertunjukan perdana akan menampilkan lineup gabungan generasi 11, 12, dan 13.\n\nTiket dapat dibeli melalui kanal resmi. Pastikan datang lebih awal karena antrean diperkirakan panjang.\n\nMember {m0} dan {m1} dipastikan tampil pada shonichi.", category="theater", is_highlighted=True, views=1284, published_at=hours_ago(2)),
            dict(slug="summer-festival-2026", title="JKT48 Summer Festival: Tiket Presale Dibuka", summary="Konser besar musim panas di Istora Senayan, presale untuk member OFC dibuka lebih dulu.", body="JKT48 Summer Festival akan digelar di Istora Senayan. Presale tiket untuk anggota OFC dibuka mulai pukul 10:00 WIB, sedangkan penjualan umum menyusul dua hari kemudian.\n\nSetlist konser akan memadukan lagu klasik dan single terbaru.", category="event", is_highlighted=True, views=980, published_at=hours_ago(6)),
            dict(slug="single-baru-rilis", title="Single Baru JKT48 Rilis di Seluruh Platform Digital", summary="Single terbaru resmi dirilis dengan MV yang syuting di Bandung.", body="Single terbaru JKT48 kini tersedia di Spotify, Apple Music, dan YouTube Music. MV resmi dapat disaksikan di kanal YouTube JKT48.\n\nSenbatsu single ini terdiri dari 16 member lintas generasi.", category="release", is_highlighted=True, views=2210, published_at=hours_ago(20)),
            dict(slug="meet-greet-gen-12", title="Meet & Greet Generasi 12 di Kota Kasablanka", summary="Sesi tatap muka spesial bersama seluruh member generasi 12.", body="Member generasi 12 akan menyapa fans dalam sesi Meet & Greet di Mall Kota Kasablanka. Tiket dijual per sesi dengan kuota terbatas.", category="event", is_highlighted=False, views=540, published_at=hours_ago(30)),
            dict(slug="ulang-tahun-member-bulan-ini", title="Daftar Member yang Berulang Tahun Bulan Ini", summary="Cek jadwal perayaan ulang tahun member dan event birthday theater bulan ini.", body="Setiap bulan Theater JKT48 mengadakan pertunjukan spesial ulang tahun member. Fans dapat mengirim ucapan melalui fitur Birthday di JKT48Verse.", category="birthday", is_highlighted=False, views=410, published_at=hours_ago(48)),
            dict(slug="aturan-baru-theater", title="Pembaruan Aturan Menonton di Theater JKT48", summary="Beberapa aturan baru terkait chant, lightstick, dan fotografi selama pertunjukan.", body="Manajemen theater memperbarui aturan: lightstick maksimal 2 buah, dilarang memotret saat pertunjukan, dan chant mengikuti arahan MC.", category="theater", is_highlighted=False, views=780, published_at=hours_ago(70)),
            dict(slug="kolaborasi-brand", title="JKT48 Umumkan Kolaborasi dengan Brand Lokal", summary="Kolaborasi merchandise edisi terbatas segera hadir.", body="JKT48 mengumumkan kolaborasi dengan brand fashion lokal untuk merchandise edisi terbatas yang dijual di theater dan online.", category="other", is_highlighted=False, views=320, published_at=hours_ago(96)),
            dict(slug="senshuuraku-fly-away", title="Senshuuraku Setlist Fly Away Segera Digelar", summary="Pertunjukan terakhir setlist Fly Away sebelum rotasi setlist berikutnya.", body="Setlist Fly Away akan memasuki senshuuraku (hari terakhir). Tiket diprediksi habis dalam hitungan menit.", category="theater", is_highlighted=False, views=655, published_at=hours_ago(120)),
        ]
        for row in news_rows:
            session.add(News(**row))
        print(f"news: {len(news_rows)}")

        # ---------- ENCYCLOPEDIA ----------
        enc_rows = [
            dict(slug="jkt48", title="JKT48", sort_order=1, content="## Sejarah\nJKT48 adalah *sister group* AKB48 pertama di luar Jepang, dibentuk pada tahun 2011 di Jakarta, Indonesia. Nama JKT diambil dari singkatan Jakarta.\n\n## Konsep\nMengusung konsep **\u201cIdol yang dapat kamu temui\u201d** (*idols you can meet*), JKT48 tampil hampir setiap hari di theater khusus sehingga fans bisa bertemu langsung.\n\n## Struktur Generasi\nMember direkrut melalui audisi per generasi. Setiap generasi memiliki karakter dan lagu debut sendiri. Saat ini generasi aktif mencakup generasi 3 hingga 14.\n\n## Filosofi\nJKT48 menekankan pertumbuhan bersama fans: member berkembang dari *trainee* hingga menjadi member regular melalui kerja keras yang disaksikan langsung oleh penggemar."),
            dict(slug="theater", title="Theater JKT48", sort_order=2, content="## Lokasi\nTheater JKT48 berada di **fX Sudirman lantai 4**, Jalan Jenderal Sudirman, Jakarta Pusat.\n\n## Kapasitas & Fungsi\nTheater berkapasitas sekitar 180\u2013200 penonton dengan panggung menghadap tribun bertingkat. Selain pertunjukan reguler, theater juga digunakan untuk event ulang tahun member, *shonichi*, dan *senshuuraku*.\n\n## Tradisi\nSetiap pertunjukan diawali *overture* dan diakhiri sesi *high-touch* atau salam perpisahan. Fans membawa lightstick dan melakukan chant yang khas untuk tiap lagu.\n\n## Denah\nArea theater terdiri dari lobi merchandise, ruang tunggu, dan ruang pertunjukan utama."),
            dict(slug="history", title="Sejarah & Timeline", sort_order=3, content="## Timeline\n- **2011** — JKT48 diumumkan sebagai sister group AKB48 pertama di luar Jepang.\n- **2012** — Theater JKT48 di fX Sudirman resmi dibuka; Team J dibentuk.\n- **2013** — Debut single \u201cRiver\u201d; generasi 2 bergabung.\n- **2014** — Team KIII terbentuk; Senbatsu Sousenkyo pertama.\n- **2015** — Konser akbar di berbagai kota; Team T dibentuk (2016).\n- **2018** — Janken Tournament pertama JKT48.\n- **2021** — Restrukturisasi besar; sistem tim ditiadakan.\n- **2023\u20132026** — Era baru dengan generasi 11\u201314, konser stadion, dan popularitas yang meningkat pesat.\n\n## Momen Monumental\nSenbatsu Sousenkyo, Janken Tournament, dan konser ulang tahun adalah momen yang paling ditunggu fans setiap tahun."),
            dict(slug="wota-culture", title="Budaya Wota", sort_order=4, content="## Apa itu Wota?\n*Wota* adalah sebutan untuk penggemar idol yang aktif mendukung, menonton theater, dan mengikuti event.\n\n## Etika Penggemar\n- Hormati member dan sesama fans di theater maupun ruang publik.\n- Ikuti arahan staf, jangan memotret saat pertunjukan.\n- Chant mengikuti tempo lagu, tidak berlebihan sehingga mengganggu penonton lain.\n- Di ruang digital: tidak menyebarkan informasi pribadi member.\n\n## Glosarium\nLihat daftar istilah di bawah artikel ini."),
        ]
        for row in enc_rows:
            session.add(Encyclopedia(**row))

        glossary_rows = [
            ("Oshi", "Member favorit yang paling didukung oleh seorang fans."),
            ("Kami-oshi", "Oshi utama; member nomor satu di hati fans."),
            ("Chant", "Teriakan dukungan berirama yang dilakukan fans selama lagu tertentu."),
            ("Wotagei", "Gerakan tangan dan lightstick terkoordinasi yang dilakukan fans."),
            ("Lightstick", "Tongkat cahaya (biasanya warna sesuai member) yang dibawa fans ke theater."),
            ("M&G", "Meet & Greet — sesi bertemu langsung dengan member."),
            ("2-Shot", "Sesi foto berdua fans dan member."),
            ("Shonichi", "Hari pertama pertunjukan sebuah setlist."),
            ("Senshuuraku", "Hari terakhir pertunjukan sebuah setlist."),
            ("Jikoshoukai", "Kalimat perkenalan diri khas tiap member."),
            ("Senbatsu", "Member terpilih yang tampil pada single utama."),
            ("Setlist", "Rangkaian lagu yang ditampilkan dalam satu pertunjukan theater."),
        ]
        for term, meaning in glossary_rows:
            session.add(Glossary(term=term, meaning=meaning))
        print("encyclopedia + glossary OK")

        # ---------- MOTIVATIONS ----------
        now = wib_now()
        today_key = now.strftime("%Y-%m-%d")
        mot_rows = [
            dict(quote="Mimpi tidak akan lari darimu. Kamulah yang harus mengejarnya, satu langkah kecil setiap hari.", author="JKT48Verse", template="jkt48-red-white", featured_on=date.fromisoformat(today_key)),
            dict(quote="Panggung terbaik adalah tempat kamu berani tampil apa adanya.", author="JKT48Verse", template="minimal"),
            dict(quote="Setiap latihan yang melelahkan adalah investasi untuk sorak sorai di masa depan.", author="JKT48Verse", template="dark-elegant"),
            dict(quote="Dukung oshi-mu dengan cara yang membuatnya bangga: jadilah fans yang baik.", author="Komunitas Wota", template="jkt48-red-white"),
        ]
        for row in mot_rows:
            session.add(Motivation(**row))

        # ---------- QUIZ ----------
        quiz_rows = [
            dict(question="Tahun berapa JKT48 dibentuk?", options=["2010", "2011", "2012", "2013"], correct_index=1, level="easy", category="sejarah"),
            dict(question="Di mana lokasi Theater JKT48?", options=["fX Sudirman", "Grand Indonesia", "Kota Kasablanka", "Senayan City"], correct_index=0, level="easy", category="theater"),
            dict(question="JKT48 adalah sister group dari?", options=["SKE48", "NMB48", "AKB48", "HKT48"], correct_index=2, level="easy", category="sejarah"),
            dict(question="Apa arti 'shonichi'?", options=["Hari terakhir", "Hari pertama", "Hari libur", "Hari ulang tahun"], correct_index=1, level="easy", category="umum"),
            dict(question="Sebutan member favorit utama seorang fans adalah?", options=["Senbatsu", "Kami-oshi", "Wotagei", "Chant"], correct_index=1, level="easy", category="umum"),
            dict(question="Theater JKT48 berada di lantai berapa fX Sudirman?", options=["2", "3", "4", "5"], correct_index=2, level="medium", category="theater"),
            dict(question="Apa nama single debut JKT48?", options=["Heavy Rotation", "River", "Fortune Cookie", "Flying Get"], correct_index=1, level="medium", category="sejarah"),
            dict(question="Apa istilah untuk hari terakhir sebuah setlist?", options=["Shonichi", "Senshuuraku", "Sousenkyo", "Janken"], correct_index=1, level="medium", category="umum"),
            dict(question="Kota asal konsep 48 Group adalah?", options=["Osaka", "Tokyo", "Nagoya", "Fukuoka"], correct_index=1, level="hard", category="sejarah"),
            dict(question="Turnamen 'batu-gunting-kertas' di JKT48 disebut?", options=["Sousenkyo", "Janken Tournament", "Request Hour", "Setlist Battle"], correct_index=1, level="hard", category="sejarah"),
        ]

        def opt4(correct: str, pool: list[str], salt: int):
            others = [p for p in pool if p != correct][:3]
            options = [correct, *others]
            shuffled = sorted(enumerate(options), key=lambda x: ((x[0] * 7919) + salt * 31) % 5)
            final = [o for _, o in shuffled]
            return final, final.index(correct)

        all_names = [m.name for m in inserted]
        for g in [10, 11, 12, 13]:
            names = [m.name for m in by_gen(g)]
            if names:
                correct = names[0]
                pool = [n for n in all_names if n not in names]
                options, ci = opt4(correct, pool, g)
                quiz_rows.append(dict(question=f"Siapa member yang berasal dari generasi {g}?", options=options, correct_index=ci, level="medium", category="member"))
        for i, m in enumerate(inserted[:8]):
            if not m.nickname:
                continue
            options, ci = opt4(m.name, all_names[i + 1 :] + all_names, i)
            quiz_rows.append(dict(question=f'Siapa member dengan nama panggilan "{m.nickname}"?', options=options, correct_index=ci, level="hard" if i % 2 else "easy", category="member"))
        for row in quiz_rows:
            session.add(QuizQuestion(**row))
        print(f"quiz: {len(quiz_rows)}")

        # ---------- GUESS ----------
        guess_count = 0
        for m in inserted:
            if m.jikoshoukai and len(m.jikoshoukai) > 10 and guess_count < 30:
                hints = [
                    f"Generasi {m.generation or '?'}",
                    f"Lahir bulan {m.birth_date.month}" if m.birth_date else f"Tinggi {m.height or '-'}",
                    f'Nama depan diawali huruf "{m.name[0]}"',
                ]
                session.add(GuessQuestion(member_id=m.id, hints=hints))
                guess_count += 1
        print(f"guess: {guess_count}")

        # ---------- BANNED WORDS / CONTRIBUTORS ----------
        for w in ["anjing", "bangsat", "kontol", "memek", "goblok", "tolol", "bajingan", "ngentot", "babi", "asu"]:
            session.add(BannedWord(word=w))
        for c in [
            dict(name="Neldah", role="Lead Developer", contribution="Arsitektur platform, backend, scraper, dan spesifikasi produk."),
            dict(name="Komunitas JKT48Verse", role="Content Curator", contribution="Kurasi ensiklopedia, glosarium wota, dan bank soal quiz."),
            dict(name="UI/UX Volunteer", role="UI/UX Designer", contribution="Design system merah-putih, komponen, dan mode gelap."),
        ]:
            session.add(Contributor(**c))

        # ---------- LIVE HISTORY (contoh 3 hari) ----------
        for i, m in enumerate(inserted[10:20]):
            started = datetime.now(timezone.utc) - timedelta(hours=(i + 1) * 7)
            session.add(
                LiveSession(
                    member_id=m.id,
                    member_name=m.nickname,
                    platform="idn" if i % 2 else "showroom",
                    title=f"Live {m.nickname}",
                    started_at=started,
                    ended_at=started + timedelta(minutes=25 + i * 9),
                    replay_url=(m.socials or {}).get("idn_app") if i % 3 == 0 else None,
                    viewers=300 + i * 120,
                )
            )
        print("live history OK")

        # ---------- AKUN: admin / moderator / demo ----------
        from passlib.context import CryptContext

        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        import uuid as _uuid

        accounts = [
            dict(
                user_id=str(_uuid.uuid4()), name=config.admin_username,
                username=config.admin_username, email=config.admin_email,
                password=ctx.hash(config.admin_password.get_secret_value()),
                role="ADMIN", is_admin=True, is_email_verified=True,
                avatar_seed=random.randint(1, 6),
            ),
            dict(
                user_id=str(_uuid.uuid4()), name="moderator", username="moderator",
                email="moderator@jkt48verse.local", password=ctx.hash("ModeratorJKT48verse2026"),
                role="MODERATOR", is_admin=False, is_email_verified=True, avatar_seed=2,
            ),
            dict(
                user_id=str(_uuid.uuid4()), name="fansdemo", username="fansdemo",
                email="fans@jkt48verse.local", password=ctx.hash("FansDemoJKT48verse2026"),
                role="MEMBER", is_admin=False, is_email_verified=True, avatar_seed=3,
            ),
        ]
        user_objs = []
        for a in accounts:
            u = User(last_active_at=datetime.now(timezone.utc), **a)
            session.add(u)
            user_objs.append(u)
        await session.flush()

        session.add(
            Notification(
                user_seq=user_objs[2].seq, type="SYSTEM",
                title="Selamat datang di JKT48Verse!",
                body="Atur oshi-mu di halaman Akun agar Live Alert & Birthday Alert aktif.",
                href="/account",
            )
        )
        # chat pembuka
        session.add(ChatMessage(user_seq=user_objs[0].seq, username="admin", role="ADMIN", avatar_seed=1, body="Selamat datang di chat publik JKT48Verse! Mari jaga suasana tetap positif 💕"))
        session.add(ChatMessage(user_seq=user_objs[2].seq, username="fansdemo", role="MEMBER", avatar_seed=3, body="Halo semuanya! Semangat buat oshi kalian hari ini 🚀"))
        # skor contoh untuk leaderboard
        session.add(GameScore(user_seq=user_objs[2].seq, game="quiz", score=420, detail="level medium"))
        session.add(GameScore(user_seq=user_objs[2].seq, game="guess", score=380, detail="5 soal"))
        session.add(ActivityLog(user_seq=user_objs[2].seq, action="game:quiz", detail="420 poin (level medium)"))

        session.add(AppMeta(key="seeded_at", value=datetime.now(timezone.utc).isoformat()))
        await session.commit()
        print("SEED SELESAI ✓")
        print(f"  admin     : {config.admin_username} / {config.admin_password.get_secret_value()}")
        print("  moderator : moderator / ModeratorJKT48verse2026")
        print("  member    : fansdemo / FansDemoJKT48verse2026")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
