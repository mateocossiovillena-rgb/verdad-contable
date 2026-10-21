"""Cronograma de la obra: fases, actividades y predecesoras.

Toda operación que cambia algo devuelve el cronograma completo ya recalculado,
así la línea de tiempo del celular se actualiza con una sola petición.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import servicios
from app.calculos import cronograma as cr
from app.db import obtener_sesion
from app.esquemas import (
    ActividadEntrada,
    ActividadSalida,
    Cronograma,
    FaseEntrada,
    FaseSalida,
    ObraSalida,
    OrdenFases,
)
from app.modelos import Actividad, Dependencia, Fase, Obra, Usuario
from app.seguridad import obra_propia, obra_visible, solo_dueno, usuario_actual

rutas = APIRouter(prefix="/api", tags=["cronograma"])


def _cronograma(sesion: Session, obra: Obra) -> Cronograma:
    fases = list(sesion.scalars(select(Fase).where(Fase.obra_id == obra.id).order_by(Fase.orden, Fase.id)))
    enlaces = servicios.predecesoras_por_actividad(sesion, obra.id)
    actividades = sorted(servicios.actividades_de_obra(sesion, obra.id), key=lambda a: (a.orden, a.id))
    por_fase: dict[int, list[ActividadSalida]] = {f.id: [] for f in fases}
    for a in actividades:
        por_fase[a.fase_id].append(
            ActividadSalida(
                id=a.id,
                fase_id=a.fase_id,
                nombre=a.nombre,
                duracion_dias=a.duracion_dias,
                inicio_manual=a.inicio_manual,
                fecha_inicio=a.fecha_inicio,
                fecha_fin=a.fecha_fin,
                orden=a.orden,
                predecesoras=sorted(d.predecesora_id for d in enlaces.get(a.id, [])),
            )
        )
    return Cronograma(
        obra=ObraSalida.model_validate(obra),
        hoy=servicios.hoy(),
        fecha_inicio=min([obra.fecha_inicio] + [a.fecha_inicio for a in actividades]),
        fecha_fin=obra.fecha_fin,
        fases=[FaseSalida(id=f.id, nombre=f.nombre, orden=f.orden, actividades=por_fase[f.id]) for f in fases],
    )


def _guardar(sesion: Session, obra: Obra) -> Cronograma:
    servicios.recalcular_cronograma(sesion, obra)
    sesion.commit()
    return _cronograma(sesion, obra)


@rutas.get("/obras/{obra_id}/cronograma", response_model=Cronograma)
def ver_cronograma(obra_id: int, usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    return _cronograma(sesion, obra_visible(sesion, usuario, obra_id))


# --- Fases ---


def _fase_propia(sesion: Session, dueno: Usuario, fase_id: int) -> tuple[Fase, Obra]:
    fase = sesion.get(Fase, fase_id)
    if fase is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fase no encontrada")
    return fase, obra_propia(sesion, dueno, fase.obra_id)


@rutas.post("/obras/{obra_id}/fases", response_model=Cronograma, status_code=status.HTTP_201_CREATED)
def crear_fase(
    obra_id: int, datos: FaseEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra = obra_propia(sesion, dueno, obra_id)
    orden = (sesion.scalar(select(func.max(Fase.orden)).where(Fase.obra_id == obra_id)) or 0) + 1
    sesion.add(Fase(obra_id=obra_id, nombre=datos.nombre.strip(), orden=orden))
    return _guardar(sesion, obra)


@rutas.put("/fases/{fase_id}", response_model=Cronograma)
def editar_fase(
    fase_id: int, datos: FaseEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    fase, obra = _fase_propia(sesion, dueno, fase_id)
    fase.nombre = datos.nombre.strip()
    return _guardar(sesion, obra)


@rutas.delete("/fases/{fase_id}", response_model=Cronograma)
def borrar_fase(fase_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    """Borra la fase con sus actividades; las que dependían de ellas pierden ese enlace."""
    fase, obra = _fase_propia(sesion, dueno, fase_id)
    sesion.delete(fase)
    sesion.flush()
    sesion.expire_all()
    return _guardar(sesion, obra)


@rutas.put("/obras/{obra_id}/fases/orden", response_model=Cronograma)
def ordenar_fases(
    obra_id: int, datos: OrdenFases, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra = obra_propia(sesion, dueno, obra_id)
    fases = {f.id: f for f in sesion.scalars(select(Fase).where(Fase.obra_id == obra_id))}
    if sorted(datos.ids) != sorted(fases):
        raise HTTPException(422, "El orden debe incluir todas las fases de la obra, una sola vez")
    for posicion, fase_id in enumerate(datos.ids, start=1):
        fases[fase_id].orden = posicion
    return _guardar(sesion, obra)


# --- Actividades ---


def _validar_predecesoras(sesion: Session, obra: Obra, actividad_id: int | None, predecesoras: list[int]) -> None:
    if len(set(predecesoras)) != len(predecesoras):
        raise HTTPException(422, "Hay predecesoras repetidas")
    if actividad_id is not None and actividad_id in predecesoras:
        raise HTTPException(422, "Una actividad no puede ser predecesora de sí misma")
    actividades = servicios.actividades_de_obra(sesion, obra.id)
    nombres = {a.id: a.nombre for a in actividades}
    if any(p not in nombres for p in predecesoras):
        raise HTTPException(422, "Las predecesoras deben ser actividades de esta misma obra")
    if actividad_id is None:
        return  # una actividad nueva no tiene sucesoras: no puede cerrar un ciclo
    enlaces = {
        sucesora: [(d.predecesora_id, d.desfase_dias) for d in deps]
        for sucesora, deps in servicios.predecesoras_por_actividad(sesion, obra.id).items()
    }
    enlaces[actividad_id] = [(p, 0) for p in predecesoras]
    try:
        cr.orden_topologico(servicios.datos_cronograma(actividades, enlaces))
    except cr.DependenciaCircular as e:
        recorrido = " → ".join(nombres[i] for i in e.ciclo + e.ciclo[:1])
        raise HTTPException(422, f"Dependencia circular: {recorrido}") from None


def _actividad_propia(sesion: Session, dueno: Usuario, actividad_id: int) -> tuple[Actividad, Obra]:
    actividad = sesion.get(Actividad, actividad_id)
    if actividad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Actividad no encontrada")
    return actividad, obra_propia(sesion, dueno, actividad.obra_id)


@rutas.post("/fases/{fase_id}/actividades", response_model=Cronograma, status_code=status.HTTP_201_CREATED)
def crear_actividad(
    fase_id: int,
    datos: ActividadEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    fase, obra = _fase_propia(sesion, dueno, fase_id)
    _validar_predecesoras(sesion, obra, None, datos.predecesoras)
    orden = (sesion.scalar(select(func.max(Actividad.orden)).where(Actividad.fase_id == fase_id)) or 0) + 1
    inicio = datos.inicio_manual or obra.fecha_inicio  # provisional: el recálculo pone la fecha real
    actividad = Actividad(
        obra_id=obra.id,
        fase_id=fase.id,
        nombre=datos.nombre.strip(),
        duracion_dias=datos.duracion_dias,
        inicio_manual=datos.inicio_manual,
        fecha_inicio=inicio,
        fecha_fin=cr.fin_de(inicio, datos.duracion_dias),
        orden=orden,
        predecesoras=[Dependencia(predecesora_id=p) for p in datos.predecesoras],
    )
    sesion.add(actividad)
    return _guardar(sesion, obra)


@rutas.put("/actividades/{actividad_id}", response_model=Cronograma)
def editar_actividad(
    actividad_id: int,
    datos: ActividadEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    actividad, obra = _actividad_propia(sesion, dueno, actividad_id)
    _validar_predecesoras(sesion, obra, actividad.id, datos.predecesoras)
    if datos.fase_id is not None and datos.fase_id != actividad.fase_id:
        destino = sesion.get(Fase, datos.fase_id)
        if destino is None or destino.obra_id != obra.id:
            raise HTTPException(422, "La fase no es de esta obra")
        actividad.fase_id = destino.id
    actividad.nombre = datos.nombre.strip()
    actividad.duracion_dias = datos.duracion_dias
    actividad.inicio_manual = datos.inicio_manual
    actividad.predecesoras = [Dependencia(predecesora_id=p, sucesora_id=actividad.id) for p in datos.predecesoras]
    return _guardar(sesion, obra)


@rutas.delete("/actividades/{actividad_id}", response_model=Cronograma)
def borrar_actividad(
    actividad_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    actividad, obra = _actividad_propia(sesion, dueno, actividad_id)
    sesion.delete(actividad)
    sesion.flush()
    sesion.expire_all()
    return _guardar(sesion, obra)
