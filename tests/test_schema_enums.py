from app.schemas.enums import Priority, RequestType, State


def test_request_type_values():
    assert [item.value for item in RequestType] == [
        "Acceso a plataforma",
        "Soporte técnico",
        "Académica",
        "Administrativa",
    ]


def test_priority_values():
    assert [item.value for item in Priority] == ["Baja", "Media", "Alta"]


def test_state_values():
    assert [item.value for item in State] == [
        "Recibida",
        "En proceso",
        "Completada",
        "Rechazada",
    ]
