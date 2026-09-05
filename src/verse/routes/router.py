"""Agregasi seluruh router verse.

PENTING (urutan): router dengan path STATIS yang bisa bentrok dengan path
dinamis harus di-include lebih dulu. Contoh: ``GET /schedules/reminders``
(community) wajib terdaftar sebelum ``GET /schedules/{schedule_id}``
(content) agar tidak tertutup (shadowed) dan berakhir 422.
"""

from fastapi import APIRouter

from src.verse.routes import admin, community, content, games, live, search_ai

router = APIRouter()
router.include_router(community.router)
router.include_router(content.router)
router.include_router(games.router)
router.include_router(live.router)
router.include_router(search_ai.router)
router.include_router(admin.router)
