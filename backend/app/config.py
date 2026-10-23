"""Configuración leída de variables de entorno."""

import os
import warnings
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{RAIZ_BACKEND / 'verdad_contable.db'}")
# Railway/Render entregan "postgres://"; SQLAlchemy con psycopg 3 necesita este prefijo.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://") :]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://") :]

CLAVE_SECRETA = os.environ.get("CLAVE_SECRETA", "")
if not CLAVE_SECRETA:
    CLAVE_SECRETA = "solo-para-desarrollo-cambiar-en-produccion"
    warnings.warn("CLAVE_SECRETA no está definida: usando una clave de desarrollo.", stacklevel=1)

# Bolivia no tiene horario de verano: UTC-4 todo el año.
HORAS_ZONA_HORARIA = int(os.environ.get("HORAS_ZONA_HORARIA", "-4"))

DIAS_SESION = int(os.environ.get("DIAS_SESION", "30"))

CARPETA_FOTOS = Path(os.environ.get("CARPETA_FOTOS", RAIZ_BACKEND / "fotos"))
TAMANO_MAX_FOTO = 3 * 1024 * 1024  # bytes, ya comprimida en el celular

CARPETA_PLANOS = Path(os.environ.get("CARPETA_PLANOS", RAIZ_BACKEND / "planos"))
TAMANO_MAX_PLANO = 25 * 1024 * 1024  # bytes

CARPETA_FRONTEND = Path(os.environ.get("CARPETA_FRONTEND", RAIZ_BACKEND.parent / "frontend" / "dist"))
