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
   python scripts/seed.py            # data awal (idempoten)
   ```

## 2. Backend FastAPI (Railway / Render / Fly.io / VPS)
- Start command: `uvicorn src.api:app --host 0.0.0.0 --port $PORT` (tanpa `--reload`).
- Environment variables (lihat `.env.example`):
  - `DATABASE_URL` — string koneksi Supabase.
  - `REDIS_URL` — Redis sungguhan (mis. Upstash `redis://...`); WAJIB di produksi.
  - `SECRET_KEY` — kunci JWT acak (`openssl rand -hex 32`).
  - `LLM_API_KEY` / `LLM_BASE_URL=https://openrouter.ai/api/v1` / `LLM_MODEL` — AI Search via OpenRouter (opsional; tanpa ini AI Search fallback mode DB).
  - `RESEND_API_KEY` + `MAIL_FROM` — kirim email OTP via Resend (opsional; tanpa ini kode OTP ditulis ke log backend untuk development).
- Pastikan CORS mengizinkan origin frontend bila ada pemanggilan langsung dari browser (normalnya tidak perlu — semua lewat server Next).

## 3. Frontend (Vercel)
1. Import repo GitHub ini ke Vercel, **Root Directory: `frontend`** (preset Next.js terdeteksi otomatis).
2. Environment variable:
   - `API_BASE_URL` = `https://<domain-backend>/api`
3. Deploy. Semua route halaman + server action memanggil backend dengan meneruskan cookie, jadi auth berjalan first-party tanpa CORS.

## Akun seed (ganti setelah deploy)
- `admin` / `AdminJKT48verse2026` · `moderator` / `ModeratorJKT48verse2026` · `fansdemo` / `FansDemoJKT48verse2026`

## Catatan
- Sandbox lokal: `python scripts/dev_pg.py` (Postgres dev port 5433) + `uvicorn src.api:app --reload --port 8000` + `cd frontend && npm i && npm run dev`.
- Migrasi baru: `alembic revision --autogenerate -m "..."` lalu `alembic upgrade head`.
