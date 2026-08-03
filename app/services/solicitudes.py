from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.Exceptions.RequestError import ConflictError
from app.db.models.solicitudes import Solicitudes
from app.repositories.solicitudes import SolicitudRepository
from app.schemas.solicitudes import SolicitudCreate


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
