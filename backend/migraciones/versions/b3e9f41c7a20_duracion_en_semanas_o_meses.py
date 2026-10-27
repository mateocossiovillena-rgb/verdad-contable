"""duración en días, semanas o meses

Revision ID: b3e9f41c7a20
Revises: a1c7e5d20b3f
Create Date: 2026-10-27 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e9f41c7a20"
down_revision: str | Sequence[str] | None = "a1c7e5d20b3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("actividad", schema=None) as batch_op:
        batch_op.add_column(sa.Column("duracion_cantidad", sa.Numeric(6, 1), nullable=True))
        batch_op.add_column(sa.Column("unidad_duracion", sa.String(10), server_default="dias", nullable=False))
    op.execute("UPDATE actividad SET duracion_cantidad = duracion_dias")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("actividad", schema=None) as batch_op:
        batch_op.drop_column("unidad_duracion")
        batch_op.drop_column("duracion_cantidad")
