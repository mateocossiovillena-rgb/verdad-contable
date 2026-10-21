"""Obras, partidas, hitos, indicadores y alertas."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app import servicios
from app.calculos import valor_ganado as vg
from app.db import obtener_sesion
from app.esquemas import (
    AdvertenciaSalida,
    Alerta,
    HitoEntrada,
    HitoSalida,
    IndicadoresObra,
    IndicadoresSalida,
    ObraEntrada,
    ObraResumen,
    ObraSalida,
    PartidaEntrada,
    PartidaIndicadores,
    PartidaSalida,
    PuntoCurvaSalida,
)
from app.modelos import ROL_DUENO, Avance, Gasto, Hito, Obra, Partida, Usuario
from app.seguridad import ids_obras_visibles, obra_propia, obra_visible, solo_dueno, usuario_actual

rutas = APIRouter(prefix="/api", tags=["obras"])


def _f(valor: Decimal | None) -> float | None:
    return None if valor is None else float(vg.redondear_indice(valor))


def _indicadores(i: vg.Indicadores) -> IndicadoresSalida:
    dinero = vg.redondear_dinero
    return IndicadoresSalida(
        bac=dinero(i.bac),
        pv=dinero(i.pv),
        ev=dinero(i.ev),
        ac=dinero(i.ac),
        sv=dinero(i.sv),
        cv=dinero(i.cv),
        spi=_f(i.spi),
        cpi=_f(i.cpi),
        eac=None if i.eac is None else dinero(i.eac),
        avance_planificado=_f(i.avance_planificado),
        avance_real=_f(i.avance_real),
        avance_esperado_por_gasto=_f(i.avance_esperado_por_gasto),
    )


# --- Obras ---


@rutas.get("/obras", response_model=list[ObraResumen])
def listar_obras(usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    ids = ids_obras_visibles(sesion, usuario)
    obras = sesion.scalars(select(Obra).where(Obra.id.in_(ids)).order_by(Obra.fecha_inicio.desc())) if ids else []
    corte = servicios.hoy()
    salida = []
    for obra in obras:
        fila = ObraResumen(
            **ObraSalida.model_validate(obra).model_dump(), gastado_hoy=servicios.gastado_en(sesion, obra.id, corte)
        )
        if usuario.rol == ROL_DUENO:
            _, resultado = servicios.calcular(sesion, obra, corte)
            i = resultado.indicadores
            fila = fila.model_copy(
                update={
                    "presupuesto": i.bac,
                    "gastado": i.ac,
                    "avance_real": _f(i.avance_real),
                    "avance_planificado": _f(i.avance_planificado),
                    "spi": _f(i.spi),
                    "cpi": _f(i.cpi),
                    "semaforo": vg.semaforo(i, obra.umbral_amarillo, obra.umbral_rojo),
                    "alertas": len(servicios.alertas_de_obra(sesion, obra, corte)),
                }
            )
        salida.append(fila)
    return salida


@rutas.post("/obras", response_model=ObraSalida, status_code=status.HTTP_201_CREATED)
def crear_obra(datos: ObraEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    obra = Obra(dueno_id=dueno.id, **datos.model_dump())
    sesion.add(obra)
    sesion.flush()
    servicios.partida_generales(sesion, obra)
    sesion.commit()
    return obra


@rutas.get("/obras/{obra_id}", response_model=ObraSalida)
def ver_obra(obra_id: int, usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    return obra_visible(sesion, usuario, obra_id)


@rutas.put("/obras/{obra_id}", response_model=ObraSalida)
def editar_obra(
    obra_id: int, datos: ObraEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra = obra_propia(sesion, dueno, obra_id)
    for campo, valor in datos.model_dump().items():
        setattr(obra, campo, valor)
    sesion.commit()
    return obra


@rutas.get("/obras/{obra_id}/indicadores", response_model=IndicadoresObra)
def indicadores_obra(
    obra_id: int,
    corte: date | None = None,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    obra = obra_propia(sesion, dueno, obra_id)
    hoy = servicios.hoy()
    corte = corte or hoy
    datos, resultado = servicios.calcular(sesion, obra, corte)
    partidas = []
    for (partida, _), r in zip(datos, resultado.partidas, strict=True):
        partidas.append(
            PartidaIndicadores(
                partida=PartidaSalida.model_validate(partida).model_copy(
                    update={"porcentaje_avance": float(r.porcentaje_avance)}
                ),
                porcentaje_avance=float(r.porcentaje_avance),
                indicadores=_indicadores(r.indicadores),
                semaforo=vg.semaforo(r.indicadores, obra.umbral_amarillo, obra.umbral_rojo),
                advertencias=[AdvertenciaSalida(codigo=a.codigo, mensaje=a.mensaje) for a in r.advertencias],
            )
        )
    curva = vg.calcular_curva([d for _, d in datos], servicios.fechas_curva(obra, corte), hoy=min(corte, hoy))
    return IndicadoresObra(
        obra=ObraSalida.model_validate(obra),
        corte=corte,
        indicadores=_indicadores(resultado.indicadores),
        semaforo=vg.semaforo(resultado.indicadores, obra.umbral_amarillo, obra.umbral_rojo),
        frases=vg.frases_resumen(resultado.indicadores),
        advertencias=[AdvertenciaSalida(codigo=a.codigo, mensaje=a.mensaje) for a in resultado.advertencias],
        partidas=partidas,
        curva=[
            PuntoCurvaSalida(
                fecha=p.fecha,
                pv=vg.redondear_dinero(p.pv),
                ev=None if p.ev is None else vg.redondear_dinero(p.ev),
                ac=None if p.ac is None else vg.redondear_dinero(p.ac),
            )
            for p in curva
        ],
        hitos=[HitoSalida.model_validate(h) for h in servicios.hitos_de_obra(sesion, obra.id)],
    )


@rutas.get("/alertas", response_model=list[Alerta])
def alertas(dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    corte = servicios.hoy()
    salida = []
    for obra in sesion.scalars(select(Obra).where(Obra.dueno_id == dueno.id).order_by(Obra.nombre)):
        salida.extend(servicios.alertas_de_obra(sesion, obra, corte))
    salida.sort(key=lambda a: a["nivel"] != "rojo")
    return salida


# --- Partidas ---


@rutas.get("/obras/{obra_id}/partidas", response_model=list[PartidaSalida])
def listar_partidas(
    obra_id: int, usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)
):
    obra_visible(sesion, usuario, obra_id)
    avances = servicios.avance_actual_por_partida(sesion, obra_id, servicios.hoy())
    salida = []
    for p in servicios.partidas_de_obra(sesion, obra_id):
        fila = PartidaSalida.model_validate(p).model_copy(update={"porcentaje_avance": float(avances.get(p.id, 0))})
        if usuario.rol != ROL_DUENO:
            fila = fila.model_copy(update={"presupuesto": Decimal("0")})
        salida.append(fila)
    return salida


@rutas.post("/obras/{obra_id}/partidas", response_model=PartidaSalida, status_code=status.HTTP_201_CREATED)
def crear_partida(
    obra_id: int, datos: PartidaEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra_propia(sesion, dueno, obra_id)
    valores = datos.model_dump()
    if valores["orden"] is None:
        valores["orden"] = (sesion.scalar(select(func.max(Partida.orden)).where(Partida.obra_id == obra_id)) or 0) + 1
    partida = Partida(obra_id=obra_id, **valores)
    sesion.add(partida)
    sesion.commit()
    return partida


def _partida_propia(sesion: Session, dueno: Usuario, partida_id: int) -> Partida:
    partida = sesion.get(Partida, partida_id)
    if partida is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partida no encontrada")
    obra_propia(sesion, dueno, partida.obra_id)
    return partida


@rutas.put("/partidas/{partida_id}", response_model=PartidaSalida)
def editar_partida(
    partida_id: int,
    datos: PartidaEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    partida = _partida_propia(sesion, dueno, partida_id)
    for campo, valor in datos.model_dump(exclude_none=True).items():
        setattr(partida, campo, valor)
    if datos.fecha_inicio is None:
        partida.fecha_inicio = None
    if datos.fecha_fin is None:
        partida.fecha_fin = None
    sesion.commit()
    return partida


@rutas.delete("/partidas/{partida_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_partida(partida_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    partida = _partida_propia(sesion, dueno, partida_id)
    if partida.es_generales:
        raise HTTPException(status.HTTP_409_CONFLICT, "La partida de gastos generales no se puede borrar")
    tiene_registros = sesion.scalar(select(exists().where(Gasto.partida_id == partida.id))) or sesion.scalar(
        select(exists().where(Avance.partida_id == partida.id))
    )
    if tiene_registros:
        raise HTTPException(status.HTTP_409_CONFLICT, "La partida ya tiene gastos o avances; no se puede borrar")
    sesion.delete(partida)
    sesion.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Hitos ---


@rutas.get("/obras/{obra_id}/hitos", response_model=list[HitoSalida])
def listar_hitos(obra_id: int, usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    obra_visible(sesion, usuario, obra_id)
    return servicios.hitos_de_obra(sesion, obra_id)


@rutas.post("/obras/{obra_id}/hitos", response_model=HitoSalida, status_code=status.HTTP_201_CREATED)
def crear_hito(
    obra_id: int, datos: HitoEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra_propia(sesion, dueno, obra_id)
    hito = Hito(obra_id=obra_id, **datos.model_dump())
    sesion.add(hito)
    sesion.commit()
    return hito


def _hito_propio(sesion: Session, dueno: Usuario, hito_id: int) -> Hito:
    hito = sesion.get(Hito, hito_id)
    if hito is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hito no encontrado")
    obra_propia(sesion, dueno, hito.obra_id)
    return hito


@rutas.put("/hitos/{hito_id}", response_model=HitoSalida)
def editar_hito(
    hito_id: int, datos: HitoEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    hito = _hito_propio(sesion, dueno, hito_id)
    for campo, valor in datos.model_dump().items():
        setattr(hito, campo, valor)
    sesion.commit()
    return hito


@rutas.delete("/hitos/{hito_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_hito(hito_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    sesion.delete(_hito_propio(sesion, dueno, hito_id))
    sesion.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
