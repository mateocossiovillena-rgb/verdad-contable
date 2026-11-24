"""Lógica que une la base de datos con los cálculos."""

from __future__ import annotations

import base64
import binascii
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.calculos import costos
from app.calculos import cronograma as cr
from app.calculos import valor_ganado as vg
from app.modelos import (
    Actividad,
    Avance,
    CierreDia,
    Dependencia,
    Fase,
    Gasto,
    Hito,
    LineaBase,
    LineaBasePartida,
    Obra,
    ParametrosApu,
    Partida,
    RecursoActividad,
    Usuario,
)

NOMBRE_GENERALES = "Gastos generales"
_FIRMAS_IMAGEN = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png", b"RIFF": ".webp"}


def hoy() -> date:
    return datetime.now(timezone(timedelta(hours=config.HORAS_ZONA_HORARIA))).date()


# --- Fotos ---


def guardar_foto(contenido_base64: str | None) -> str | None:
    """Guarda una foto enviada en base64 (o data URL) y devuelve su nombre de archivo."""
    if not contenido_base64:
        return None
    if contenido_base64.startswith("data:"):
        contenido_base64 = contenido_base64.split(",", 1)[-1]
    try:
        datos = base64.b64decode(contenido_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "La foto no es válida") from None
    if len(datos) > config.TAMANO_MAX_FOTO:
        raise HTTPException(413, "La foto es demasiado grande")
    extension = next((ext for firma, ext in _FIRMAS_IMAGEN.items() if datos.startswith(firma)), None)
    if extension is None:
        raise HTTPException(422, "La foto debe ser JPG, PNG o WEBP")
    config.CARPETA_FOTOS.mkdir(parents=True, exist_ok=True)
    nombre = uuid.uuid4().hex + extension
    (config.CARPETA_FOTOS / nombre).write_bytes(datos)
    return nombre


# --- Partidas ---


def partida_generales(sesion: Session, obra: Obra) -> Partida:
    partida = sesion.scalar(select(Partida).where(Partida.obra_id == obra.id, Partida.es_generales.is_(True)))
    if partida is None:
        partida = Partida(
            obra_id=obra.id, codigo="0", nombre=NOMBRE_GENERALES, presupuesto=Decimal("0"), orden=0, es_generales=True
        )
        sesion.add(partida)
        sesion.flush()
    return partida


def partidas_de_obra(sesion: Session, obra_id: int) -> list[Partida]:
    return list(sesion.scalars(select(Partida).where(Partida.obra_id == obra_id).order_by(Partida.orden, Partida.id)))


def avance_actual_por_partida(sesion: Session, obra_id: int, corte: date) -> dict[int, Decimal]:
    datos = datos_obra(sesion, obra_id)
    return {p.id: vg.avance_a_la_fecha(d.avances, corte) for p, d in datos}


def linea_base_vigente(sesion: Session, obra_id: int) -> LineaBase | None:
    return sesion.scalar(select(LineaBase).where(LineaBase.obra_id == obra_id, LineaBase.vigente.is_(True)))


