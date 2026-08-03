from enum import StrEnum


class RequestType(StrEnum):
    PLATFORM_ACCESS = "Acceso a plataforma"
    TECHNICAL_SUPPORT = "Soporte técnico"
    ACADEMIC = "Académica"
    ADMINISTRATIVE = "Administrativa"


class Priority(StrEnum):
    LOW = "Baja"
    MEDIUM = "Media"
    HIGH = "Alta"


class State(StrEnum):
    RECEIVED = "Recibida"
    IN_PROGRESS = "En proceso"
    COMPLETED = "Completada"
    REJECTED = "Rechazada"
