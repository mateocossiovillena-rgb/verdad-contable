"""Tablas de la base de datos."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

DINERO = Numeric(14, 2)

ROL_DUENO = "dueno"
ROL_ENCARGADO = "encargado"

TIPOS_GASTO = {
    "material": "Material",
    "mano_obra": "Mano de obra",
    "subcontrato": "Subcontrato",
    "caja_chica": "Caja chica",
    "transporte": "Transporte",
}


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str | None] = mapped_column(String(200), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(30), unique=True)
    rol: Mapped[str] = mapped_column(String(20))
    clave_hash: Mapped[str] = mapped_column(String(200))
    # Los encargados pertenecen al dueño que los invitó.
    dueno_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Obra(Base):
    __tablename__ = "obra"

    id: Mapped[int] = mapped_column(primary_key=True)
    dueno_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(160))
    ubicacion: Mapped[str] = mapped_column(String(200), default="")
    cliente: Mapped[str] = mapped_column(String(160), default="", server_default="")
    fecha_inicio: Mapped[date] = mapped_column(Date)
    # Si la obra tiene cronograma, se ajusta sola al fin de la última actividad.
    fecha_fin: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(8), default="Bs")
    presupuesto_total: Mapped[Decimal | None] = mapped_column(DINERO)
    umbral_amarillo: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.90"))
    umbral_rojo: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.80"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    partidas: Mapped[list[Partida]] = relationship(back_populates="obra", order_by="Partida.orden")


class Asignacion(Base):
    __tablename__ = "asignacion"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), primary_key=True)


class Partida(Base):
    __tablename__ = "partida"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(20), default="")
    nombre: Mapped[str] = mapped_column(String(160))
    fase: Mapped[str] = mapped_column(String(80), default="")
    fecha_inicio: Mapped[date | None] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    presupuesto: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    orden: Mapped[int] = mapped_column(Integer, default=0)
    # Partida automática donde caen los gastos que no se asignan a otra.
    es_generales: Mapped[bool] = mapped_column(Boolean, default=False)
    # Partida de una actividad del cronograma: nombre, fase, fechas y presupuesto (su costo) vienen de la
    # actividad y se actualizan en cada recálculo (`servicios.sincronizar_partidas`).
    desde_cronograma: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    actividad_id: Mapped[int | None] = mapped_column(ForeignKey("actividad.id", ondelete="SET NULL"), unique=True)

    obra: Mapped[Obra] = relationship(back_populates="partidas")


class Hito(Base):
    __tablename__ = "hito"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(160))
    fecha_prevista: Mapped[date] = mapped_column(Date)
    fecha_real: Mapped[date | None] = mapped_column(Date)


class Avance(Base):
    """Observación de avance físico. Solo se agregan; nunca se editan."""

    __tablename__ = "avance"

    id: Mapped[int] = mapped_column(primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id", ondelete="CASCADE"), index=True)
    fecha: Mapped[date] = mapped_column(Date)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    nota: Mapped[str] = mapped_column(Text, default="")
    foto: Mapped[str | None] = mapped_column(String(80))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    # Identificador generado en el celular para no duplicar al reenviar sin señal.
    id_cliente: Mapped[str | None] = mapped_column(String(64), unique=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Gasto(Base):
    """Gasto de obra. No se borra: se anula indicando el motivo."""

    __tablename__ = "gasto"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), index=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    monto: Mapped[Decimal] = mapped_column(DINERO)
    tipo: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    con_factura: Mapped[bool] = mapped_column(Boolean, default=False)
    foto: Mapped[str | None] = mapped_column(String(80))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    id_cliente: Mapped[str | None] = mapped_column(String(64), unique=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str] = mapped_column(Text, default="")
    anulado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))


class CierreDia(Base):
    __tablename__ = "cierre_dia"
    __table_args__ = (UniqueConstraint("obra_id", "fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), index=True)
    fecha: Mapped[date] = mapped_column(Date)
    total_dia: Mapped[Decimal] = mapped_column(DINERO)
    acumulado: Mapped[Decimal] = mapped_column(DINERO)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


# --- Cronograma ---


class Fase(Base):
    """Agrupa actividades del cronograma (ej. Obra gruesa, Instalaciones, Acabados)."""

    __tablename__ = "fase"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    orden: Mapped[int] = mapped_column(Integer, default=0)

    actividades: Mapped[list[Actividad]] = relationship(
        back_populates="fase", order_by="Actividad.orden", cascade="all, delete-orphan", passive_deletes=True
    )


class Actividad(Base):
    """Tarea del cronograma. `fecha_inicio`/`fecha_fin` se recalculan al guardar (paso adelante del CPM).

    La holgura y la ruta crítica se calculan al leer (`calculos.cronograma.calcular_holguras`).
    """

    __tablename__ = "actividad"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), index=True)
    fase_id: Mapped[int] = mapped_column(ForeignKey("fase.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(160))
    duracion_dias: Mapped[int] = mapped_column(Integer)
    # Lo que eligió el usuario; solo se usa si la actividad no tiene predecesoras.
    inicio_manual: Mapped[date | None] = mapped_column(Date)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    orden: Mapped[int] = mapped_column(Integer, default=0)

    fase: Mapped[Fase] = relationship(back_populates="actividades")
    predecesoras: Mapped[list[Dependencia]] = relationship(
        foreign_keys="Dependencia.sucesora_id", cascade="all, delete-orphan", passive_deletes=True
    )
    recursos: Mapped[list[RecursoActividad]] = relationship(
        order_by="RecursoActividad.orden", cascade="all, delete-orphan", passive_deletes=True
    )


class Dependencia(Base):
    """Enlace predecesora → sucesora, fin-comienzo (FC). `desfase_dias` es una espera entre las dos
    (ej. fraguado de la losa); `tipo` queda para otros tipos de enlace."""

    __tablename__ = "dependencia"

    predecesora_id: Mapped[int] = mapped_column(ForeignKey("actividad.id", ondelete="CASCADE"), primary_key=True)
    sucesora_id: Mapped[int] = mapped_column(ForeignKey("actividad.id", ondelete="CASCADE"), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(2), default="FC", server_default="FC")
    desfase_dias: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


TIPOS_RECURSO = {"mano_obra": "Mano de obra", "material": "Material"}


class RecursoActividad(Base):
    """Mano de obra o material de una actividad. El costo se calcula al leer (depende de la duración).

    Mano de obra: `cantidad` = personas, `precio_unitario` = costo por persona; si `por_dia`,
    se multiplica por la duración de la actividad (jornal). Material: cantidad × precio unitario.
    """

    __tablename__ = "recurso_actividad"

    id: Mapped[int] = mapped_column(primary_key=True)
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(160))
    unidad: Mapped[str] = mapped_column(String(20), default="", server_default="")
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    precio_unitario: Mapped[Decimal] = mapped_column(DINERO)
    por_dia: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    orden: Mapped[int] = mapped_column(Integer, default=0)


# --- Estimación desde plano (CAD o BIM) ---


class Estimacion(Base):
    """Asistente "Estimar desde plano" de una obra: lo leído del archivo y lo que confirmó el dueño.

    `paso` es el paso del asistente en el que quedó. CAD (dxf): capas → plantas → formulario → cantidades →
    confirmada → generada. BIM (ifc): plantas → cantidades → confirmada → generada (el modelo responde el
    formulario). `ejecucion` guarda cómo se va a ejecutar (inicio, días por semana, cuadrillas) al generar.
    Las cantidades no se guardan: se calculan al leer con `medicion` y `formulario`. Solo se guardan las
    correcciones a mano (`ediciones`), así no se pierden si se vuelve a un paso anterior.
    """

    __tablename__ = "estimacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", ondelete="CASCADE"), index=True)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    tipo_archivo: Mapped[str] = mapped_column(String(4))
    nombre_archivo: Mapped[str] = mapped_column(String(200))
    # Nombre aleatorio en la carpeta de planos; nunca se sirve en público.
    archivo: Mapped[str] = mapped_column(String(80))
    paso: Mapped[str] = mapped_column(String(20))
    unidades: Mapped[int | None] = mapped_column(Integer)
    lectura: Mapped[dict] = mapped_column(JSON, default=dict)
    capas: Mapped[dict] = mapped_column(JSON, default=dict)
    plantas: Mapped[list] = mapped_column(JSON, default=list)
    formulario: Mapped[dict | None] = mapped_column(JSON)
    medicion: Mapped[dict | None] = mapped_column(JSON)
    ediciones: Mapped[dict] = mapped_column(JSON, default=dict)
    ejecucion: Mapped[dict | None] = mapped_column(JSON)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


class MapeoCapa(Base):
    """Rol que el dueño le dio a una capa CAD, para sugerirlo igual en su próximo plano."""

    __tablename__ = "mapeo_capa"
    __table_args__ = (UniqueConstraint("dueno_id", "capa"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dueno_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    capa: Mapped[str] = mapped_column(String(120))  # nombre normalizado (mayúsculas, sin tildes)
    rol: Mapped[str] = mapped_column(String(20))
