"""Estimar desde plano: subir un DXF (CAD) o IFC (BIM) y confirmar paso a paso lo que se leyó.

Los planos son confidenciales: se guardan con nombre aleatorio y nunca se sirven de vuelta.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, planos
from app.db import obtener_sesion
from app.esquemas import (
    CantidadesEntrada,
    CapasEntrada,
    EstimacionResumen,
    EstimacionSalida,
    FormularioEntrada,
    PlantaEntrada,
)
from app.modelos import Estimacion, Usuario
from app.seguridad import obra_propia, solo_dueno

rutas = APIRouter(prefix="/api", tags=["estimaciones"])


def _estimacion_propia(sesion: Session, usuario: Usuario, estimacion_id: int) -> Estimacion:
    estimacion = sesion.get(Estimacion, estimacion_id)
    if estimacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estimación no encontrada")
    obra_propia(sesion, usuario, estimacion.obra_id)
    return estimacion


@rutas.post("/obras/{obra_id}/estimaciones", response_model=EstimacionSalida, status_code=status.HTTP_201_CREATED)
async def subir_plano(
    obra_id: int,
    request: Request,
    nombre: str = Query(min_length=5, max_length=200, description="Nombre del archivo, con su extensión"),
    usuario: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    """El cuerpo es el archivo tal cual (application/octet-stream), sin base64, para planos grandes."""
    obra = obra_propia(sesion, usuario, obra_id)
    planos.tipo_de_archivo(nombre)
    datos = bytearray()
    async for parte in request.stream():
        datos += parte
        if len(datos) > config.TAMANO_MAX_PLANO:
            raise HTTPException(
                413, "El plano pesa más de 25 MB. Borra las capas que no sirven para medir y vuelve a subirlo."
            )
    if not datos:
        raise HTTPException(422, "El archivo está vacío")
    estimacion = await run_in_threadpool(planos.crear, sesion, obra, usuario, nombre, bytes(datos))
    return planos.salida(estimacion)


@rutas.get("/obras/{obra_id}/estimaciones", response_model=list[EstimacionResumen])
def listar_estimaciones(
    obra_id: int, usuario: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra_propia(sesion, usuario, obra_id)
    return sesion.scalars(
        select(Estimacion)
        .where(Estimacion.obra_id == obra_id)
        .order_by(Estimacion.creado_en.desc(), Estimacion.id.desc())
    ).all()


@rutas.get("/estimaciones/{estimacion_id}", response_model=EstimacionSalida)
def ver_estimacion(
    estimacion_id: int, usuario: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    return planos.salida(_estimacion_propia(sesion, usuario, estimacion_id))


@rutas.get("/estimaciones/{estimacion_id}/geometria")
def geometria_estimacion(
    estimacion_id: int, usuario: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    return planos.geometria(_estimacion_propia(sesion, usuario, estimacion_id))


@rutas.put("/estimaciones/{estimacion_id}/capas", response_model=EstimacionSalida)
def confirmar_capas(
    estimacion_id: int,
    datos: CapasEntrada,
    usuario: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    estimacion = _estimacion_propia(sesion, usuario, estimacion_id)
    if estimacion.tipo_archivo != "dxf":
        raise HTTPException(status.HTTP_409_CONFLICT, "Los planos BIM no tienen capas que confirmar.")
    planos.aplicar_capas(sesion, estimacion, usuario, datos.capas, datos.unidades)
    return planos.salida(estimacion)


@rutas.put("/estimaciones/{estimacion_id}/plantas", response_model=EstimacionSalida)
def confirmar_plantas(
    estimacion_id: int,
    datos: list[PlantaEntrada],
    usuario: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    estimacion = _estimacion_propia(sesion, usuario, estimacion_id)
    planos.aplicar_plantas(sesion, estimacion, [p.model_dump() for p in datos])
    return planos.salida(estimacion)


@rutas.put("/estimaciones/{estimacion_id}/formulario", response_model=EstimacionSalida)
def guardar_formulario(
    estimacion_id: int,
    datos: FormularioEntrada,
    usuario: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    estimacion = _estimacion_propia(sesion, usuario, estimacion_id)
    planos.aplicar_formulario(sesion, estimacion, datos.model_dump())
    return planos.salida(estimacion)


@rutas.put("/estimaciones/{estimacion_id}/cantidades", response_model=EstimacionSalida)
def confirmar_cantidades(
    estimacion_id: int,
    datos: CantidadesEntrada,
    usuario: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    estimacion = _estimacion_propia(sesion, usuario, estimacion_id)
    planos.aplicar_cantidades(sesion, estimacion, datos.ediciones, datos.confirmar)
    return planos.salida(estimacion)


@rutas.delete("/estimaciones/{estimacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_estimacion(
    estimacion_id: int, usuario: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    planos.borrar(sesion, _estimacion_propia(sesion, usuario, estimacion_id))
