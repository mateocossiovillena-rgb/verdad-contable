"""registro de riesgos (AACE 44R-08)

Revision ID: e1f4a6b8c203
Revises: d7b3e2c9a114
Create Date: 2026-11-24 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f4a6b8c203"
down_revision: str | Sequence[str] | None = "d7b3e2c9a114"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "riesgo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obra.id", ondelete="CASCADE"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.String(300), nullable=False),
        sa.Column("causa", sa.Text(), nullable=False),
        sa.Column("probabilidad", sa.Numeric(5, 2), nullable=False),
        sa.Column("impacto_costo", sa.Numeric(14, 2), nullable=False),
        sa.Column("impacto_dias", sa.Integer(), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("estrategia", sa.String(12), nullable=False),
        sa.Column("respuesta", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("obra_id", "numero"),
    )
    op.create_index("ix_riesgo_obra_id", "riesgo", ["obra_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_riesgo_obra_id", table_name="riesgo")
    op.drop_table("riesgo")
