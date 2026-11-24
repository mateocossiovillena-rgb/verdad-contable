"""Clase del estimado a partir del checklist de entregables (tabla editable en `clases_estimado.toml`).

Funciones puras: reciben el checklist y la tabla, devuelven el % de definición y la clase.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path

ARCHIVO = Path(__file__).with_name("clases_estimado.toml")
ESTADOS = ("no", "parcial", "completo")
CIEN = Decimal("100")


@dataclass(frozen=True)
class Entregable:
    clave: str
    nombre: str
    peso: Decimal


@dataclass(frozen=True)
class Clase:
    clase: int
    desde: Decimal
    definicion_norma: str
    uso: str
    metodologia: str
    exactitud_baja: tuple[int, int]  # % negativos, del rango típico (ej. -20 a -30)
    exactitud_alta: tuple[int, int]


@dataclass(frozen=True)
class TablaClases:
    avance: dict[str, Decimal]
    entregables: tuple[Entregable, ...]
    clases: tuple[Clase, ...]  # de clase 5 a clase 1


@dataclass(frozen=True)
class Resultado:
    porcentaje_definicion: Decimal
    clase: Clase
    # Rango del total estimado según la exactitud: el extremo más amplio de cada lado.
    minimo: Decimal | None
    maximo: Decimal | None


class TablaInvalida(ValueError):
    pass


def leer_tabla(texto: str) -> TablaClases:
    datos = tomllib.loads(texto)
    avance = {k: Decimal(str(v)) for k, v in datos["avance"].items()}
    if set(avance) != set(ESTADOS):
        raise TablaInvalida(f"[avance] debe tener exactamente: {', '.join(ESTADOS)}")
    entregables = tuple(Entregable(e["clave"], e["nombre"], Decimal(str(e["peso"]))) for e in datos["entregables"])
    if sum(e.peso for e in entregables) != CIEN:
        raise TablaInvalida("Los pesos de los entregables deben sumar 100")
    clases = tuple(
        sorted(
            (
                Clase(
                    clase=int(c["clase"]),
                    desde=Decimal(str(c["desde"])),
                    definicion_norma=c["definicion_norma"],
                    uso=c["uso"],
                    metodologia=c["metodologia"],
                    exactitud_baja=tuple(c["exactitud_baja"]),
                    exactitud_alta=tuple(c["exactitud_alta"]),
                )
                for c in datos["clases"]
            ),
            key=lambda c: c.desde,
        )
    )
    if not clases or clases[0].desde != 0:
        raise TablaInvalida("Debe haber una clase con desde = 0")
    return TablaClases(avance=avance, entregables=entregables, clases=clases)


@cache
def tabla() -> TablaClases:
    return leer_tabla(ARCHIVO.read_text(encoding="utf-8"))


def porcentaje_definicion(checklist: Mapping[str, str], t: TablaClases) -> Decimal:
    """Suma de peso × avance. Entregables que faltan en el checklist cuentan como "no"."""
    total = sum((e.peso * t.avance[checklist.get(e.clave, "no")] for e in t.entregables), Decimal("0"))
    return total.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def clase_para(porcentaje: Decimal, t: TablaClases) -> Clase:
    return [c for c in t.clases if c.desde <= porcentaje][-1]


def clasificar(checklist: Mapping[str, str], t: TablaClases, total_estimado: Decimal | None = None) -> Resultado:
    pct = porcentaje_definicion(checklist, t)
    c = clase_para(pct, t)
    minimo = maximo = None
    if total_estimado:
        peor_bajo = min(c.exactitud_baja)  # el más negativo
        peor_alto = max(c.exactitud_alta)
        centavo = Decimal("0.01")
        minimo = (total_estimado * (CIEN + peor_bajo) / CIEN).quantize(centavo, rounding=ROUND_HALF_UP)
        maximo = (total_estimado * (CIEN + peor_alto) / CIEN).quantize(centavo, rounding=ROUND_HALF_UP)
    return Resultado(porcentaje_definicion=pct, clase=c, minimo=minimo, maximo=maximo)
