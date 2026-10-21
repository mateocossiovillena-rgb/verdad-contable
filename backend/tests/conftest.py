import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import config
from app.db import Base, crear_motor, obtener_sesion
from app.main import app


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CARPETA_FOTOS", tmp_path / "fotos")
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)

    def sesion_prueba():
        with fabrica() as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = sesion_prueba
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    motor.dispose()


def cabecera(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def dueno(cliente):
    r = cliente.post(
        "/api/sesion/registro", json={"nombre": "Ana Quispe", "correo": "ana@obra.bo", "clave": "clave-segura"}
    )
    assert r.status_code == 201, r.text
    return cabecera(r.json()["token"])
