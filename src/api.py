from fastapi import APIRouter

from src.auth.route import router as auth_router
from src.concerts.route import router as concerts_router
from src.health.route import router as health_router
from src.live.route import router as live_router
from src.setlists.route import router as setlists_router
from src.users.route import router as user_router
from src.verse.routes import router as verse_router

router = APIRouter()

router.include_router(auth_router, tags=["Auth"])
router.include_router(user_router, tags=["Users"])
router.include_router(health_router, tags=["Health"])

# JKT48Verse canonical API (dipakai frontend Next.js)
router.include_router(verse_router, tags=["JKT48Verse"])

# Live proxy (ShowRoom / IDN) — modul legacy yang masih relevan
router.include_router(live_router, prefix="/jkt48/live", tags=["Live"])

# Legacy MyPage48 (opsional; tabel setlists & concerts)
router.include_router(setlists_router, prefix="/theater/setlists", tags=["Setlists"])
router.include_router(concerts_router, prefix="/theater/concerts", tags=["Concerts"])
