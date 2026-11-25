"""Genera los archivos Excel de la carpeta /kit desde el código, para que siempre coincidan con la app.

Uso:  python -m app.tcm.kit
  kit/plantillas/plantilla-kit-tcm.xlsx         plantilla vacía del estimado (para importar una obra)
  kit/plantillas/riesgos-y-cambios.xlsx         registro de riesgos y bitácora de cambios vacíos
  kit/ejemplo/vivienda-120m2.xlsx               la obra de ejemplo llena, lista para importar
  kit/ejemplo/estimado-vivienda-en-ejecucion.xlsx  lo que exporta la app de la obra de ejemplo en ejecución
  kit/prueba/hoja-de-registro.xlsx              hoja de registro de la prueba de uso (tiempos, errores, SUS)

No toca la base de datos de la app: la obra en ejecución se arma en una base temporal.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import servicios
from app.tcm import ejemplo
from app.tcm.hoja_prueba import escribir_hoja_prueba
from app.tcm.plantilla import escribir_plantilla
from app.tcm.registros_excel import escribir_registros

CARPETA = ejemplo.RAIZ_PROYECTO / "kit"


def _estimado_en_ejecucion(contenido_ejemplo: bytes) -> bytes:
    from app.db import Base, crear_motor
    from app.modelos import ROL_DUENO, Cambio, LineaBase, Riesgo, Usuario
    from app.tcm import exportar

    with tempfile.TemporaryDirectory() as carpeta:
        motor = crear_motor(f"sqlite:///{Path(carpeta) / 'kit.db'}")
        Base.metadata.create_all(motor)
        try:
            with sessionmaker(bind=motor)() as sesion:
                dueno = Usuario(
                    nombre="Constructora de ejemplo", correo="ejemplo@kit.bo", rol=ROL_DUENO, clave_hash="-"
                )
                sesion.add(dueno)
                sesion.flush()
                obra = ejemplo.cargar_en_ejecucion(sesion, dueno, contenido_ejemplo, servicios.hoy())
                sesion.commit()
                riesgos = list(sesion.scalars(select(Riesgo).where(Riesgo.obra_id == obra.id).order_by(Riesgo.numero)))
                cambios = list(sesion.scalars(select(Cambio).where(Cambio.obra_id == obra.id).order_by(Cambio.numero)))
                versiones = {
                    b.cambio_id: b.version
                    for b in sesion.scalars(select(LineaBase).where(LineaBase.obra_id == obra.id))
                    if b.cambio_id
                }
                return exportar.exportar_estimado(
                    sesion, obra, servicios.linea_base_vigente(sesion, obra.id), registros=(riesgos, cambios, versiones)
                )
        finally:
            motor.dispose()


def generar(destino: Path = CARPETA) -> list[Path]:
    archivos: list[Path] = []

    def guardar(ruta: str, contenido: bytes) -> None:
        archivo = destino / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(contenido)
        archivos.append(archivo)

    contenido_ejemplo = escribir_plantilla(ejemplo.datos())
    guardar("plantillas/plantilla-kit-tcm.xlsx", escribir_plantilla())
    guardar("plantillas/riesgos-y-cambios.xlsx", escribir_registros([], [], {}))
    guardar("ejemplo/vivienda-120m2.xlsx", contenido_ejemplo)
    guardar("ejemplo/estimado-vivienda-en-ejecucion.xlsx", _estimado_en_ejecucion(contenido_ejemplo))
    guardar("prueba/hoja-de-registro.xlsx", escribir_hoja_prueba())
    return archivos


if __name__ == "__main__":
    for archivo in generar():
        print(archivo.relative_to(ejemplo.RAIZ_PROYECTO))
