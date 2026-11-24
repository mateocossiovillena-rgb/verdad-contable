"""kit TCM: estimado (APU, clase, base del estimado) y línea base versionada

Revision ID: c4d2a8e61f05
Revises: b3e9f41c7a20
Create Date: 2026-11-24 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d2a8e61f05"
down_revision: str | Sequence[str] | None = "b3e9f41c7a20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PORCENTAJE = sa.Numeric(6, 2)
DINERO = sa.Numeric(14, 2)


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("actividad", schema=None) as batch_op:
        batch_op.add_column(sa.Column("codigo", sa.String(20), server_default="", nullable=False))
        batch_op.add_column(sa.Column("unidad", sa.String(20), server_default="", nullable=False))
        batch_op.add_column(sa.Column("computo", sa.Numeric(14, 3), nullable=True))
    with op.batch_alter_table("recurso_actividad", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rendimiento", sa.Numeric(14, 4), nullable=True))

    op.create_table(
        "parametros_apu",
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obra.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cargas_sociales", PORCENTAJE, nullable=False),
        sa.Column("iva_mano_obra", PORCENTAJE, nullable=False),
        sa.Column("herramientas", PORCENTAJE, nullable=False),
        sa.Column("gastos_generales", PORCENTAJE, nullable=False),
        sa.Column("utilidad", PORCENTAJE, nullable=False),
        sa.Column("impuestos", PORCENTAJE, nullable=False),
    )
    op.create_table(
        "clasificacion_estimado",
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obra.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entregables", sa.JSON(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "base_estimado",
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obra.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("proposito", sa.Text(), nullable=False),
        sa.Column("alcance", sa.Text(), nullable=False),
        sa.Column("metodologia", sa.Text(), nullable=False),
        sa.Column("base_diseno", sa.Text(), nullable=False),
        sa.Column("base_planificacion", sa.Text(), nullable=False),
        sa.Column("fuentes_precios", sa.Text(), nullable=False),
        sa.Column("fecha_precios", sa.Date(), nullable=True),
        sa.Column("supuestos", sa.Text(), nullable=False),
        sa.Column("exclusiones", sa.Text(), nullable=False),
        sa.Column("riesgos_oportunidades", sa.Text(), nullable=False),
        sa.Column("contingencia_porcentaje", sa.Numeric(5, 2), nullable=False),
        sa.Column("contingencia_nota", sa.Text(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "linea_base",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obra.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("aprobada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aprobada_por", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("bac", DINERO, nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("clase", sa.Integer(), nullable=True),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("obra_id", "version"),
    )
    op.create_index("ix_linea_base_obra_id", "linea_base", ["obra_id"])
    op.create_table(
        "linea_base_partida",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "linea_base_id", sa.Integer(), sa.ForeignKey("linea_base.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("partida_id", sa.Integer(), sa.ForeignKey("partida.id", ondelete="SET NULL"), nullable=True),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("fase", sa.String(80), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("presupuesto", DINERO, nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
    )
    op.create_index("ix_linea_base_partida_linea_base_id", "linea_base_partida", ["linea_base_id"])
    op.create_index("ix_linea_base_partida_partida_id", "linea_base_partida", ["partida_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_linea_base_partida_partida_id", table_name="linea_base_partida")
    op.drop_index("ix_linea_base_partida_linea_base_id", table_name="linea_base_partida")
    op.drop_table("linea_base_partida")
    op.drop_index("ix_linea_base_obra_id", table_name="linea_base")
    op.drop_table("linea_base")
    op.drop_table("base_estimado")
    op.drop_table("clasificacion_estimado")
    op.drop_table("parametros_apu")
    with op.batch_alter_table("recurso_actividad", schema=None) as batch_op:
        batch_op.drop_column("rendimiento")
    with op.batch_alter_table("actividad", schema=None) as batch_op:
        batch_op.drop_column("computo")
        batch_op.drop_column("unidad")
        batch_op.drop_column("codigo")
