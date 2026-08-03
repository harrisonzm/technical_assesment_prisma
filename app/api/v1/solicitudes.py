from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.solicitudes import SolicitudRepository
from app.schemas.solicitudes import SolicitudCreate, SolicitudResponse
from app.services.solicitudes import SolicitudService


router = APIRouter(prefix="/solicitudes", tags=["solicitudes"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=SolicitudResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_solicitud(
    data: SolicitudCreate,
    session: DbSession,
) -> SolicitudResponse:
    service = SolicitudService(SolicitudRepository(session), session)
    solicitud = await service.create(data)
    return SolicitudResponse.model_validate(solicitud)