def datos_obra(sesion: Session, obra_id: int) -> list[tuple[Partida, vg.DatosPartida]]:
    """Partidas de la obra con su historial de avances y gastos (no anulados).

    Si la obra tiene una línea base aprobada, el presupuesto (BAC) y las fechas (PV) salen de ella y no del
    plan editable: así el valor ganado mide contra lo aprobado. Una partida que no estaba en la línea base
    entra con BAC 0 (su gasto sí suma al AC).
    """
    obra = sesion.get(Obra, obra_id)
    partidas = partidas_de_obra(sesion, obra_id)
    base = linea_base_vigente(sesion, obra_id)
    congeladas: dict[int, LineaBasePartida] | None = None
    if base is not None:
        congeladas = {lp.partida_id: lp for lp in base.partidas if lp.partida_id is not None}
    avances: dict[int, list[vg.RegistroAvance]] = defaultdict(list)
    for a in sesion.scalars(
        select(Avance).join(Partida).where(Partida.obra_id == obra_id).order_by(Avance.creado_en, Avance.id)
    ):
        avances[a.partida_id].append(vg.RegistroAvance(a.fecha, a.porcentaje))
    gastos: dict[int, list[vg.RegistroGasto]] = defaultdict(list)
    for g in sesion.scalars(select(Gasto).where(Gasto.obra_id == obra_id, Gasto.anulado.is_(False))):
        gastos[g.partida_id].append(vg.RegistroGasto(g.fecha, g.monto))
    salida = []
    for p in partidas:
        presupuesto, inicio, fin = p.presupuesto, p.fecha_inicio, p.fecha_fin
        if congeladas is not None:
            lp = congeladas.get(p.id)
            presupuesto = lp.presupuesto if lp else Decimal("0")
            if lp:
                inicio, fin = lp.fecha_inicio, lp.fecha_fin
        salida.append(
            (
                p,
                vg.DatosPartida(
                    id=p.id,
                    nombre=p.nombre,
                    presupuesto=presupuesto,
                    # Los gastos generales corren durante toda la obra si no tienen fechas propias.
                    fecha_inicio=inicio or (obra.fecha_inicio if p.es_generales else None),
                    fecha_fin=fin or (obra.fecha_fin if p.es_generales else None),
                    avances=avances[p.id],
                    gastos=gastos[p.id],
                    es_generales=p.es_generales,
                ),
            )
        )
    return salida


def fechas_curva(obra: Obra, corte: date) -> list[date]:
    """Un punto por semana desde el inicio hasta el fin de la obra, más el día de corte."""
    fin = max(obra.fecha_fin, corte)
    fechas = set()
    f = obra.fecha_inicio
    while f < fin:
        fechas.add(f)
        f += timedelta(days=7)
    fechas.update({fin, corte, obra.fecha_fin})
    return sorted(x for x in fechas if x >= obra.fecha_inicio)


# --- Días y cierres ---


def gastado_hasta(sesion: Session, obra_id: int, fecha: date) -> Decimal:
    total = sesion.scalar(
        select(func.coalesce(func.sum(Gasto.monto), 0)).where(
            Gasto.obra_id == obra_id, Gasto.anulado.is_(False), Gasto.fecha <= fecha
        )
    )
    return Decimal(str(total))


def gastado_en(sesion: Session, obra_id: int, fecha: date) -> Decimal:
    total = sesion.scalar(
        select(func.coalesce(func.sum(Gasto.monto), 0)).where(
            Gasto.obra_id == obra_id, Gasto.anulado.is_(False), Gasto.fecha == fecha
        )
    )
    return Decimal(str(total))


def cierre_de(sesion: Session, obra_id: int, fecha: date) -> CierreDia | None:
    return sesion.scalar(select(CierreDia).where(CierreDia.obra_id == obra_id, CierreDia.fecha == fecha))


def exigir_dia_abierto(sesion: Session, obra_id: int, fecha: date) -> None:
    if cierre_de(sesion, obra_id, fecha) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El día {fecha.strftime('%d/%m/%Y')} ya está cerrado. Pide al dueño que lo reabra.",
        )


def gastos_con_nombres(sesion: Session, gastos: list[Gasto]) -> list[dict]:
    ids_partida = {g.partida_id for g in gastos}
    nombres_partida = (
        dict(sesion.execute(select(Partida.id, Partida.nombre).where(Partida.id.in_(ids_partida))).all())
        if ids_partida
        else {}
    )
    ids_usuario = {g.usuario_id for g in gastos}
    nombres_usuario = (
        dict(sesion.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids_usuario))).all())
        if ids_usuario
        else {}
    )
    salida = []
    for g in gastos:
        fila = {c.key: getattr(g, c.key) for c in Gasto.__table__.columns}
        fila["partida_nombre"] = nombres_partida.get(g.partida_id, "")
        fila["usuario_nombre"] = nombres_usuario.get(g.usuario_id, "")
        salida.append(fila)
    return salida


# --- Indicadores y alertas ---


def calcular(
    sesion: Session, obra: Obra, corte: date
) -> tuple[list[tuple[Partida, vg.DatosPartida]], vg.ResultadoObra]:
    datos = datos_obra(sesion, obra.id)
    return datos, vg.calcular_obra([d for _, d in datos], corte)


