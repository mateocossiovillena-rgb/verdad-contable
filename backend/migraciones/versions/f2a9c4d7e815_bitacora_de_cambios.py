"""bitácora de cambios y cambio que generó cada línea base

Revision ID: f2a9c4d7e815
Revises: e1f4a6b8c203
Create Date: 2026-11-24 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a9c4d7e815"
down_revision: str | Sequence[str] | None = "e1f4a6b8c203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cambio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obra.id", ondelete="CASCADE"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("solicitante", sa.String(120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("impacto_costo", sa.Numeric(14, 2), nullable=False),
        sa.Column("impacto_dias", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False),
        sa.Column("aprobador", sa.String(120), nullable=False),
        sa.Column("fecha_resolucion", sa.Date(), nullable=True),
        sa.Column("comentario_resolucion", sa.Text(), nullable=False),
        sa.Column("partida_id", sa.Integer(), sa.ForeignKey("partida.id", ondelete="SET NULL"), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("obra_id", "numero"),
    )
    op.create_index("ix_cambio_obra_id", "cambio", ["obra_id"])
    with op.batch_alter_table("linea_base", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cambio_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_linea_base_cambio", "cambio", ["cambio_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("linea_base", schema=None) as batch_op:
        batch_op.drop_constraint("fk_linea_base_cambio", type_="foreignkey")
        batch_op.drop_column("cambio_id")
    op.drop_index("ix_cambio_obra_id", table_name="cambio")
    op.drop_table("cambio")
