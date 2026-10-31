"""Cálculo de valor ganado (EVM, PMBOK) para partidas y obras.

Funciones puras: no tocan la base de datos ni la API, solo reciben datos y
devuelven resultados. Todo el dinero se maneja con Decimal.

Convenciones:
- El porcentaje de avance va de 0 a 100.
- La fecha de corte se considera al final de ese día.
- Si un índice no se puede calcular (división entre cero) se devuelve None,
  nunca 0: la interfaz debe mostrarlo como "sin dato".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CERO = Decimal("0")
UNO = Decimal("1")
CIEN = Decimal("100")

DIAS_GASTO_SIN_AVANCE = 7


@dataclass(frozen=True)
class RegistroAvance:
    fecha: date
    porcentaje: Decimal


@dataclass(frozen=True)
class RegistroGasto:
    fecha: date
    monto: Decimal


@dataclass
class DatosPartida:
    nombre: str
    presupuesto: Decimal
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    # En el orden en que se registraron (el último del mismo día manda).
    avances: Sequence[RegistroAvance] = ()
    gastos: Sequence[RegistroGasto] = ()
    id: int | None = None
    # Gastos generales: costo indirecto sin avance físico. Se "gana" con el tiempo (EV = PV, nivel de esfuerzo
    # en PMBOK), así no atrasa a la obra ni da avisos de fechas o avance.
    es_generales: bool = False


@dataclass(frozen=True)
class Indicadores:
    bac: Decimal
    pv: Decimal
    ev: Decimal
    ac: Decimal
    sv: Decimal
    cv: Decimal
    spi: Decimal | None
    cpi: Decimal | None
    eac: Decimal | None
    # Fracciones de 0 a 1 (o más, si se gastó más que el presupuesto).
    avance_planificado: Decimal | None  # PV / BAC
    avance_real: Decimal | None  # EV / BAC
    avance_esperado_por_gasto: Decimal | None  # AC / BAC


@dataclass(frozen=True)
class Advertencia:
    codigo: str
    mensaje: str


@dataclass
class ResultadoPartida:
    datos: DatosPartida
    porcentaje_avance: Decimal
    indicadores: Indicadores
    advertencias: list[Advertencia] = field(default_factory=list)


@dataclass
class ResultadoObra:
    indicadores: Indicadores
    partidas: list[ResultadoPartida]
    advertencias: list[Advertencia] = field(default_factory=list)


@dataclass(frozen=True)
class PuntoCurva:
    fecha: date
    pv: Decimal
    ev: Decimal | None
    ac: Decimal | None


def dividir(numerador: Decimal, denominador: Decimal) -> Decimal | None:
    if denominador == 0:
        return None
    return numerador / denominador


def redondear_dinero(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def formatear_bs(valor: Decimal) -> str:
    """Formato boliviano: Bs 12.345,67"""
    texto = f"{redondear_dinero(valor):,.2f}"
    return "Bs " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def redondear_indice(valor: Decimal | None) -> Decimal | None:
    if valor is None:
        return None
    return valor.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def fraccion_planificada(inicio: date | None, fin: date | None, corte: date) -> Decimal | None:
    """Parte del trabajo que debería estar hecha al final del día `corte`.

    Reparto lineal por días calendario entre inicio y fin (ambos incluidos).
    Devuelve None si faltan fechas.
    """
    if inicio is None or fin is None:
        return None
    if fin < inicio:
        raise ValueError("La fecha de fin no puede ser anterior a la de inicio")
    if corte < inicio:
        return CERO
    if corte >= fin:
        return UNO
    dias_totales = (fin - inicio).days + 1
    dias_transcurridos = (corte - inicio).days + 1
    return Decimal(dias_transcurridos) / Decimal(dias_totales)


def avance_a_la_fecha(avances: Sequence[RegistroAvance], corte: date) -> Decimal:
    """Último porcentaje registrado con fecha <= corte (0 si no hay ninguno)."""
    vigentes = [(a.fecha, i, a.porcentaje) for i, a in enumerate(avances) if a.fecha <= corte]
    if not vigentes:
        return CERO
    return max(vigentes)[2]


def costo_a_la_fecha(gastos: Sequence[RegistroGasto], corte: date) -> Decimal:
    return sum((g.monto for g in gastos if g.fecha <= corte), CERO)


def calcular_indicadores(bac: Decimal, pv: Decimal, ev: Decimal, ac: Decimal) -> Indicadores:
    cpi = dividir(ev, ac)
    # EAC = BAC / CPI, escrito como BAC * AC / EV para no arrastrar decimales periódicos.
    eac = None if cpi is None or cpi == 0 else bac * ac / ev
    return Indicadores(
        bac=bac,
        pv=pv,
        ev=ev,
        ac=ac,
        sv=ev - pv,
        cv=ev - ac,
        spi=dividir(ev, pv),
        cpi=cpi,
        eac=eac,
        avance_planificado=dividir(pv, bac),
        avance_real=dividir(ev, bac),
        avance_esperado_por_gasto=dividir(ac, bac),
    )


def _advertencias_partida(p: DatosPartida, porcentaje: Decimal, ac: Decimal, corte: date) -> list[Advertencia]:
    avisos: list[Advertencia] = []
    if ac > p.presupuesto:
        if p.presupuesto == 0:
            avisos.append(Advertencia("gasto_sin_presupuesto", "Tiene gastos pero no tiene presupuesto."))
        else:
            avisos.append(Advertencia("gasto_supera_presupuesto", "Lo gastado ya supera su presupuesto."))
    if p.es_generales:
        return avisos
    if p.presupuesto > 0 and (p.fecha_inicio is None or p.fecha_fin is None):
        avisos.append(Advertencia("sin_fechas", "No tiene fechas: no se puede saber cuánto debería llevar."))
    fechas_gasto = [g.fecha for g in p.gastos if g.fecha <= corte]
    if fechas_gasto and porcentaje == 0:
        dias = (corte - min(fechas_gasto)).days
        if dias > DIAS_GASTO_SIN_AVANCE and p.presupuesto > 0:
            avisos.append(Advertencia("gasto_sin_avance", f"Tiene gastos desde hace {dias} días y 0 % de avance."))
    if porcentaje >= CIEN and ac == 0 and p.presupuesto > 0:
        avisos.append(Advertencia("terminada_sin_gastos", "Está al 100 % pero no tiene gastos registrados."))
    return avisos


def calcular_partida(p: DatosPartida, corte: date) -> ResultadoPartida:
    fraccion = fraccion_planificada(p.fecha_inicio, p.fecha_fin, corte)
    porcentaje = avance_a_la_fecha(p.avances, corte)
    ac = costo_a_la_fecha(p.gastos, corte)
    pv = p.presupuesto * fraccion if fraccion is not None else CERO
    ev = pv if p.es_generales else p.presupuesto * porcentaje / CIEN
    return ResultadoPartida(
        datos=p,
        porcentaje_avance=porcentaje,
        indicadores=calcular_indicadores(p.presupuesto, pv, ev, ac),
        advertencias=_advertencias_partida(p, porcentaje, ac, corte),
    )


def calcular_obra(partidas: Sequence[DatosPartida], corte: date) -> ResultadoObra:
    resultados = [calcular_partida(p, corte) for p in partidas]
    bac = sum((r.indicadores.bac for r in resultados), CERO)
    pv = sum((r.indicadores.pv for r in resultados), CERO)
    ev = sum((r.indicadores.ev for r in resultados), CERO)
    ac = sum((r.indicadores.ac for r in resultados), CERO)
    totales = calcular_indicadores(bac, pv, ev, ac)
    avisos: list[Advertencia] = []
    if bac > 0 and ac > bac:
        avisos.append(Advertencia("obra_supera_presupuesto", "Lo gastado en la obra ya supera el presupuesto total."))
    if totales.eac is not None and bac > 0 and totales.eac > bac:
        exceso = formatear_bs(totales.eac - bac)
        avisos.append(
            Advertencia(
                "proyeccion_supera_presupuesto", f"A este ritmo la obra costará {exceso} más de lo presupuestado."
            )
        )
    return ResultadoObra(indicadores=totales, partidas=resultados, advertencias=avisos)


def calcular_curva(partidas: Sequence[DatosPartida], fechas: Sequence[date], hoy: date) -> list[PuntoCurva]:
    """PV para todas las fechas; EV y AC solo hasta `hoy` (el futuro no se conoce)."""
    puntos: list[PuntoCurva] = []
    for f in fechas:
        totales = calcular_obra(partidas, f).indicadores
        conocido = f <= hoy
        puntos.append(
            PuntoCurva(
                fecha=f,
                pv=totales.pv,
                ev=totales.ev if conocido else None,
                ac=totales.ac if conocido else None,
            )
        )
    return puntos


def semaforo(ind: Indicadores, umbral_amarillo: Decimal, umbral_rojo: Decimal) -> str:
    """'verde', 'amarillo', 'rojo' o 'sin_dato' según SPI, CPI y el gasto total."""
    if ind.bac == 0:
        return "sin_dato"
    if ind.ac > ind.bac:
        return "rojo"
    indices = [i for i in (ind.spi, ind.cpi) if i is not None]
    if not indices:
        return "sin_dato"
    peor = min(indices)
    if peor < umbral_rojo:
        return "rojo"
    if peor < umbral_amarillo:
        return "amarillo"
    return "verde"


def _pct(fraccion: Decimal) -> str:
    return f"{(fraccion * CIEN).quantize(UNO, rounding=ROUND_HALF_UP)} %"


def frases_resumen(ind: Indicadores) -> list[str]:
    """Frases cortas en lenguaje de obra para el dueño."""
    frases: list[str] = []
    if ind.bac == 0:
        return ["Todavía no hay presupuesto cargado."]
    gastado = ind.avance_esperado_por_gasto or CERO
    real = ind.avance_real or CERO
    frases.append(f"Gastaste el {_pct(gastado)} del presupuesto y avanzaste el {_pct(real)}.")
    if gastado > real:
        frases.append("Estás gastando más de lo que avanzas.")
    elif ind.ac > 0:
        frases.append("Tu gasto va de acuerdo con el avance.")
    if ind.avance_planificado is not None and ind.pv > 0:
        plan = ind.avance_planificado
        if real < plan:
            frases.append(f"Según el cronograma deberías ir en {_pct(plan)}: vas atrasado.")
        else:
            frases.append(f"Según el cronograma deberías ir en {_pct(plan)}: vas a tiempo.")
    return frases
