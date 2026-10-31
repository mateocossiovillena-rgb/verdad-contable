"""Pone una clave nueva a un dueño que olvidó la suya (todavía no hay recuperación por correo).

Uso (en Render: servicio verdad-contable → Shell):  python -m app.cambiar_clave correo@del.dueno
Imprime una clave temporal al azar; pásasela al dueño por un canal privado. A los encargados no hace falta:
su dueño les cambia el PIN desde Equipo.
"""

import secrets
import sys

from sqlalchemy import select

from app.db import FabricaSesion
from app.modelos import ROL_DUENO, Usuario
from app.seguridad import cifrar_clave

# Sin letras que se confunden al dictarlas por teléfono (0/O, 1/l/I).
LETRAS = "abcdefghjkmnpqrstuvwxyz23456789"


def clave_temporal(largo: int = 10) -> str:
    return "".join(secrets.choice(LETRAS) for _ in range(largo))


def cambiar_clave(correo: str) -> str:
    with FabricaSesion() as sesion:
        # El registro guarda el correo en minúsculas.
        dueno = sesion.scalar(select(Usuario).where(Usuario.correo == correo.strip().lower(), Usuario.rol == ROL_DUENO))
        if dueno is None:
            raise SystemExit(f"No hay ningún dueño con el correo {correo}.")
        clave = clave_temporal()
        dueno.clave_hash = cifrar_clave(clave)
        dueno.activo = True
        sesion.commit()
    return clave


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(f"Clave nueva: {cambiar_clave(sys.argv[1])}")
    print("Si el dueño probó muchas veces, el ingreso puede seguir bloqueado hasta 15 minutos.")
