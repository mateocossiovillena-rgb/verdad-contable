"""partidas desde el cronograma

Revision ID: a1c7e5d20b3f
Revises: 0ee866022a51
Create Date: 2026-10-24 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c7e5d20b3f"
down_revision: str | Sequence[str] | None = "0ee866022a51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("partida", schema=None) as batch_op:
        batch_op.add_column(sa.Column("desde_cronograma", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("actividad_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint("uq_partida_actividad_id", ["actividad_id"])
        batch_op.create_foreign_key(
            "fk_partida_actividad_id", "actividad", ["actividad_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("partida", schema=None) as batch_op:
        batch_op.drop_constraint("fk_partida_actividad_id", type_="foreignkey")
        batch_op.drop_constraint("uq_partida_actividad_id", type_="unique")
        batch_op.drop_column("actividad_id")
        batch_op.drop_column("desde_cronograma")
