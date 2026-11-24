"""Costo de la línea base distribuido por semana: PV semanal y acumulado (curva S).

Usa el mismo reparto lineal por días calendario que `valor_ganado.fraccion_planificada`, así la tabla
semanal y la curva S del Resumen dan el mismo PV en cada fecha.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.calculos import valor_ganado as vg

CERO = Decimal("0")


@dataclass(frozen=True)
class PartidaPlan:
    presupuesto: Decimal
    fecha_inicio: date | None
    fecha_fin: date | None


@dataclass(frozen=True)
class Semana:
    numero: int
    inicio: date
    fin: date
    pv: Decimal
    pv_acumulado: Decimal
    porcentaje_acumulado: Decimal | None  # 0 a 100


def pv_acumulado(partidas: Sequence[PartidaPlan], corte: date) -> Decimal:
    total = CERO
    for p in partidas:
        fraccion = vg.fraccion_planificada(p.fecha_inicio, p.fecha_fin, corte)
        if fraccion is not None:
            total += p.presupuesto * fraccion
    return total


def pv_semanal(partidas: Sequence[PartidaPlan], inicio: date) -> list[Semana]:
    """Semanas de 7 días desde `inicio` hasta la semana en que termina la última partida.

    Las partidas sin fechas no se distribuyen (no hay cuándo): su presupuesto queda fuera de la curva.
    """
    con_fechas = [p for p in partidas if p.fecha_inicio and p.fecha_fin]
    if not con_fechas:
        return []
    fin = max(p.fecha_fin for p in con_fechas)
    bac = sum((p.presupuesto for p in con_fechas), CERO)
    semanas: list[Semana] = []
    anterior = CERO
    desde = inicio
    numero = 1
    while desde <= fin:
        hasta = desde + timedelta(days=6)
        acumulado = vg.redondear_dinero(pv_acumulado(con_fechas, hasta))
        semanas.append(
            Semana(
                numero=numero,
                inicio=desde,
                fin=hasta,
                pv=acumulado - anterior,
                pv_acumulado=acumulado,
                porcentaje_acumulado=None if bac == 0 else (acumulado / bac * 100).quantize(Decimal("0.1")),
            )
        )
        anterior = acumulado
        desde = hasta + timedelta(days=1)
        numero += 1
    return semanas
