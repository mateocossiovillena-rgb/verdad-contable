"""Une la base de datos con los cálculos del Kit TCM: estimado con APU, clase, base del estimado y línea base."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import servicios
from app.calculos import costos
from app.calculos import cronograma as cr
from app.modelos import (
    Actividad,
    BaseEstimado,
    ClasificacionEstimado,
    Dependencia,
    Fase,
    LineaBase,
    LineaBasePartida,
    Obra,
    ParametrosApu,
    RecursoActividad,
    Usuario,
)
from app.tcm import clasificacion as cl
from app.tcm import linea_base as lb
from app.tcm.plantilla import PARAMETROS, ObraLeida

CERO = Decimal("0")

# Campos de texto de la Base del estimado (34R-05), en el orden en que se muestran y exportan.
CAMPOS_BASE = {
    "proposito": "Propósito del estimado",
    "alcance": "Alcance",
    "metodologia": "Metodología",
    "base_diseno": "Base de diseño (documentos usados)",
    "base_planificacion": "Base de planificación (cómo se ejecutará)",
    "fuentes_precios": "Fuentes de precios",
    "supuestos": "Supuestos",
    "exclusiones": "Exclusiones",
    "riesgos_oportunidades": "Riesgos y oportunidades",
    "contingencia_nota": "Contingencia: criterio",
}


# --- Estimado (WBS → actividades → APU) ---


@dataclass
class ActividadEstimada:
    actividad: Actividad
    recursos: list[RecursoActividad]
    apu: costos.Apu
    precio_unitario: Decimal | None


@dataclass
class FaseEstimada:
    fase: Fase
    actividades: list[ActividadEstimada] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((a.apu.total for a in self.actividades), CERO)


@dataclass
class Estimado:
    parametros: costos.ParametrosApu
    fases: list[FaseEstimada]

    @property
    def actividades(self) -> list[ActividadEstimada]:
        return [a for f in self.fases for a in f.actividades]

    def suma(self, campo: str) -> Decimal:
        return sum((getattr(a.apu, campo) for a in self.actividades), CERO)

    @property
    def total(self) -> Decimal:
        return self.suma("total")


def estimado(sesion: Session, obra: Obra) -> Estimado:
    parametros = servicios.parametros_apu(sesion, obra.id)
    fases = list(sesion.scalars(select(Fase).where(Fase.obra_id == obra.id).order_by(Fase.orden, Fase.id)))
    por_fase = {f.id: FaseEstimada(f) for f in fases}
    actividades = sorted(servicios.actividades_de_obra(sesion, obra.id), key=lambda a: (a.orden, a.id))
    recursos: dict[int, list[RecursoActividad]] = defaultdict(list)
    for r in sesion.scalars(
        select(RecursoActividad)
        .join(Actividad)
        .where(Actividad.obra_id == obra.id)
        .order_by(RecursoActividad.orden, RecursoActividad.id)
    ):
        recursos[r.actividad_id].append(r)
    for a in actividades:
        costo = costos.costo_actividad([servicios.datos_recurso(r) for r in recursos[a.id]], a.duracion_dias)
        apu = costos.calcular_apu(costo, parametros)
        por_fase[a.fase_id].actividades.append(
            ActividadEstimada(a, recursos[a.id], apu, costos.precio_unitario(apu, a.computo))
        )
    return Estimado(parametros=parametros, fases=list(por_fase.values()))


# --- Clasificación ---


def checklist(sesion: Session, obra_id: int) -> dict[str, str]:
    fila = sesion.get(ClasificacionEstimado, obra_id)
    return dict(fila.entregables) if fila else {}


def guardar_checklist(sesion: Session, obra_id: int, entregables: dict[str, str]) -> None:
    t = cl.tabla()
    validas = {e.clave for e in t.entregables}
    desconocidas = set(entregables) - validas
    if desconocidas:
        raise HTTPException(422, f"Entregables desconocidos: {', '.join(sorted(desconocidas))}")
    if any(v not in cl.ESTADOS for v in entregables.values()):
        raise HTTPException(422, "Cada entregable debe estar en: no, parcial o completo")
    fila = sesion.get(ClasificacionEstimado, obra_id)
    if fila is None:
        fila = ClasificacionEstimado(obra_id=obra_id, entregables={})
        sesion.add(fila)
    fila.entregables = {**fila.entregables, **entregables}


def clasificar(sesion: Session, obra: Obra, total: Decimal | None = None) -> cl.Resultado:
    if total is None:
        total = estimado(sesion, obra).total
    return cl.clasificar(checklist(sesion, obra.id), cl.tabla(), total)


# --- Base del estimado ---


def base_del_estimado(sesion: Session, obra_id: int) -> BaseEstimado:
    """La de la obra, o una vacía (sin guardar) si todavía no tiene."""
    fila = sesion.get(BaseEstimado, obra_id)
    if fila is None:
        fila = BaseEstimado(obra_id=obra_id, contingencia_porcentaje=CERO, fecha_precios=None)
        for campo in CAMPOS_BASE:
            setattr(fila, campo, "")
    return fila


# --- Línea base ---


def lineas_base(sesion: Session, obra_id: int) -> list[LineaBase]:
    return list(
        sesion.scalars(select(LineaBase).where(LineaBase.obra_id == obra_id).order_by(LineaBase.version.desc()))
    )


def aprobar_linea_base(sesion: Session, obra: Obra, usuario: Usuario, motivo: str) -> LineaBase:
    """Congela presupuesto y fechas de todas las partidas como una versión nueva; la anterior deja de valer."""
    servicios.recalcular_cronograma(sesion, obra)
    partidas = servicios.partidas_de_obra(sesion, obra.id)
    bac = sum((p.presupuesto for p in partidas), CERO)
    if bac <= 0:
        raise HTTPException(422, "La obra no tiene presupuesto: carga el estimado antes de aprobar la línea base.")
    anterior = servicios.linea_base_vigente(sesion, obra.id)
    if anterior is not None:
        anterior.vigente = False
        sesion.flush()
    version = (sesion.scalar(select(func.max(LineaBase.version)).where(LineaBase.obra_id == obra.id)) or 0) + 1
    nueva = LineaBase(
        obra_id=obra.id,
        version=version,
        aprobada_por=usuario.id,
        motivo=motivo.strip(),
        bac=bac,
        fecha_inicio=obra.fecha_inicio,
        fecha_fin=obra.fecha_fin,
        clase=clasificar(sesion, obra).clase.clase,
        vigente=True,
        partidas=[
            LineaBasePartida(
                partida_id=p.id,
                codigo=p.codigo,
                nombre=p.nombre,
                fase=p.fase,
                # Los gastos generales sin fechas propias corren durante toda la obra.
                fecha_inicio=p.fecha_inicio or (obra.fecha_inicio if p.es_generales else None),
                fecha_fin=p.fecha_fin or (obra.fecha_fin if p.es_generales else None),
                presupuesto=p.presupuesto,
                orden=p.orden,
            )
            for p in partidas
        ],
    )
    sesion.add(nueva)
    sesion.flush()
    return nueva


def pv_semanal(base: LineaBase) -> list[lb.Semana]:
    return lb.pv_semanal(
        [lb.PartidaPlan(p.presupuesto, p.fecha_inicio, p.fecha_fin) for p in base.partidas], base.fecha_inicio
    )


# --- Importar desde la plantilla Excel ---


def crear_obra_desde_plantilla(sesion: Session, dueno: Usuario, d: ObraLeida) -> Obra:
    """Crea la obra completa (estimado, clasificación, base del estimado y cronograma) desde una lectura válida."""
    obra = Obra(
        dueno_id=dueno.id,
        nombre=d.nombre,
        cliente=d.cliente,
        ubicacion=d.ubicacion,
        fecha_inicio=d.fecha_inicio,
        fecha_fin=d.fecha_inicio,
        moneda=d.moneda,
    )
    sesion.add(obra)
    sesion.flush()
    servicios.partida_generales(sesion, obra)
    sesion.add(ParametrosApu(obra_id=obra.id, **{k: d.parametros.get(k, CERO) for k in PARAMETROS}))
    sesion.add(ClasificacionEstimado(obra_id=obra.id, entregables=dict(d.clasificacion)))
    base = BaseEstimado(
        obra_id=obra.id,
        fecha_precios=d.fecha_precios,
        contingencia_porcentaje=d.contingencia_porcentaje,
        **{c: d.base.get(c, "") for c in CAMPOS_BASE},
    )
    sesion.add(base)

    fases: dict[str, Fase] = {}
    for a in d.actividades:
        if a.fase not in fases:
            fases[a.fase] = Fase(obra_id=obra.id, nombre=a.fase[:120], orden=len(fases) + 1)
            sesion.add(fases[a.fase])
    sesion.flush()

    insumos: dict[str, list] = defaultdict(list)
    for r in d.insumos:
        insumos[r.codigo_actividad].append(r)
    actividades: dict[str, Actividad] = {}
    orden_en_fase: dict[str, int] = defaultdict(int)
    for a in d.actividades:
        orden_en_fase[a.fase] += 1
        dias = cr.a_dias(a.duracion, a.unidad_duracion)
        inicio = a.inicio or obra.fecha_inicio
        actividad = Actividad(
            obra_id=obra.id,
            fase_id=fases[a.fase].id,
            codigo=a.codigo,
            nombre=a.nombre,
            unidad=a.unidad,
            computo=a.computo,
            duracion_dias=dias,
            duracion_cantidad=a.duracion,
            unidad_duracion=a.unidad_duracion,
            inicio_manual=None if a.predecesoras else a.inicio,
            fecha_inicio=inicio,
            fecha_fin=cr.fin_de(inicio, dias),
            orden=orden_en_fase[a.fase],
            recursos=[
                RecursoActividad(
                    tipo=r.tipo,
                    descripcion=r.descripcion,
                    unidad=r.unidad,
                    rendimiento=r.rendimiento,
                    cantidad=(r.rendimiento * a.computo).quantize(Decimal("0.001")),
                    precio_unitario=r.precio,
                    por_dia=False,
                    orden=i,
                )
                for i, r in enumerate(insumos[a.codigo])
            ],
        )
        sesion.add(actividad)
        actividades[a.codigo] = actividad
    sesion.flush()
    for a in d.actividades:
        actividades[a.codigo].predecesoras = [
            Dependencia(predecesora_id=actividades[p].id, sucesora_id=actividades[a.codigo].id) for p in a.predecesoras
        ]
    servicios.recalcular_cronograma(sesion, obra)
    return obra
