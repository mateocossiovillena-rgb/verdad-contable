"""Costo de las actividades a partir de su mano de obra y materiales."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class DatosRecurso:
    tipo: str  # "mano_obra" o "material"
    cantidad: Decimal  # personas o cantidad de material
    precio_unitario: Decimal  # costo por persona o precio por unidad
    por_dia: bool = False  # solo mano de obra: el costo por persona es por día (jornal)


@dataclass(frozen=True)
class CostoActividad:
    mano_obra: Decimal
    materiales: Decimal

    @property
    def total(self) -> Decimal:
        return self.mano_obra + self.materiales


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def costo_recurso(r: DatosRecurso, duracion_dias: int) -> Decimal:
    """Personas × costo por persona (× días si es jornal), o cantidad × precio unitario."""
    costo = r.cantidad * r.precio_unitario
    if r.tipo == "mano_obra" and r.por_dia:
        costo *= duracion_dias
    return redondear(costo)


def costo_actividad(recursos: Iterable[DatosRecurso], duracion_dias: int) -> CostoActividad:
    mano_obra = Decimal("0")
    materiales = Decimal("0")
    for r in recursos:
        if r.tipo == "mano_obra":
            mano_obra += costo_recurso(r, duracion_dias)
        else:
            materiales += costo_recurso(r, duracion_dias)
    return CostoActividad(mano_obra=mano_obra, materiales=materiales)
