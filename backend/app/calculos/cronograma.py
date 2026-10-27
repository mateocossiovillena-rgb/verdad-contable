"""Fechas del cronograma a partir de duraciones y predecesoras.

Regla: una actividad sin predecesoras empieza en su fecha manual (o la de la obra);
con predecesoras empieza el día siguiente a que termina la última de ellas.
La duración cuenta días calendario e incluye el primero: 3 días desde el lunes terminan el miércoles.

`calcular_fechas` es el "paso hacia adelante" del método de ruta crítica (CPM) y `calcular_holguras` el
"paso hacia atrás": fechas tardías desde el fin de la obra y holgura de cada actividad. Holgura 0 = ruta
crítica: si esa actividad se atrasa un día, la entrega se atrasa un día.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class Enlace:
    """Dependencia fin → comienzo. `desfase_dias` queda listo para esperas (ej. fraguado)."""

    predecesora: int
    desfase_dias: int = 0


@dataclass(frozen=True)
class DatosActividad:
    id: int
    duracion_dias: int
    inicio_manual: date | None = None
    predecesoras: tuple[Enlace, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Fechas:
    inicio: date
    fin: date


@dataclass(frozen=True)
class Holgura:
    inicio_tardio: date
    fin_tardio: date
    dias: int  # cuánto puede atrasarse sin mover el fin de la obra

    @property
    def critica(self) -> bool:
        return self.dias == 0


class DependenciaCircular(ValueError):
    def __init__(self, ciclo: list[int]):
        self.ciclo = ciclo
        super().__init__("Dependencia circular entre actividades")


# Días calendario por unidad de duración que elige el usuario.
UNIDADES_DURACION = {"dias": 1, "semanas": 7, "meses": 30}


def a_dias(cantidad: Decimal, unidad: str) -> int:
    """Duración escrita por el usuario (ej. 1,5 semanas) en días calendario, redondeando hacia arriba."""
    return max(math.ceil(Decimal(cantidad) * UNIDADES_DURACION[unidad]), 1)


def fin_de(inicio: date, duracion_dias: int) -> date:
    return inicio + timedelta(days=max(duracion_dias, 1) - 1)


def orden_topologico(actividades: list[DatosActividad]) -> list[int]:
    """Ids ordenados para que cada actividad vaya después de sus predecesoras.

    Lanza DependenciaCircular con los ids de un ciclo si lo hay.
    """
    ids = {a.id for a in actividades}
    sucesoras: dict[int, list[int]] = {a.id: [] for a in actividades}
    pendientes = {a.id: 0 for a in actividades}
    for a in actividades:
        for e in a.predecesoras:
            if e.predecesora not in ids:
                raise ValueError(f"La predecesora {e.predecesora} no existe")
            sucesoras[e.predecesora].append(a.id)
            pendientes[a.id] += 1

    # Se respeta el orden de entrada entre actividades independientes.
    cola = deque(a.id for a in actividades if pendientes[a.id] == 0)
    orden: list[int] = []
    while cola:
        actual = cola.popleft()
        orden.append(actual)
        for s in sucesoras[actual]:
            pendientes[s] -= 1
            if pendientes[s] == 0:
                cola.append(s)

    if len(orden) < len(actividades):
        raise DependenciaCircular(_buscar_ciclo(actividades, set(orden)))
    return orden


def _buscar_ciclo(actividades: list[DatosActividad], resueltas: set[int]) -> list[int]:
    """Recorre hacia atrás por predecesoras no resueltas hasta repetir una actividad."""
    predecesoras = {
        a.id: [e.predecesora for e in a.predecesoras if e.predecesora not in resueltas] for a in actividades
    }
    actual = next(a.id for a in actividades if a.id not in resueltas)
    camino: list[int] = []
    while actual not in camino:
        camino.append(actual)
        actual = predecesoras[actual][0]
    ciclo = camino[camino.index(actual) :]
    ciclo.reverse()  # en sentido predecesora → sucesora
    return ciclo


def calcular_fechas(actividades: list[DatosActividad], inicio_obra: date) -> dict[int, Fechas]:
    por_id = {a.id: a for a in actividades}
    fechas: dict[int, Fechas] = {}
    for id_ in orden_topologico(actividades):
        a = por_id[id_]
        if a.predecesoras:
            inicio = max(fechas[e.predecesora].fin + timedelta(days=1 + e.desfase_dias) for e in a.predecesoras)
        else:
            inicio = a.inicio_manual or inicio_obra
        fechas[id_] = Fechas(inicio=inicio, fin=fin_de(inicio, a.duracion_dias))
    return fechas


def calcular_holguras(actividades: list[DatosActividad], fechas: dict[int, Fechas]) -> dict[int, Holgura]:
    """Paso hacia atrás sobre fechas ya calculadas (tempranas). El fin de la obra es el fin más tardío."""
    if not actividades:
        return {}
    fin_obra = max(f.fin for f in fechas.values())
    sucesoras: dict[int, list[tuple[int, int]]] = {a.id: [] for a in actividades}
    for a in actividades:
        for e in a.predecesoras:
            sucesoras[e.predecesora].append((a.id, e.desfase_dias))
    holguras: dict[int, Holgura] = {}
    for id_ in reversed(orden_topologico(actividades)):
        fin_tardio = min(
            (holguras[s].inicio_tardio - timedelta(days=1 + desfase) for s, desfase in sucesoras[id_]),
            default=fin_obra,
        )
        duracion = (fechas[id_].fin - fechas[id_].inicio).days
        inicio_tardio = fin_tardio - timedelta(days=duracion)
        holguras[id_] = Holgura(inicio_tardio, fin_tardio, max((inicio_tardio - fechas[id_].inicio).days, 0))
    return holguras
