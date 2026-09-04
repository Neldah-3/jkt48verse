"""Agregasi seluruh router verse."""

from fastapi import APIRouter

from src.verse.routes import admin, community, content, games, live, search_ai

router = APIRouter()
router.include_router(content.router)
router.include_router(community.router)
router.include_router(games.router)
router.include_router(live.router)
router.include_router(search_ai.router)
router.include_router(admin.router)
