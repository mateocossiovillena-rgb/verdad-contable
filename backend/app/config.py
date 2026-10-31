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

# "produccion" en el servidor publicado: ahí la app no arranca sin una CLAVE_SECRETA propia.
ENTORNO = os.environ.get("ENTORNO", "desarrollo")

CLAVE_SECRETA = os.environ.get("CLAVE_SECRETA", "")
if ENTORNO == "produccion" and len(CLAVE_SECRETA) < 32:
    # Con la clave de desarrollo (visible en este archivo) cualquiera podría fabricar sesiones válidas.
    raise RuntimeError(
        "En producción CLAVE_SECRETA es obligatoria y debe tener al menos 32 caracteres. "
        'Genera una con: python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
if ENTORNO == "produccion" and DATABASE_URL.startswith("sqlite"):
    # Sin esto, si DATABASE_URL falta el servidor arranca con SQLite en un disco que se borra en cada publicación.
    raise RuntimeError("En producción DATABASE_URL es obligatoria (PostgreSQL), no SQLite.")
if not CLAVE_SECRETA:
    CLAVE_SECRETA = "solo-para-desarrollo-cambiar-en-produccion"
    warnings.warn("CLAVE_SECRETA no está definida: usando una clave de desarrollo.", stacklevel=1)

# Intentos fallidos de ingreso antes de bloquear por un rato (frena a quien prueba PINs al azar).
INTENTOS_POR_USUARIO = int(os.environ.get("INTENTOS_POR_USUARIO", "5"))
INTENTOS_POR_IP = int(os.environ.get("INTENTOS_POR_IP", "20"))
MINUTOS_BLOQUEO = int(os.environ.get("MINUTOS_BLOQUEO", "15"))

# Bolivia no tiene horario de verano: UTC-4 todo el año.
HORAS_ZONA_HORARIA = int(os.environ.get("HORAS_ZONA_HORARIA", "-4"))

DIAS_SESION = int(os.environ.get("DIAS_SESION", "30"))

CARPETA_FOTOS = Path(os.environ.get("CARPETA_FOTOS", RAIZ_BACKEND / "fotos"))
TAMANO_MAX_FOTO = 3 * 1024 * 1024  # bytes, ya comprimida en el celular

CARPETA_PLANOS = Path(os.environ.get("CARPETA_PLANOS", RAIZ_BACKEND / "planos"))
TAMANO_MAX_PLANO = 25 * 1024 * 1024  # bytes

CARPETA_FRONTEND = Path(os.environ.get("CARPETA_FRONTEND", RAIZ_BACKEND.parent / "frontend" / "dist"))