def hitos_de_obra(sesion: Session, obra_id: int) -> list[Hito]:
    return list(sesion.scalars(select(Hito).where(Hito.obra_id == obra_id).order_by(Hito.fecha_prevista)))


def alertas_de_obra(sesion: Session, obra: Obra, corte: date) -> list[dict]:
    _, resultado = calcular(sesion, obra, corte)
    alertas: list[dict] = []

    def agregar(nivel: str, mensaje: str, partida_id: int | None = None) -> None:
        alertas.append(
            {
                "obra_id": obra.id,
                "obra_nombre": obra.nombre,
                "partida_id": partida_id,
                "nivel": nivel,
                "mensaje": mensaje,
            }
        )

    color = vg.semaforo(resultado.indicadores, obra.umbral_amarillo, obra.umbral_rojo)
    if color in ("amarillo", "rojo"):
        agregar(color, " ".join(vg.frases_resumen(resultado.indicadores)))
    for aviso in resultado.advertencias:
        agregar("rojo", aviso.mensaje)
    for r in resultado.partidas:
        color_partida = vg.semaforo(r.indicadores, obra.umbral_amarillo, obra.umbral_rojo)
        if color_partida in ("amarillo", "rojo") and r.datos.presupuesto > 0:
            agregar(color_partida, f"{r.datos.nombre}: {_resumen_partida(r)}", r.datos.id)
        for aviso in r.advertencias:
            agregar("amarillo", f"{r.datos.nombre}: {aviso.mensaje}", r.datos.id)

    ayer = corte - timedelta(days=1)
    if obra.fecha_inicio <= ayer <= obra.fecha_fin and cierre_de(sesion, obra.id, ayer) is None:
        agregar("amarillo", f"No se cerró el día {ayer.strftime('%d/%m/%Y')}.")
    return alertas


def _resumen_partida(r: vg.ResultadoPartida) -> str:
    i = r.indicadores
    partes = []
    if i.spi is not None and i.spi < 1:
        partes.append("va atrasada")
    if i.cpi is not None and i.cpi < 1:
        partes.append("gasta más de lo que avanza")
    return " y ".join(partes) or "fuera de rango"


# --- Cronograma ---


def actividades_de_obra(sesion: Session, obra_id: int) -> list[Actividad]:
    return list(sesion.scalars(select(Actividad).where(Actividad.obra_id == obra_id).order_by(Actividad.id)))


def predecesoras_por_actividad(sesion: Session, obra_id: int) -> dict[int, list[Dependencia]]:
    enlaces: dict[int, list[Dependencia]] = defaultdict(list)
    for d in sesion.scalars(
        select(Dependencia).join(Actividad, Dependencia.sucesora_id == Actividad.id).where(Actividad.obra_id == obra_id)
    ):
        enlaces[d.sucesora_id].append(d)
    return enlaces


def datos_cronograma(
    actividades: list[Actividad], enlaces: dict[int, list[tuple[int, int]]]
) -> list[cr.DatosActividad]:
    return [
        cr.DatosActividad(
            id=a.id,
            duracion_dias=a.duracion_dias,
            inicio_manual=a.inicio_manual,
            predecesoras=tuple(cr.Enlace(p, desfase) for p, desfase in enlaces.get(a.id, [])),
        )
        for a in actividades
    ]


def recalcular_cronograma(sesion: Session, obra: Obra) -> None:
    """Recalcula las fechas de todas las actividades y el fin de la obra, y sus partidas. Hace flush antes."""
    sesion.flush()
    actividades = actividades_de_obra(sesion, obra.id)
    if actividades:
        _recalcular_fechas(obra, actividades, sesion)
    sincronizar_partidas(sesion, obra, actividades)


def _recalcular_fechas(obra: Obra, actividades: list[Actividad], sesion: Session) -> None:
    enlaces = {
        sucesora: [(d.predecesora_id, d.desfase_dias) for d in deps]
        for sucesora, deps in predecesoras_por_actividad(sesion, obra.id).items()
    }
    fechas = cr.calcular_fechas(datos_cronograma(actividades, enlaces), obra.fecha_inicio)
    for a in actividades:
        a.fecha_inicio = fechas[a.id].inicio
        a.fecha_fin = fechas[a.id].fin
    obra.fecha_fin = max([obra.fecha_inicio] + [f.fin for f in fechas.values()])


