from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.enums import Priority, RequestType, State


class SolicitudCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    type: RequestType
    applicant: str = Field(min_length=1, max_length=40)
    email: EmailStr
    description: str = Field(min_length=1, max_length=1000)
    priority: Priority
    state: State = State.RECEIVED


class SolicitudUpdate(BaseModel):
    type: RequestType | None = None
    applicant: str | None = Field(default=None, min_length=1, max_length=40)
    email: EmailStr | None = None
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    priority: Priority | None = None
    state: State | None = None


class SolicitudFilters(BaseModel):
    id: UUID | None = None
    external_id: str | None = Field(default=None, min_length=1, max_length=100)
    type: RequestType | None = None
    applicant: str | None = Field(default=None, min_length=1, max_length=40)
    email: EmailStr | None = None
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    priority: Priority | None = None
    state: State | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class SolicitudResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    type: RequestType
    applicant: str
    email: EmailStr
    description: str
    priority: Priority
    state: State
    created_at: datetime
    updated_at: datetime
