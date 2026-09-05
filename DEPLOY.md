# Panduan Deploy JKT48Verse

Arsitektur: **Next.js (frontend murni, Vercel)** ⇄ **FastAPI (backend, host terpisah)** ⇄ **PostgreSQL (Supabase)**.

Semua akses data frontend melalui API FastAPI (cookie auth diteruskan server-side), jadi backend harus dapat dijangkau dari server Vercel (bukan dari browser user).

## 1. Database (Supabase)
1. Buat project PostgreSQL di Supabase, salin connection string (mode **Session pooler / port 5432**, bukan 6543).
2. Jalankan migrasi dari repo:
   ```bash
   pip install -r requirements/base.txt
   export DATABASE_URL="postgresql://..."
   alembic upgrade head
   python scripts/seed.py            # data awal (idempoten, aman dijalankan ulang)
   python scripts/seed_concerts.py # opsional: data konser (tabel legacy concerts)
   ```
   Seeder mengisi: akun `admin`/`moderator`/`fansdemo`, 69 member kanonik,
   setlist teater, encyclopedia/glossary/motivation/contributors, serta bank
   soal Quiz & Guess Member. Password seed mengikuti nilai bawaan di
   `DEPLOY.md` — **ganti setelah deploy** (atau override via env
   `ADMIN_PASSWORD`, `MODERATOR_PASSWORD`, `FANS_PASSWORD`).

## 2. Backend FastAPI (Railway / Render / Fly.io / VPS)
- Start command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT` (tanpa `--reload`).
- Environment variables (lihat `.env.example`):
  - `DATABASE_URL` — string koneksi Supabase.
  - `REDIS_URL` — Redis sungguhan (mis. Upstash `redis://...`); WAJIB di produksi.
  - `SECRET_KEY` — kunci JWT acak (`openssl rand -hex 32`).
  - `LLM_API_KEYS` / `LLM_BASE_URL=https://openrouter.ai/api/v1` / `LLM_MODEL` — AI Search via OpenRouter (opsional; tanpa ini AI Search fallback mode DB). Bisa banyak key, cukup satu: **router multi-key** memakainya bergiliran (lihat bagian 4).
  - `RESEND_API_KEY` + `MAIL_FROM` — kirim email OTP via Resend (opsional; tanpa ini kode OTP ditulis ke log backend untuk development).
- Pastikan CORS mengizinkan origin frontend bila ada pemanggilan langsung dari browser (normalnya tidak perlu — semua lewat server Next).

## 3. Frontend (Vercel)
1. Import repo GitHub ini ke Vercel, **Root Directory: `frontend`** (preset Next.js terdeteksi otomatis).
2. Environment variable:
   - `API_BASE_URL` = `https://<domain-backend>/api`
3. Deploy. Semua route halaman + server action memanggil backend dengan meneruskan cookie, jadi auth berjalan first-party tanpa CORS.

## 4. Kredensial staff: 3 Admin + 10 Moderator (all-or-nothing)

Akun staff tidak lagi diketik di database, melainkan di environment — lalu
disinkronkan ke tabel `users` oleh seeder:

```bash
python scripts/seed.py --staff
```

Penamaan env (isi yang diperlukan saja; sisanya biarkan kosong = `false`):

```
ADMIN_1_USERNAME=   ADMIN_1_EMAIL=   ADMIN_1_PASSWORD=   ADMIN_1_ACCESS_CODE=
ADMIN_2_USERNAME=   ADMIN_2_EMAIL=   ADMIN_2_PASSWORD=   ADMIN_2_ACCESS_CODE=
ADMIN_3_USERNAME=   ADMIN_3_EMAIL=   ADMIN_3_PASSWORD=   ADMIN_3_ACCESS_CODE=
MOD_1_USERNAME=     MOD_1_EMAIL=     MOD_1_PASSWORD=     MOD_1_ACCESS_CODE=
... sampai MOD_10_*
```

Aturan kerasnya:

1. **Satu slot butuh 4 nilai sekaligus**: `_USERNAME` + `_EMAIL` + `_PASSWORD`
   + `_ACCESS_CODE`.
2. Kalau **satu saja kosong** ⇒ slot bernilai `false` (nonaktif). User-nya
   tidak dibuat, dan kalau sudah ada di database akan **dinonaktifkan** sampai
   slot-nya dilengkapi.
3. Nilai dicocokkan **100% persis** saat login: besar/kecil huruf, spasi, dan
   karakter apa pun ikut terhitung (tidak di-trim, tidak di-lowercase).
4. **Tidak wajib mengisi semua slot** — cukup satu user yang lengkap. Yang
   tidak dipakai biarkan kosong (otomatis `false`).
5. Login staff wajib mengirim `access_code` (field form) di samping username
   dan password. Salah code → gagal masuk dan dihitung sebagai percobaan gagal.

Pantau status tiap slot (aktif/`false` + field yang kurang) lewat
`GET /api/admin/credentials` atau kartu **Kredensial Staff** di halaman Admin.
Setelah mengubah env, cukup jalankan ulang `python scripts/seed.py --staff`
atau panggil `POST /api/admin/credentials/reload`.

## 5. Router API key AI (1 base URL, 1 model, banyak key)

AI chat (AI Search) dan **block chat** (moderasi AI) memakai kumpulan API key
yang sama. Supaya tidak cepat limit:

```
LLM_API_KEYS=sk-or-v1-aaa,sk-or-v1-bbb,sk-or-v1-ccc   # paling mudah
LLM_BASE_URL=https://openrouter.ai/api/v1             # TETAP satu
LLM_MODEL=meta-llama/llama-3.1-8b-instruct            # TETAP satu
LLM_MODERATION_ENABLED=true                           # set false utk hemat token
```

Cara kerja router (`src/verse/llm_router.py`):

* Permintaan dibagi **round-robin** ke semua key → beban merata.
* Key yang kena **429** (limit) atau **5xx** masuk **cooldown sementara**
  (`LLM_KEY_COOLDOWN_SECONDS`, default 60 detik) dan dilewati; permintaan
  otomatis lanjut ke key berikutnya dalam panggilan yang sama.
* Key invalid (**401/403**) diistirahatkan lebih lama
  (`LLM_KEY_INVALID_COOLDOWN_SECONDS`, default 15 menit) lalu dicoba lagi.
* Moderasi AI **fail-open**: kalau LLM error/timeout, pesan tetap diizinkan
  (chat tidak pernah lumpuh gara-gara AI).

Pantau kesehatan key lewat `GET /api/admin/ai/keys` atau kartu
**Router API Key AI** di halaman Admin. Untuk memuat ulang key tanpa restart:
`POST /api/admin/ai/keys/reload`.

## Akun seed (ganti setelah deploy)
- `admin` / `AdminJKT48verse2026` · `moderator` / `ModeratorJKT48verse2026` · `fansdemo` / `FansDemoJKT48verse2026`

## Catatan
- Sandbox lokal:
  1. `python scripts/dev_pg.py` → Postgres dev di port 5433 (DB `jkt48verse`).
  2. `export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5433/jkt48verse"` lalu `alembic upgrade head && python scripts/seed.py`.
  3. `uvicorn src.main:app --reload --port 8000`.
  4. `cd frontend && npm i && npm run dev`.
- Migrasi baru: `alembic revision --autogenerate -m "..."` lalu `alembic upgrade head`.
- Scraper (cron harian): `cd scraper && python jkt48scraper.py --members --sync` dsb.
  Data ditulis ke schema kanonik memakai kolom jembatan `external_id` /
  `source_id` (migration 003), jadi aman dijalankan berulang.
