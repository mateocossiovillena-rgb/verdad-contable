"""Costo de las actividades a partir de su mano de obra, materiales y equipo, y su análisis de precio unitario (APU)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
CERO = Decimal("0")
CIEN = Decimal("100")


@dataclass(frozen=True)
class DatosRecurso:
    tipo: str  # "mano_obra", "material" o "equipo"
    cantidad: Decimal  # personas, cantidad de material u horas/días de equipo
    precio_unitario: Decimal  # costo por persona o precio por unidad
    por_dia: bool = False  # solo mano de obra: el costo por persona es por día (jornal)


@dataclass(frozen=True)
class CostoActividad:
    mano_obra: Decimal
    materiales: Decimal
    equipo: Decimal = CERO

    @property
    def total(self) -> Decimal:
        return self.mano_obra + self.materiales + self.equipo


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def costo_recurso(r: DatosRecurso, duracion_dias: int) -> Decimal:
    """Personas × costo por persona (× días si es jornal), o cantidad × precio unitario."""
    costo = r.cantidad * r.precio_unitario
    if r.tipo == "mano_obra" and r.por_dia:
        costo *= duracion_dias
    return redondear(costo)


def costo_actividad(recursos: Iterable[DatosRecurso], duracion_dias: int) -> CostoActividad:
    mano_obra = CERO
    materiales = CERO
    equipo = CERO
    for r in recursos:
        if r.tipo == "mano_obra":
            mano_obra += costo_recurso(r, duracion_dias)
        elif r.tipo == "equipo":
            equipo += costo_recurso(r, duracion_dias)
        else:
            materiales += costo_recurso(r, duracion_dias)
    return CostoActividad(mano_obra=mano_obra, materiales=materiales, equipo=equipo)


# --- Análisis de precio unitario (formato usual en Bolivia) ---


@dataclass(frozen=True)
class ParametrosApu:
    """Porcentajes (0 a 100) que se suman al costo directo. Todo en 0 = el precio es el costo directo."""

    cargas_sociales: Decimal = CERO  # sobre la mano de obra
    iva_mano_obra: Decimal = CERO  # sobre mano de obra + cargas sociales
    herramientas: Decimal = CERO  # herramientas menores, sobre el total de mano de obra
    gastos_generales: Decimal = CERO  # sobre materiales + mano de obra + equipo
    utilidad: Decimal = CERO  # sobre costo directo + gastos generales
    impuestos: Decimal = CERO  # IT, sobre costo directo + gastos generales + utilidad


@dataclass(frozen=True)
class Apu:
    materiales: Decimal
    mano_obra: Decimal
    cargas_sociales: Decimal
    iva_mano_obra: Decimal
    equipo: Decimal
    herramientas: Decimal
    gastos_generales: Decimal
    utilidad: Decimal
    impuestos: Decimal

    @property
    def total_mano_obra(self) -> Decimal:
        return self.mano_obra + self.cargas_sociales + self.iva_mano_obra

    @property
    def total_equipo(self) -> Decimal:
        return self.equipo + self.herramientas

    @property
    def costo_directo(self) -> Decimal:
        return self.materiales + self.total_mano_obra + self.total_equipo

    @property
    def total(self) -> Decimal:
        return self.costo_directo + self.gastos_generales + self.utilidad + self.impuestos


def _porcion(base: Decimal, porcentaje: Decimal) -> Decimal:
    return redondear(base * porcentaje / CIEN)


def calcular_apu(costo: CostoActividad, p: ParametrosApu) -> Apu:
    """1 materiales, 2 mano de obra (+ cargas sociales + IVA), 3 equipo (+ herramientas), 4 gastos generales,
    5 utilidad, 6 impuestos. Cada porcentaje se aplica sobre la suma de los anteriores, redondeado a centavos."""
    cargas = _porcion(costo.mano_obra, p.cargas_sociales)
    iva = _porcion(costo.mano_obra + cargas, p.iva_mano_obra)
    herramientas = _porcion(costo.mano_obra + cargas + iva, p.herramientas)
    directo = costo.materiales + costo.mano_obra + cargas + iva + costo.equipo + herramientas
    generales = _porcion(directo, p.gastos_generales)
    utilidad = _porcion(directo + generales, p.utilidad)
    impuestos = _porcion(directo + generales + utilidad, p.impuestos)
    return Apu(
        materiales=costo.materiales,
        mano_obra=costo.mano_obra,
        cargas_sociales=cargas,
        iva_mano_obra=iva,
        equipo=costo.equipo,
        herramientas=herramientas,
        gastos_generales=generales,
        utilidad=utilidad,
        impuestos=impuestos,
    )


def precio_unitario(apu: Apu, computo: Decimal | None) -> Decimal | None:
    """Precio por unidad de la actividad (m², m³, pieza…); None si no tiene cómputo."""
    if not computo:
        return None
    return redondear(apu.total / computo)
