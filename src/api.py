from fastapi import APIRouter

from src.auth.route import router as auth_router
from src.concerts.route import router as concerts_router
from src.events.route import router as events_router
from src.health.route import router as health_router
from src.live.route import router as live_router
from src.members.route import router as members_router
from src.news.route import router as news_router
from src.setlists.route import router as setlists_router
from src.sorter.route import router as sorter_router
from src.users.route import router as user_router

router = APIRouter()

router.include_router(auth_router, tags=["Auth"])
router.include_router(user_router, tags=["Users"])
router.include_router(health_router, tags=["Health"])
router.include_router(members_router, prefix="/members", tags=["Members"])
router.include_router(setlists_router, prefix="/theater/setlists", tags=["Setlists"])
router.include_router(events_router, prefix="/events", tags=["Events"])
router.include_router(news_router, prefix="/theater/news", tags=["News"])
router.include_router(live_router, prefix="/jkt48/live", tags=["Live"])
router.include_router(sorter_router, prefix="/theater/sorter", tags=["Sorter"])
router.include_router(concerts_router, prefix="/theater/concerts", tags=["Concerts"])
