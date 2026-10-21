"""Conexión a la base de datos y sesión por petición."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


def crear_motor(url: str) -> Engine:
    if url.startswith("sqlite"):
        motor = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(motor, "connect")
        def _activar_llaves_foraneas(conexion, _registro):
            cursor = conexion.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return motor
    return create_engine(url, pool_pre_ping=True)


motor = crear_motor(config.DATABASE_URL)
FabricaSesion = sessionmaker(bind=motor, expire_on_commit=False)


def obtener_sesion() -> Iterator[Session]:
    with FabricaSesion() as sesion:
        yield sesion
