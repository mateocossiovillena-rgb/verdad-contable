"""Migraciones con Alembic. La URL de la base sale de app.config (variable DATABASE_URL)."""

from logging.config import fileConfig

from alembic import context

from app import config as config_app
from app import modelos  # noqa: F401  (registra las tablas en Base.metadata)
from app.db import Base, crear_motor

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config_app.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    motor = crear_motor(config_app.DATABASE_URL)
    with motor.connect() as conexion:
        # render_as_batch permite cambiar columnas también en SQLite.
        context.configure(connection=conexion, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
