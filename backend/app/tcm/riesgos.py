"""Registro de riesgos (AACE 44R-08): valor esperado P × I, nivel y contingencia sugerida.

Funciones puras. La probabilidad va de 0 a 100 (%); el impacto en dinero (moneda de la obra) y en días.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CERO = Decimal("0")
CIEN = Decimal("100")

ESTADOS = {"abierto": "Abierto", "ocurrido": "Ocurrido", "cerrado": "Cerrado"}
ESTRATEGIAS = {"evitar": "Evitar", "mitigar": "Mitigar", "transferir": "Transferir", "aceptar": "Aceptar"}


@dataclass(frozen=True)
class DatosRiesgo:
    probabilidad: Decimal  # 0 a 100
    impacto_costo: Decimal
    impacto_dias: int
    estado: str = "abierto"


def valor_esperado(r: DatosRiesgo) -> Decimal:
    """P × I en dinero, redondeado a centavos."""
    return (r.probabilidad / CIEN * r.impacto_costo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def dias_esperados(r: DatosRiesgo) -> Decimal:
    return (r.probabilidad / CIEN * r.impacto_dias).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _grado_probabilidad(p: Decimal) -> int:
    return 1 if p <= 30 else 2 if p <= 60 else 3


def _grado_impacto(impacto: Decimal, total_estimado: Decimal | None) -> int:
    """Impacto relativo al estimado: hasta 1 % bajo, hasta 5 % medio, más alto. Sin estimado: medio."""
    if not total_estimado:
        return 2
    fraccion = impacto / total_estimado
    return 1 if fraccion <= Decimal("0.01") else 2 if fraccion <= Decimal("0.05") else 3


def nivel(r: DatosRiesgo, total_estimado: Decimal | None) -> str:
    """Matriz 3 × 3 de probabilidad por impacto: "bajo" (1–2), "medio" (3–4) o "alto" (6–9)."""
    puntaje = _grado_probabilidad(r.probabilidad) * _grado_impacto(r.impacto_costo, total_estimado)
    return "bajo" if puntaje <= 2 else "medio" if puntaje <= 4 else "alto"


@dataclass(frozen=True)
class Resumen:
    abiertos: int
    valor_esperado: Decimal  # suma P × I de los abiertos = contingencia sugerida
    dias_esperados: Decimal
    porcentaje_del_estimado: Decimal | None  # 0 a 100


def resumir(riesgos: Iterable[DatosRiesgo], total_estimado: Decimal | None) -> Resumen:
    abiertos = [r for r in riesgos if r.estado == "abierto"]
    ve = sum((valor_esperado(r) for r in abiertos), CERO)
    dias = sum((dias_esperados(r) for r in abiertos), CERO)
    pct = None if not total_estimado else (ve / total_estimado * CIEN).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Resumen(abiertos=len(abiertos), valor_esperado=ve, dias_esperados=dias, porcentaje_del_estimado=pct)
