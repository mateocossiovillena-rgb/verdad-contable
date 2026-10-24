"""Crea o actualiza las partidas de todas las actividades del cronograma, en todas las obras.

Uso (una vez, después de `alembic upgrade head`):  python -m app.sincronizar
Las obras con cronograma creado antes de unir actividades y partidas no tienen esas partidas hasta que se
cambia algo de su cronograma; este comando las crea de una vez.
"""

from sqlalchemy import select

from app import servicios
from app.db import FabricaSesion
from app.modelos import Obra


def sincronizar() -> int:
    with FabricaSesion() as sesion:
        obras = list(sesion.scalars(select(Obra)))
        for obra in obras:
            servicios.recalcular_cronograma(sesion, obra)
        sesion.commit()
    return len(obras)


if __name__ == "__main__":
    print(f"Listo: {sincronizar()} obra(s) revisadas.")
