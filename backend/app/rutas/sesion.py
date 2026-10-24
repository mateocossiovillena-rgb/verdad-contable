"""Registro de dueños, inicio de sesión y equipo (encargados)."""

import math

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app import config
from app.db import obtener_sesion
from app.esquemas import (
    EncargadoCambios,
    EncargadoNuevo,
    EncargadoSalida,
    Ingreso,
    RegistroDueno,
    Sesion,
    UsuarioSalida,
)
from app.modelos import ROL_DUENO, ROL_ENCARGADO, Asignacion, Usuario
from app.seguridad import (
    cifrar_clave,
    crear_token,
    intentos_ingreso,
    obra_propia,
    solo_dueno,
    usuario_actual,
    verificar_clave,
)

rutas = APIRouter(prefix="/api", tags=["sesión"])


def _normalizar_telefono(telefono: str) -> str:
    return telefono.replace(" ", "")


@rutas.post("/sesion/registro", response_model=Sesion, status_code=status.HTTP_201_CREATED)
def registrar_dueno(datos: RegistroDueno, sesion: Session = Depends(obtener_sesion)):
    correo = datos.correo.strip().lower()
    if sesion.scalar(select(Usuario).where(Usuario.correo == correo)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese correo")
    usuario = Usuario(nombre=datos.nombre.strip(), correo=correo, rol=ROL_DUENO, clave_hash=cifrar_clave(datos.clave))
    sesion.add(usuario)
    sesion.commit()
    return Sesion(token=crear_token(usuario), usuario=UsuarioSalida.model_validate(usuario))


@rutas.post("/sesion/ingreso", response_model=Sesion)
def ingresar(datos: Ingreso, peticion: Request, sesion: Session = Depends(obtener_sesion)):
    identificador = datos.usuario.strip()
    # Se bloquea por cuenta (alguien probando PINs de un celular) y por IP (probando muchas cuentas).
    clave_usuario = "usuario:" + _normalizar_telefono(identificador.lower())
    clave_ip = "ip:" + (peticion.client.host if peticion.client else "desconocida")
    ventana = config.MINUTOS_BLOQUEO * 60
    espera = max(
        intentos_ingreso.segundos_bloqueado(clave_usuario, config.INTENTOS_POR_USUARIO, ventana),
        intentos_ingreso.segundos_bloqueado(clave_ip, config.INTENTOS_POR_IP, ventana),
    )
    if espera > 0:
        minutos = max(1, math.ceil(espera / 60))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Demasiados intentos fallidos. Espera {minutos} min y vuelve a intentar.",
            headers={"Retry-After": str(math.ceil(espera))},
        )
    usuario = sesion.scalar(
        select(Usuario).where(
            or_(Usuario.correo == identificador.lower(), Usuario.telefono == _normalizar_telefono(identificador))
        )
    )
    if usuario is None or not usuario.activo or not verificar_clave(datos.clave, usuario.clave_hash):
        intentos_ingreso.registrar_fallo(clave_usuario)
        intentos_ingreso.registrar_fallo(clave_ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o clave incorrectos")
    intentos_ingreso.limpiar(clave_usuario)
    return Sesion(token=crear_token(usuario), usuario=UsuarioSalida.model_validate(usuario))


@rutas.get("/sesion/yo", response_model=UsuarioSalida)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario


def _encargado_salida(sesion: Session, encargado: Usuario) -> EncargadoSalida:
    obra_ids = list(sesion.scalars(select(Asignacion.obra_id).where(Asignacion.usuario_id == encargado.id)))
    return EncargadoSalida.model_validate(encargado).model_copy(update={"obra_ids": obra_ids})


def _asignar(sesion: Session, dueno: Usuario, encargado: Usuario, obra_ids: list[int]) -> None:
    for obra_id in obra_ids:
        obra_propia(sesion, dueno, obra_id)
    sesion.execute(delete(Asignacion).where(Asignacion.usuario_id == encargado.id))
    for obra_id in set(obra_ids):
        sesion.add(Asignacion(usuario_id=encargado.id, obra_id=obra_id))


def _encargado_propio(sesion: Session, dueno: Usuario, encargado_id: int) -> Usuario:
    encargado = sesion.get(Usuario, encargado_id)
    if encargado is None or encargado.dueno_id != dueno.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encargado no encontrado")
    return encargado


@rutas.get("/equipo", response_model=list[EncargadoSalida])
def listar_equipo(dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    encargados = sesion.scalars(select(Usuario).where(Usuario.dueno_id == dueno.id).order_by(Usuario.nombre))
    return [_encargado_salida(sesion, e) for e in encargados]


@rutas.post("/equipo", response_model=EncargadoSalida, status_code=status.HTTP_201_CREATED)
def crear_encargado(
    datos: EncargadoNuevo, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    telefono = _normalizar_telefono(datos.telefono)
    if sesion.scalar(select(Usuario).where(Usuario.telefono == telefono)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese teléfono")
    encargado = Usuario(
        nombre=datos.nombre.strip(),
        telefono=telefono,
        rol=ROL_ENCARGADO,
        clave_hash=cifrar_clave(datos.pin),
        dueno_id=dueno.id,
    )
    sesion.add(encargado)
    sesion.flush()
    _asignar(sesion, dueno, encargado, datos.obra_ids)
    sesion.commit()
    return _encargado_salida(sesion, encargado)


@rutas.patch("/equipo/{encargado_id}", response_model=EncargadoSalida)
def cambiar_encargado(
    encargado_id: int,
    datos: EncargadoCambios,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    encargado = _encargado_propio(sesion, dueno, encargado_id)
    if datos.nombre is not None:
        encargado.nombre = datos.nombre.strip()
    if datos.pin is not None:
        encargado.clave_hash = cifrar_clave(datos.pin)
    if datos.activo is not None:
        encargado.activo = datos.activo
    if datos.obra_ids is not None:
        _asignar(sesion, dueno, encargado, datos.obra_ids)
    sesion.commit()
    return _encargado_salida(sesion, encargado)
