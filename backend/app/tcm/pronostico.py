"""Pronóstico del costo final (AACE 80R-13) a partir de los valores de valor ganado (AACE 82R-13).

Nomenclatura AACE / equivalencia clásica:
PV = BCWS (valor planificado), EV = BCWP (valor ganado), AC = ACWP (costo real), BAC = presupuesto a la conclusión.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.calculos import valor_ganado as vg


@dataclass(frozen=True)
class Pronostico:
    clave: str
    nombre: str
    formula: str
    supuesto: str
    eac: Decimal | None
    etc: Decimal | None  # costo para terminar = EAC − AC
    vac: Decimal | None  # variación a la conclusión = BAC − EAC (negativa = sobrecosto)


def _pronostico(clave, nombre, formula, supuesto, eac: Decimal | None, bac: Decimal, ac: Decimal) -> Pronostico:
    if eac is None:
        return Pronostico(clave, nombre, formula, supuesto, None, None, None)
    eac = vg.redondear_dinero(eac)
    return Pronostico(
        clave, nombre, formula, supuesto, eac, eac - vg.redondear_dinero(ac), vg.redondear_dinero(bac) - eac
    )


def pronosticos(ind: vg.Indicadores) -> list[Pronostico]:
    """Tres EAC de 80R-13; None cuando falta un índice (sin avance o sin gasto)."""
    bac, ev, ac, cpi, spi = ind.bac, ind.ev, ind.ac, ind.cpi, ind.spi
    restante = bac - ev
    atipico = ac + restante
    por_cpi = None if not cpi else bac / cpi
    por_ambos = None if not cpi or not spi else ac + restante / (cpi * spi)
    return [
        _pronostico(
            "atipico",
            "Desvío atípico",
            "EAC = AC + (BAC − EV)",
            "Lo que falta se hará al costo presupuestado: el desvío de hasta hoy no se repite.",
            atipico,
            bac,
            ac,
        ),
        _pronostico(
            "cpi",
            "Eficiencia de costo actual",
            "EAC = BAC / CPI",
            "Lo que falta costará con la misma eficiencia (CPI) que hasta hoy.",
            por_cpi,
            bac,
            ac,
        ),
        _pronostico(
            "cpi_spi",
            "Costo y cronograma",
            "EAC = AC + (BAC − EV) / (CPI × SPI)",
            "El atraso también encarece lo que falta (más días de cuadrilla y gastos generales).",
            por_ambos,
            bac,
            ac,
        ),
    ]


def tcpi(ind: vg.Indicadores) -> Decimal | None:
    """Índice de desempeño para terminar dentro del BAC: (BAC − EV) / (BAC − AC)."""
    return vg.dividir(ind.bac - ind.ev, ind.bac - ind.ac)
