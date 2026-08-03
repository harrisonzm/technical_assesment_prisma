from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.Exceptions.RequestError import ConflictError, ResourceNotFoundError
from app.db.models.solicitudes import Solicitudes
from app.repositories.pagination import Page
from app.repositories.solicitudes import SolicitudRepository
from app.schemas.solicitudes import SolicitudCreate, SolicitudFilters


class SolicitudService:
    def __init__(
        self,
        repository: SolicitudRepository,
        session: AsyncSession,
    ) -> None:
        self.repository = repository
        self.session = session

    async def create(self, data: SolicitudCreate) -> Solicitudes:
        try:
            solicitud = await self.repository.create(data)
            await self.session.commit()
            return solicitud
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "A solicitud with this external ID already exists",
                details={"external_id": data.external_id},
            ) from exc

    async def list(self, filters: SolicitudFilters) -> Page[Solicitudes]:
        return await self.repository.list(filters)

    async def get_by_id(self, solicitud_id: UUID) -> Solicitudes:
        solicitud = await self.repository.get_by_id(solicitud_id)
        if solicitud is None:
            raise ResourceNotFoundError(
                "Solicitud was not found",
                details={"solicitud_id": str(solicitud_id)},
            )

        return solicitud