def parametros_apu(sesion: Session, obra_id: int) -> costos.ParametrosApu:
    fila = sesion.get(ParametrosApu, obra_id)
    if fila is None:
        return costos.ParametrosApu()
    return costos.ParametrosApu(
        cargas_sociales=fila.cargas_sociales,
        iva_mano_obra=fila.iva_mano_obra,
        herramientas=fila.herramientas,
        gastos_generales=fila.gastos_generales,
        utilidad=fila.utilidad,
        impuestos=fila.impuestos,
    )


def apu_actividad(a: Actividad, parametros: costos.ParametrosApu) -> costos.Apu:
    return costos.calcular_apu(
        costos.costo_actividad([datos_recurso(r) for r in a.recursos], a.duracion_dias), parametros
    )


def datos_recurso(r: RecursoActividad) -> costos.DatosRecurso:
    return costos.DatosRecurso(tipo=r.tipo, cantidad=r.cantidad, precio_unitario=r.precio_unitario, por_dia=r.por_dia)


def tiene_registros(sesion: Session, partida_id: int) -> bool:
    return bool(
        sesion.scalar(select(func.count()).select_from(Gasto).where(Gasto.partida_id == partida_id))
        or sesion.scalar(select(func.count()).select_from(Avance).where(Avance.partida_id == partida_id))
    )


def sincronizar_partidas(sesion: Session, obra: Obra, actividades: list[Actividad]) -> None:
    """Cada actividad del cronograma tiene su partida, que es donde caen gastos y avances.

    Así "gasté vs. debería" sale del mismo cronograma: la partida toma el nombre, la fase y las fechas de la
    actividad, y como presupuesto su precio según el APU (costo directo + porcentajes de la obra; sin
    porcentajes cargados, es el costo de mano de obra + materiales + equipo). Si la actividad no tiene costos se
    conserva el presupuesto que tenía la partida. Si la actividad se borra, su partida se borra también,
    salvo que ya tenga gastos o avances: entonces queda como partida suelta para no perder el historial.
    """
    fases = sorted(sesion.scalars(select(Fase).where(Fase.obra_id == obra.id)), key=lambda f: (f.orden, f.id))
    numero_fase = {f.id: i for i, f in enumerate(fases, 1)}
    nombre_fase = {f.id: f.nombre for f in fases}
    # populate_existing: la base pone actividad_id en NULL al borrar la actividad; no confiar en la copia en memoria.
    vinculadas = list(
        sesion.scalars(
            select(Partida)
            .where(Partida.obra_id == obra.id, Partida.desde_cronograma.is_(True))
            .execution_options(populate_existing=True)
        )
    )
    por_actividad = {p.actividad_id: p for p in vinculadas if p.actividad_id is not None}
    vigentes = {a.id for a in actividades}

    parametros = parametros_apu(sesion, obra.id)
    numero_en_fase: dict[int, int] = defaultdict(int)
    ordenadas = sorted(actividades, key=lambda a: (numero_fase.get(a.fase_id, 0), a.orden, a.id))
    for orden, a in enumerate(ordenadas, 1):
        partida = por_actividad.get(a.id)
        if partida is None:
            partida = Partida(obra_id=obra.id, desde_cronograma=True, actividad_id=a.id, presupuesto=Decimal("0"))
            sesion.add(partida)
        numero_en_fase[a.fase_id] += 1
        partida.codigo = a.codigo or f"{numero_fase.get(a.fase_id, 0)}.{numero_en_fase[a.fase_id]}"
        partida.nombre = a.nombre
        partida.fase = nombre_fase.get(a.fase_id, "")[:80]
        partida.fecha_inicio = a.fecha_inicio
        partida.fecha_fin = a.fecha_fin
        partida.orden = orden
        costo = apu_actividad(a, parametros).total
        if costo > 0:
            partida.presupuesto = costo

    for partida in vinculadas:
        if partida.actividad_id in vigentes:
            continue
        if tiene_registros(sesion, partida.id):
            partida.desde_cronograma = False
            partida.actividad_id = None
        else:
            sesion.delete(partida)
    sesion.flush()
