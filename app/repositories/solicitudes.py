from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.solicitudes import Solicitudes
from app.repositories.pagination import Page
from app.schemas.solicitudes import SolicitudCreate, SolicitudFilters, SolicitudUpdate


class SolicitudRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: SolicitudCreate) -> Solicitudes:
        solicitud = Solicitudes(**data.model_dump())
        self.session.add(solicitud)
        await self.session.flush()
        await self.session.refresh(solicitud)
        return solicitud

    async def get_by_id(self, solicitud_id: UUID) -> Solicitudes | None:
        return await self.session.get(Solicitudes, solicitud_id)

    async def get_by_external_id(self, external_id: str) -> Solicitudes | None:
        result = await self.session.execute(
            select(Solicitudes).where(Solicitudes.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def list(self, filters: SolicitudFilters) -> Page[Solicitudes]:
        statement = select(Solicitudes)

        for field in (
            "id",
            "external_id",
            "type",
            "applicant",
            "email",
            "description",
            "priority",
            "state",
            "created_at",
            "updated_at",
        ):
            value = getattr(filters, field)
            if value is not None:
                statement = statement.where(getattr(Solicitudes, field) == value)

        count_statement = select(func.count()).select_from(statement.subquery())
        total = await self.session.scalar(count_statement)

        page_statement = (
            statement.order_by(Solicitudes.created_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
        )
        result = await self.session.execute(page_statement)
        items = list(result.scalars().all())

        return Page(
            items=items,
            total=total or 0,
            offset=filters.offset,
            limit=filters.limit,
        )

    async def update(
        self,
        solicitud: Solicitudes,
        data: SolicitudUpdate,
    ) -> Solicitudes:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(solicitud, field, value)

        await self.session.flush()
        await self.session.refresh(solicitud)
        return solicitud

    async def delete(self, solicitud: Solicitudes) -> None:
        await self.session.delete(solicitud)
        await self.session.flush()
