"""Claves, sesiones y permisos."""

import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import obtener_sesion
from app.modelos import ROL_DUENO, Asignacion, Obra, Partida, Usuario

ITERACIONES = 200_000
_portador = HTTPBearer(auto_error=False)


def cifrar_clave(clave: str) -> str:
    sal = secrets.token_hex(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), ITERACIONES).hex()
    return f"pbkdf2_sha256${ITERACIONES}${sal}${resumen}"


def verificar_clave(clave: str, guardada: str) -> bool:
    try:
        _, iteraciones, sal, resumen = guardada.split("$")
    except ValueError:
        return False
    calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), int(iteraciones)).hex()
    return hmac.compare_digest(calculado, resumen)


class ControlIntentos:
    """Cuenta ingresos fallidos por clave (usuario o IP) dentro de una ventana de tiempo.

    En memoria: alcanza para un solo proceso del servidor, que es como se despliega el MVP.
    """

    def __init__(self, reloj: Callable[[], float] = time.monotonic):
        self._reloj = reloj
        self._fallos: dict[str, list[float]] = {}

    def _recientes(self, clave: str, ventana: float) -> list[float]:
        limite = self._reloj() - ventana
        fallos = [t for t in self._fallos.get(clave, []) if t > limite]
        if fallos:
            self._fallos[clave] = fallos
        else:
            self._fallos.pop(clave, None)
        return fallos

    def segundos_bloqueado(self, clave: str, maximo: int, ventana: float) -> float:
        """0 si puede intentar; si no, cuánto falta para que caduque el fallo más antiguo."""
        fallos = self._recientes(clave, ventana)
        if len(fallos) < maximo:
            return 0.0
        return max(0.0, fallos[-maximo] + ventana - self._reloj())

    def registrar_fallo(self, clave: str) -> None:
        self._fallos.setdefault(clave, []).append(self._reloj())

    def limpiar(self, clave: str | None = None) -> None:
        if clave is None:
            self._fallos.clear()
        else:
            self._fallos.pop(clave, None)


intentos_ingreso = ControlIntentos()


def crear_token(usuario: Usuario) -> str:
    vence = datetime.now(UTC) + timedelta(days=config.DIAS_SESION)
    return jwt.encode({"sub": str(usuario.id), "exp": vence}, config.CLAVE_SECRETA, algorithm="HS256")


def usuario_actual(
    credencial: HTTPAuthorizationCredentials | None = Depends(_portador),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    no_autorizado = HTTPException(status.HTTP_401_UNAUTHORIZED, "Inicia sesión de nuevo")
    if credencial is None:
        raise no_autorizado
    try:
        datos = jwt.decode(credencial.credentials, config.CLAVE_SECRETA, algorithms=["HS256"])
        usuario = sesion.get(Usuario, int(datos["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise no_autorizado from None
    if usuario is None or not usuario.activo:
        raise no_autorizado
    return usuario


def solo_dueno(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    if usuario.rol != ROL_DUENO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el dueño puede hacer esto")
    return usuario


def ids_obras_visibles(sesion: Session, usuario: Usuario) -> list[int]:
    if usuario.rol == ROL_DUENO:
        return list(sesion.scalars(select(Obra.id).where(Obra.dueno_id == usuario.id)))
    return list(sesion.scalars(select(Asignacion.obra_id).where(Asignacion.usuario_id == usuario.id)))


def obra_visible(sesion: Session, usuario: Usuario, obra_id: int) -> Obra:
    """La obra si el usuario puede verla; si no, 404 (no revela si existe)."""
    obra = sesion.get(Obra, obra_id)
    if obra is None or obra_id not in ids_obras_visibles(sesion, usuario):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Obra no encontrada")
    return obra


def obra_propia(sesion: Session, usuario: Usuario, obra_id: int) -> Obra:
    obra = sesion.get(Obra, obra_id)
    if obra is None or obra.dueno_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Obra no encontrada")
    return obra


def partida_visible(sesion: Session, usuario: Usuario, partida_id: int) -> Partida:
    partida = sesion.get(Partida, partida_id)
    if partida is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partida no encontrada")
    obra_visible(sesion, usuario, partida.obra_id)
    return partida
