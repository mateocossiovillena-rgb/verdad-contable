"""De las cantidades al cronograma: pasos del proyecto, duraciones, cuadrillas, costos y ruta crítica.

Sin base de datos. Entra lo que salió del plano (cantidades por rubro y piso), el formulario y cómo se va a
ejecutar la obra (fecha de inicio, días de trabajo por semana, cuadrillas por oficio); sale una propuesta
que el servicio guarda con las mismas tablas del cronograma.

1. Pasos: secuencia constructiva tipo (plan §8.1), repetida por piso. Un paso sin cantidad no se crea y
   sus sucesoras heredan sus predecesoras (sin cubierta de teja no hay "Cubierta de teja").
2. Duración: días de trabajo = cantidad ÷ (rendimiento × cuadrillas del oficio), pasados a días calendario
   según los días de trabajo por semana.
3. Cuadrillas compartidas (plan §8.2): dos pasos del mismo oficio no van en paralelo; va primero el que
   puede empezar antes (si empiezan juntos, el de menor holgura) y se agrega una predecesora "por
   cuadrilla". Los oficios subcontratados no compiten.
5. Se quitan las predecesoras que ya están implícitas en otra (A → B → C no necesita A → C).
4. Ruta crítica y sugerencia: qué oficio de la ruta crítica acorta más la obra con una cuadrilla más.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal

from app.calculos import costos
from app.calculos import cronograma as cr
from app.calculos.catalogo import (
    CATALOGO,
    FACTOR_ACABADO,
    FIERRO,
    FRACCION_COLUMNAS,
    FRAGUADO_DIAS,
    JORNALES,
    OFICIOS,
    Rubro,
)
from app.calculos.computos import Formulario

MAX_NIVELACIONES = 400


@dataclass(frozen=True)
class CantidadRubro:
    rubro: str
    piso: str | None
    cantidad: float
    unidad: str


@dataclass(frozen=True)
class Ejecucion:
    fecha_inicio: date
    dias_semana: int = 6
    entrega_deseada: date | None = None
    cuadrillas: dict[str, int] = field(default_factory=dict)  # por oficio; 1 si no se dice
    subcontratos: frozenset[str] = frozenset()  # oficios que no compiten por cuadrilla

    def cuadrillas_de(self, oficio: str) -> int:
        return max(self.cuadrillas.get(oficio, 1), 1)


@dataclass(frozen=True)
class Recurso:
    tipo: str  # mano_obra o material
    descripcion: str
    unidad: str
    cantidad: float
    precio_unitario: float
    por_dia: bool


@dataclass(frozen=True)
class EnlacePaso:
    predecesora: str  # clave del paso
    desfase_dias: int
    origen: str  # tecnica (secuencia constructiva) o cuadrilla (nivelación)


@dataclass
class Paso:
    clave: str
    nombre: str
    fase: str
    oficio: str
    cantidad: float | None
    unidad: str
    dias_trabajo: int
    duracion_dias: int  # calendario
    personas: int
    recursos: list[Recurso]
    predecesoras: list[EnlacePaso]
    inicio: date | None = None
    fin: date | None = None
    holgura_dias: int = 0
    critica: bool = False
    costo_mano_obra: Decimal = Decimal("0")
    costo_materiales: Decimal = Decimal("0")


@dataclass(frozen=True)
class Oficio:
    clave: str
    nombre: str
    cuadrillas: int
    subcontrato: bool
    personas_por_cuadrilla: int
    pasos: int
    dias_trabajo: int
    en_ruta_critica: bool


@dataclass(frozen=True)
class Sugerencia:
    oficio: str
    nombre: str
    dias_menos: int
    costo_extra: Decimal  # diferencia en jornales


@dataclass
class Propuesta:
    pasos: list[Paso]
    fases: list[str]  # en orden de inicio
    oficios: list[Oficio]
    inicio: date
    fin: date
    costo_mano_obra: Decimal
    costo_materiales: Decimal
    entrega_deseada: date | None
    sugerencias: list[Sugerencia]

    @property
    def dias_calendario(self) -> int:
        return (self.fin - self.inicio).days + 1

    @property
    def dias_de_retraso(self) -> int | None:
        """Positivo: llega después de la fecha deseada; negativo: antes."""
        return None if self.entrega_deseada is None else (self.fin - self.entrega_deseada).days


# --- Calendario ---


def dias_calendario(dias_trabajo: int, dias_semana: int) -> int:
    """Días calendario para cumplir N días de trabajo empezando un día de trabajo (6 por semana: 7 → 8)."""
    dias_semana = min(max(dias_semana, 1), 7)
    return dias_trabajo + (dias_trabajo - 1) // dias_semana * (7 - dias_semana)


# --- Secuencia ---


@dataclass
class _Nodo:
    clave: str
    rubro: str  # clave del catálogo
    piso: str | None
    cantidad: float
    unidad: str
    predecesoras: list[tuple[str, int]]
    nombre: str | None = None
    fierro: float = 0.0  # kg de fierro que lleva este paso


def _secuencia(cantidades: list[CantidadRubro], pisos: list[str], area_terreno: float, f: Formulario) -> list[_Nodo]:
    """Todos los pasos posibles en orden constructivo; los que quedan con cantidad 0 se saltan después."""
    q: dict[tuple[str, str | None], CantidadRubro] = {(c.rubro, c.piso): c for c in cantidades}

    def cant(rubro: str, piso: str | None = None) -> tuple[float, str]:
        c = q.get((rubro, piso))
        return (c.cantidad, c.unidad) if c else (0.0, "")

    nodos: list[_Nodo] = []

    def nodo(clave, rubro, valor, preds, piso=None, nombre=None, fierro=0.0):
        nodos.append(
            _Nodo(
                clave,
                rubro,
                piso,
                valor[0],
                valor[1],
                [(p, 0) if isinstance(p, str) else p for p in preds],
                nombre,
                fierro,
            )
        )

    hormigon = {p: cant("hormigon", p)[0] for p in pisos}
    hormigon_total = sum(hormigon.values()) or 1.0
    fierro_total = cant("fierro")[0]

    nodo("preliminares", "preliminares", (area_terreno, "m²"), [])
    nodo("excavacion", "excavacion", cant("excavacion"), ["preliminares"])
    nodo("zapatas", "zapatas", cant("zapatas"), ["excavacion"], fierro=cant("fierro_zapatas")[0])
    nodo("cimientos", "cimientos", cant("cimientos"), ["excavacion"])
    nodo("sobrecimiento", "sobrecimiento", cant("sobrecimiento"), ["zapatas", "cimientos"])

    for i, piso in enumerate(pisos):
        ultimo = i == len(pisos) - 1
        abajo = ["zapatas", "cimientos"] if i == 0 else [(f"losa:{pisos[i - 1]}", FRAGUADO_DIAS)]
        h = hormigon[piso]
        fierro = fierro_total * h / hormigon_total
        nodo(
            f"columnas:{piso}",
            "columnas",
            (h * FRACCION_COLUMNAS, "m³"),
            abajo,
            piso,
            fierro=fierro * FRACCION_COLUMNAS,
        )
        muros = [f"columnas:{piso}"] + (["sobrecimiento"] if i == 0 else [])
        nodo(f"muros:{piso}", f"muros:{f.tipo_muro}", cant("muros", piso), muros, piso)
        sin_losa = ultimo and f.cubierta != "losa"
        nodo(
            f"losa:{piso}",
            "losa",
            (h * (1 - FRACCION_COLUMNAS), "m³"),
            [f"columnas:{piso}"],
            piso,
            nombre="Vigas de amarre de H°A°" if sin_losa else None,
            fierro=fierro * (1 - FRACCION_COLUMNAS),
        )
        nodo(f"electrica:{piso}", "electrica", cant("electrica", piso), [f"muros:{piso}"], piso)
        nodo(
            f"revoque_interior:{piso}",
            "revoque_interior",
            cant("revoque_interior", piso),
            [f"electrica:{piso}", "sanitaria", f"losa:{piso}"],
            piso,
        )
        nodo(
            f"revoque_exterior:{piso}",
            "revoque_exterior",
            cant("revoque_exterior", piso),
            [f"muros:{piso}", f"losa:{piso}"],
            piso,
        )
        nodo(f"cielo_raso:{piso}", "cielo_raso", cant("cielo_raso", piso), [f"losa:{piso}", f"electrica:{piso}"], piso)
        if i == 0:
            nodo(f"contrapiso:{piso}", "contrapiso", cant("contrapiso", piso), [f"revoque_interior:{piso}"], piso)
        nodo(
            f"piso:{piso}",
            f"piso:{f.piso}",
            cant("piso", piso),
            [f"revoque_interior:{piso}"] + ([f"contrapiso:{piso}"] if i == 0 else []),
            piso,
        )
        nodo(f"puertas:{piso}", "puertas", cant("puertas", piso), [f"revoque_interior:{piso}"], piso)
        nodo(
            f"ventanas:{piso}",
            "ventanas",
            cant("ventanas", piso),
            [f"revoque_exterior:{piso}", f"revoque_interior:{piso}"],
            piso,
        )
        nodo(
            f"pintura:{piso}",
            "pintura",
            cant("pintura", piso),
            [f"revoque_interior:{piso}", f"revoque_exterior:{piso}", f"cielo_raso:{piso}"],
            piso,
        )

    nodo("sanitaria", "sanitaria", cant("sanitaria"), [f"muros:{p}" for p in pisos])
    arriba = pisos[-1]
    techo = [f"losa:{arriba}"] if f.cubierta == "losa" else [f"muros:{arriba}", f"losa:{arriba}"]
    nodo("cubierta", f"cubierta:{f.cubierta}", cant("cubierta"), techo)
    finales = [f"{r}:{p}" for p in pisos for r in ("pintura", "piso", "puertas", "ventanas")]
    nodo("entrega", "entrega", (0.0, ""), finales + ["cubierta"])
    return nodos


def _presentes(nodos: list[_Nodo]) -> list[_Nodo]:
    """Quita los pasos sin cantidad; sus sucesoras heredan sus predecesoras (sumando las esperas)."""
    por_clave = {n.clave: n for n in nodos}

    def existe(n: _Nodo) -> bool:
        return n.cantidad > 0 or CATALOGO[n.rubro].dias_fijos is not None

    def efectivas(clave: str, desfase: int, vistos: frozenset[str]) -> list[tuple[str, int]]:
        n = por_clave.get(clave)
        if n is None or clave in vistos:
            return []
        if existe(n):
            return [(clave, desfase)]
        return [e for p, d in n.predecesoras for e in efectivas(p, desfase + d, vistos | {clave})]

    salida = []
    for n in nodos:
        if not existe(n):
            continue
        mejores: dict[str, int] = {}
        for p, d in n.predecesoras:
            for clave, desfase in efectivas(p, d, frozenset({n.clave})):
                mejores[clave] = max(mejores.get(clave, desfase), desfase)
        salida.append(replace(n, predecesoras=list(mejores.items())))
    return salida


# --- Pasos con duración y recursos ---


def _fase(rubro: Rubro, nodo: _Nodo, varios_pisos: bool) -> str:
    if rubro.fase == "Obra gruesa" and nodo.piso and varios_pisos:
        return f"Obra gruesa · {nodo.piso}"
    return rubro.fase


def _paso(nodo: _Nodo, f: Formulario, e: Ejecucion, varios_pisos: bool) -> Paso:
    rubro = CATALOGO[nodo.rubro]
    cuadrillas = e.cuadrillas_de(rubro.oficio)
    if rubro.dias_fijos is not None:
        trabajo = rubro.dias_fijos
    else:
        trabajo = max(1, math.ceil(nodo.cantidad / (rubro.rendimiento * cuadrillas) - 1e-9))
    recursos = [Recurso("mano_obra", cargo, "", n * cuadrillas, JORNALES[cargo], True) for cargo, n in rubro.cuadrilla]
    factor = FACTOR_ACABADO.get(f.acabado, 1.0)
    for c in rubro.consumos:
        precio = round(c.precio * (factor if c.acabado else 1.0), 2)
        recursos.append(
            Recurso("material", c.material, c.unidad, round(nodo.cantidad * c.por_unidad, 2), precio, False)
        )
    if nodo.fierro > 0:
        recursos.append(
            Recurso("material", FIERRO.material, FIERRO.unidad, round(nodo.fierro, 2), FIERRO.precio, False)
        )
    nombre = nodo.nombre or rubro.actividad
    if nodo.piso and varios_pisos:
        nombre = f"{nombre} · {nodo.piso}"
    return Paso(
        clave=nodo.clave,
        nombre=nombre,
        fase=_fase(rubro, nodo, varios_pisos),
        oficio=rubro.oficio,
        cantidad=None if rubro.dias_fijos is not None else round(nodo.cantidad, 2),
        unidad=nodo.unidad,
        dias_trabajo=trabajo,
        duracion_dias=dias_calendario(trabajo, e.dias_semana),
        personas=rubro.personas * cuadrillas,
        recursos=recursos,
        predecesoras=[EnlacePaso(p, d, "tecnica") for p, d in nodo.predecesoras],
    )


def _fechas(pasos: list[Paso], inicio: date) -> tuple[dict[str, cr.Fechas], dict[str, cr.Holgura]]:
    indice = {p.clave: i for i, p in enumerate(pasos)}
    datos = [
        cr.DatosActividad(
            indice[p.clave],
            p.duracion_dias,
            None,
            tuple(cr.Enlace(indice[e.predecesora], e.desfase_dias) for e in p.predecesoras),
        )
        for p in pasos
    ]
    fechas = cr.calcular_fechas(datos, inicio)
    holguras = cr.calcular_holguras(datos, fechas)
    return (
        {p.clave: fechas[indice[p.clave]] for p in pasos},
        {p.clave: holguras[indice[p.clave]] for p in pasos},
    )


def _nivelar(pasos: list[Paso], e: Ejecucion) -> tuple[dict[str, cr.Fechas], dict[str, cr.Holgura]]:
    """Mientras dos pasos del mismo oficio se crucen, uno espera al otro (ver `_primer_cruce`)."""
    orden = {p.clave: i for i, p in enumerate(pasos)}
    por_clave = {p.clave: p for p in pasos}
    for _ in range(MAX_NIVELACIONES):
        fechas, holguras = _fechas(pasos, e.fecha_inicio)
        cruce = _primer_cruce(pasos, fechas, holguras, orden, e)
        if cruce is None:
            _quitar_redundantes(pasos)
            return fechas, holguras
        primero, segundo = cruce
        por_clave[segundo].predecesoras.append(EnlacePaso(primero, 0, "cuadrilla"))
    _quitar_redundantes(pasos)
    return _fechas(pasos, e.fecha_inicio)


def _quitar_redundantes(pasos: list[Paso]) -> None:
    """Quita A → C si C ya depende de A a través de otra predecesora.

    Las técnicas solo se simplifican entre técnicas: si después se borra un enlace por cuadrilla (porque se
    sumó gente), la secuencia constructiva sigue completa. Los enlaces con espera (fraguado) se dejan, porque
    el directo puede ser el que manda.
    """
    por_clave = {p.clave: p for p in pasos}

    def ancestros(solo_tecnicas: bool) -> dict[str, set[str]]:
        memo: dict[str, set[str]] = {}

        def de(clave: str) -> set[str]:
            if clave not in memo:
                memo[clave] = set()
                for e in por_clave[clave].predecesoras:
                    if not solo_tecnicas or e.origen == "tecnica":
                        memo[clave] |= {e.predecesora} | de(e.predecesora)
            return memo[clave]

        for p in pasos:
            de(p.clave)
        return memo

    tecnicas, todas = ancestros(True), ancestros(False)
    for p in pasos:
        quedan = []
        for e in p.predecesoras:
            otras = [o for o in p.predecesoras if o is not e]
            if e.origen == "tecnica":
                implicita = any(e.predecesora in tecnicas[o.predecesora] for o in otras if o.origen == "tecnica")
            else:
                implicita = any(e.predecesora == o.predecesora or e.predecesora in todas[o.predecesora] for o in otras)
            if e.desfase_dias > 0 or not implicita:
                quedan.append(e)
        p.predecesoras = quedan


def _primer_cruce(pasos, fechas, holguras, orden, e: Ejecucion) -> tuple[str, str] | None:
    por_oficio: dict[str, list[Paso]] = defaultdict(list)
    for p in pasos:
        if p.oficio not in e.subcontratos:
            por_oficio[p.oficio].append(p)
    cruces = []
    for lista in por_oficio.values():
        lista.sort(key=lambda p: (fechas[p.clave].inicio, orden[p.clave]))
        for i, a in enumerate(lista):
            for b in lista[i + 1 :]:
                if fechas[b.clave].inicio > fechas[a.clave].fin:
                    break
                # Se cruzan: va primero el que puede empezar antes; si empiezan juntos, el de menor holgura.
                clave = lambda p: (fechas[p.clave].inicio, holguras[p.clave].dias, orden[p.clave])  # noqa: E731
                primero, segundo = sorted((a, b), key=clave)
                cruces.append((fechas[a.clave].inicio, orden[a.clave], primero.clave, segundo.clave))
                break
    if not cruces:
        return None
    _, _, primero, segundo = min(cruces)
    return primero, segundo


def _programar(cantidades, pisos, area_terreno, f: Formulario, e: Ejecucion) -> Propuesta:
    nodos = _presentes(_secuencia(cantidades, pisos, area_terreno, f))
    varios = len(pisos) > 1
    pasos = [_paso(n, f, e, varios) for n in nodos]
    _quitar_redundantes(pasos)
    fechas, holguras = _nivelar(pasos, e)
    mano_obra = materiales = Decimal("0")
    for p in pasos:
        p.inicio, p.fin = fechas[p.clave].inicio, fechas[p.clave].fin
        p.holgura_dias, p.critica = holguras[p.clave].dias, holguras[p.clave].critica
        costo = costos.costo_actividad(
            (
                costos.DatosRecurso(r.tipo, Decimal(str(r.cantidad)), Decimal(str(r.precio_unitario)), r.por_dia)
                for r in p.recursos
            ),
            p.duracion_dias,
        )
        p.costo_mano_obra, p.costo_materiales = costo.mano_obra, costo.materiales
        mano_obra += costo.mano_obra
        materiales += costo.materiales

    # Fases en el orden en que empiezan; si empiezan el mismo día, en el orden de la secuencia.
    inicio_fase: dict[str, date] = {}
    primera: dict[str, int] = {}
    for i, p in enumerate(pasos):
        primera.setdefault(p.fase, i)
        inicio_fase[p.fase] = min(inicio_fase.get(p.fase, p.inicio), p.inicio)
    fases = sorted(inicio_fase, key=lambda nombre: (inicio_fase[nombre], primera[nombre]))

    oficios = []
    for clave, nombre in OFICIOS.items():
        suyos = [p for p in pasos if p.oficio == clave]
        if not suyos:
            continue
        oficios.append(
            Oficio(
                clave=clave,
                nombre=nombre,
                cuadrillas=e.cuadrillas_de(clave),
                subcontrato=clave in e.subcontratos,
                personas_por_cuadrilla=max(
                    CATALOGO[n.rubro].personas for n in nodos if CATALOGO[n.rubro].oficio == clave
                ),
                pasos=len(suyos),
                dias_trabajo=sum(p.dias_trabajo for p in suyos),
                en_ruta_critica=any(p.critica for p in suyos),
            )
        )
    return Propuesta(
        pasos=pasos,
        fases=fases,
        oficios=oficios,
        inicio=min(p.inicio for p in pasos),
        fin=max(p.fin for p in pasos),
        costo_mano_obra=mano_obra,
        costo_materiales=materiales,
        entrega_deseada=e.entrega_deseada,
        sugerencias=[],
    )


def proponer(
    cantidades: list[CantidadRubro],
    pisos: list[str],
    area_terreno: float,
    formulario: Formulario,
    ejecucion: Ejecucion,
) -> Propuesta:
    """Propuesta completa, con la sugerencia de qué cuadrilla sumar para terminar antes."""
    if not pisos:
        raise ValueError("Hace falta al menos un piso")
    base = _programar(cantidades, pisos, area_terreno, formulario, ejecucion)
    sugerencias = []
    for oficio in base.oficios:
        if not oficio.en_ruta_critica or oficio.subcontrato or oficio.clave == "limpieza":
            continue
        cuadrillas = {**ejecucion.cuadrillas, oficio.clave: oficio.cuadrillas + 1}
        otra = _programar(cantidades, pisos, area_terreno, formulario, replace(ejecucion, cuadrillas=cuadrillas))
        menos = (base.fin - otra.fin).days
        if menos > 0:
            sugerencias.append(
                Sugerencia(oficio.clave, oficio.nombre, menos, otra.costo_mano_obra - base.costo_mano_obra)
            )
    base.sugerencias = sorted(sugerencias, key=lambda s: (-s.dias_menos, s.costo_extra))
    return base
