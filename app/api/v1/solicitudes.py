from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.solicitudes import SolicitudRepository
from app.schemas.solicitudes import (
    SolicitudCreate,
    SolicitudFilters,
    SolicitudPageResponse,
    SolicitudResponse,
)
from app.services.solicitudes import SolicitudService


router = APIRouter(prefix="/solicitudes", tags=["solicitudes"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=SolicitudPageResponse)
async def list_solicitudes(
    filters: Annotated[SolicitudFilters, Query()],
    session: DbSession,
) -> SolicitudPageResponse:
    service = SolicitudService(SolicitudRepository(session), session)
    page = await service.list(filters)

    return SolicitudPageResponse(
        items=[SolicitudResponse.model_validate(item) for item in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
        has_next=page.has_next,
    )


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
