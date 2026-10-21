"""Fechas del cronograma a partir de duraciones y predecesoras.

Regla: una actividad sin predecesoras empieza en su fecha manual (o la de la obra);
con predecesoras empieza el día siguiente a que termina la última de ellas.
La duración cuenta días calendario e incluye el primero: 3 días desde el lunes terminan el miércoles.

El cálculo es el "paso hacia adelante" del método de ruta crítica (CPM). El paso hacia
atrás (fechas tardías y holguras) se puede agregar después sobre el mismo orden topológico.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date, timedelta


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


class DependenciaCircular(ValueError):
    def __init__(self, ciclo: list[int]):
        self.ciclo = ciclo
        super().__init__("Dependencia circular entre actividades")


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
