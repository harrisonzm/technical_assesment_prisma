from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ...schemas.enums import RequestType, State, Priority



from ..base import Base

class Solicitudes(Base):
    __tablename__ = "solicitudes"
    
    id: Mapped[UUID] = mapped_column(
            Uuid,
            primary_key=True,
            default=uuid4,
        )
    
    external_id: Mapped[str] = mapped_column(
        String(100),
        name='externalId',
        unique=True,
        nullable=False,
        index=True
    )

    type: Mapped[RequestType] = mapped_column(
        Enum(
            RequestType,
            name="request_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        index=True
    )

    applicant : Mapped[str] = mapped_column(
        String(40),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
    )
    
    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    
    priority: Mapped[Priority] = mapped_column(
        Enum(
            Priority,
            name="request_priority",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        index=True
    )
    
    state: Mapped[State] = mapped_column(
        Enum(
            State,
            name="requestState",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        index=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name='createdAt',
        nullable=False,
        server_default=func.now(),
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            name='updatedAt',
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
