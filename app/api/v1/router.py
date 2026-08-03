from fastapi import APIRouter

from app.api.v1.solicitudes import router as solicitudes_router


router = APIRouter()
router.include_router(solicitudes_router)
