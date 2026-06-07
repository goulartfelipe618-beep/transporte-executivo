from fastapi import APIRouter

from app.api.v1.booking import router as booking_router
from app.api.v1.express import router as express_router
from app.api.v1.public import router as public_router

router = APIRouter(prefix="/api/v1")
router.include_router(public_router)
router.include_router(booking_router)
router.include_router(express_router)
