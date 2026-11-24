"""regla de medición del avance por partida (0/100, 50/50, % físico)

Revision ID: d7b3e2c9a114
Revises: c4d2a8e61f05
Create Date: 2026-11-24 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7b3e2c9a114"
down_revision: str | Sequence[str] | None = "c4d2a8e61f05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("partida", schema=None) as batch_op:
        batch_op.add_column(sa.Column("regla_medicion", sa.String(12), server_default="porcentaje", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("partida", schema=None) as batch_op:
        batch_op.drop_column("regla_medicion")
