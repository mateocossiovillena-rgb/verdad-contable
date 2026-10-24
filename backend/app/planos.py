"""Asistente "Estimar desde plano": une los lectores de planos y los cómputos con la base de datos.

CAD (dxf): capas y unidades → plantas → formulario → cantidades → confirmada.
BIM (ifc): plantas → cantidades → confirmada. El modelo responde el formulario, por eso no se pregunta.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.calculos import computos, medicion_plano
from app.calculos.plano_dxf import Dibujo, PlanoInvalido, leer_dxf
from app.calculos.plano_ifc import leer_ifc
from app.modelos import Estimacion, MapeoCapa, Obra, Usuario

PASOS_DXF = ("capas", "plantas", "formulario", "cantidades", "confirmada")
PASOS_IFC = ("plantas", "cantidades", "confirmada")
_OTROS_FORMATOS = {
    ".dwg": "El archivo DWG no se puede leer directo. Ábrelo en tu programa de dibujo y guárdalo como DXF.",
    ".rvt": "El archivo de Revit no se puede leer directo. Expórtalo a IFC desde Revit y súbelo de nuevo.",
    ".skp": "El archivo de SketchUp no se puede leer directo. Expórtalo a IFC o DXF y súbelo de nuevo.",
    ".pdf": "Un PDF no trae medidas que se puedan leer. Sube el plano en DXF (CAD) o IFC (BIM).",
}


def tipo_de_archivo(nombre: str) -> str:
    extension = "." + nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if extension in (".dxf", ".ifc"):
        return extension[1:]
    if extension in _OTROS_FORMATOS:
        raise HTTPException(422, _OTROS_FORMATOS[extension])
    raise HTTPException(422, "Sube el plano en DXF (CAD) o IFC (BIM).")


def _ruta(estimacion: Estimacion):
    return config.CARPETA_PLANOS / estimacion.archivo


@lru_cache(maxsize=4)
def _dibujo(archivo: str) -> Dibujo:
    """El DXF se vuelve a leer del disco al cambiar de paso; se guardan los últimos en memoria."""
    return leer_dxf((config.CARPETA_PLANOS / archivo).read_bytes())


def _factor(estimacion: Estimacion) -> float:
    return medicion_plano.UNIDADES[estimacion.unidades or 6][1]


def _exigir_paso(estimacion: Estimacion, minimo: str) -> None:
    pasos = PASOS_DXF if estimacion.tipo_archivo == "dxf" else PASOS_IFC
    if pasos.index(estimacion.paso) < pasos.index(minimo):
        raise HTTPException(status.HTTP_409_CONFLICT, "Primero completa los pasos anteriores.")


# --- Subir ---


def crear(sesion: Session, obra: Obra, usuario: Usuario, nombre: str, datos: bytes) -> Estimacion:
    """Lee el archivo (lento: llamar fuera del hilo de eventos) y crea la estimación en su primer paso."""
    tipo = tipo_de_archivo(nombre)
    try:
        lectura = _leer(sesion, usuario, tipo, datos)
    except PlanoInvalido as error:
        raise HTTPException(422, str(error)) from None
    config.CARPETA_PLANOS.mkdir(parents=True, exist_ok=True)
    archivo = uuid.uuid4().hex + "." + tipo
    (config.CARPETA_PLANOS / archivo).write_bytes(datos)
    estimacion = Estimacion(
        obra_id=obra.id,
        creado_por=usuario.id,
        tipo_archivo=tipo,
        nombre_archivo=nombre[-200:],
        archivo=archivo,
        lectura=lectura,
        ediciones={},
    )
    if tipo == "dxf":
        estimacion.paso = "capas"
        estimacion.unidades = lectura.pop("unidades")
        estimacion.capas = lectura.pop("roles")
        estimacion.plantas = []
    else:
        estimacion.paso = "plantas"
        estimacion.capas = {}
        estimacion.formulario = lectura["formulario"]
        estimacion.plantas = [
            {"indice": i, "nombre": p["nombre"], "incluir": p["incluir"], "repeticiones": 1}
            for i, p in enumerate(lectura["pisos"])
        ]
    sesion.add(estimacion)
    sesion.commit()
    return estimacion


def _leer(sesion: Session, usuario: Usuario, tipo: str, datos: bytes) -> dict:
    if tipo == "ifc":
        modelo = leer_ifc(datos)
        return {
            "pisos": [
                {
                    "nombre": p.nombre,
                    "elevacion": round(p.elevacion, 2),
                    "elementos": p.elementos,
                    "incluir": any(p.elementos.values()),
                    "medido": p.medido.como_dict(),
                }
                for p in modelo.pisos
            ],
            "formulario": modelo.formulario.como_dict(),
            "datos_del_modelo": modelo.datos_del_modelo,
            "avisos": modelo.avisos,
        }
    dibujo = leer_dxf(datos)
    capas = medicion_plano.resumen_capas(dibujo)
    if not capas:
        raise PlanoInvalido("El plano no tiene nada dibujado que se pueda medir.")
    guardados = dict(
        sesion.execute(select(MapeoCapa.capa, MapeoCapa.rol).where(MapeoCapa.dueno_id == usuario.id)).all()
    )
    roles = {}
    for c in capas:
        recordado = guardados.get(medicion_plano.normalizar(c["nombre"]))
        c["recordada"] = recordado is not None
        roles[c["nombre"]] = recordado or c["rol_sugerido"]
    unidades, deducidas = medicion_plano.detectar_unidades(dibujo)
    return {
        "capas": capas,
        "unidades": unidades,
        "unidades_deducidas": deducidas,
        "roles": roles,
        "avisos": dibujo.avisos,
    }


# --- Pasos ---


def aplicar_capas(sesion: Session, estimacion: Estimacion, usuario: Usuario, capas: dict[str, str], unidades: int):
    """Guarda el rol de cada capa (y lo recuerda para el próximo plano) y busca las plantas del dibujo."""
    conocidas = {c["nombre"] for c in estimacion.lectura["capas"]}
    roles = {nombre: capas.get(nombre, estimacion.capas.get(nombre, "ignorar")) for nombre in conocidas}
    if not any(r == "muros" for r in roles.values()):
        raise HTTPException(422, "Marca al menos una capa como muros.")
    estimacion.capas = roles
    estimacion.unidades = unidades
    _recordar_capas(sesion, usuario, roles)

    dibujo = _dibujo(estimacion.archivo)
    regiones = medicion_plano.detectar_regiones(dibujo, roles, _factor(estimacion))
    resumenes = [medicion_plano.resumen_region(dibujo, r, roles, _factor(estimacion)) for r in regiones]
    if not any(r["tiene_muros"] for r in resumenes):
        raise HTTPException(422, "No encontramos muros en las capas marcadas. Revisa las capas y las unidades.")
    estimacion.lectura = {**estimacion.lectura, "regiones": resumenes}
    estimacion.plantas = _plantas_iniciales(resumenes)
    estimacion.medicion = None
    estimacion.paso = "plantas"
    sesion.commit()


def _recordar_capas(sesion: Session, usuario: Usuario, roles: dict[str, str]) -> None:
    guardados = {m.capa: m for m in sesion.scalars(select(MapeoCapa).where(MapeoCapa.dueno_id == usuario.id))}
    for nombre, rol in roles.items():
        clave = medicion_plano.normalizar(nombre)[:120]
        if clave in guardados:
            guardados[clave].rol = rol
        else:
            guardados[clave] = MapeoCapa(dueno_id=usuario.id, capa=clave, rol=rol)
            sesion.add(guardados[clave])


def _plantas_iniciales(resumenes: list[dict]) -> list[dict]:
    plantas, n = [], 0
    for i, r in enumerate(resumenes):
        nombre = f"Zona {i + 1}"
        if r["tiene_muros"]:
            nombre = "Planta baja" if n == 0 else f"Piso {n}"
            n += 1
        plantas.append({"indice": i, "nombre": nombre, "incluir": r["tiene_muros"], "repeticiones": 1})
    return plantas


def aplicar_plantas(sesion: Session, estimacion: Estimacion, plantas: list[dict]) -> None:
    """Cuáles zonas del dibujo (o pisos del modelo) son plantas de la obra, con su nombre, y las mide."""
    _exigir_paso(estimacion, "plantas")
    total = len(estimacion.lectura["regiones"] if estimacion.tipo_archivo == "dxf" else estimacion.lectura["pisos"])
    por_indice = {p["indice"]: p for p in plantas if 0 <= p["indice"] < total}
    nuevas = [
        por_indice.get(p["indice"], p) | {"nombre": por_indice.get(p["indice"], p)["nombre"].strip()}
        for p in estimacion.plantas
    ]
    incluidas = [p for p in nuevas if p["incluir"]]
    if not incluidas:
        raise HTTPException(422, "Elige al menos una planta.")
    nombres = [p["nombre"].lower() for p in incluidas]
    if len(set(nombres)) != len(nombres) or not all(nombres):
        raise HTTPException(422, "Cada planta necesita un nombre distinto.")
    estimacion.plantas = nuevas

    if estimacion.tipo_archivo == "dxf":
        dibujo = _dibujo(estimacion.archivo)
        regiones = medicion_plano.detectar_regiones(dibujo, estimacion.capas, _factor(estimacion))
        pisos, avisos = [], []
        for p in incluidas:
            medida = medicion_plano.medir_planta(
                dibujo, regiones[p["indice"]], estimacion.capas, _factor(estimacion), p["nombre"]
            )
            medida.piso.repeticiones = p["repeticiones"]
            pisos.append({"medido": medida.piso.como_dict(), "geometria": medida.geometria})
            avisos += [a if a.startswith(p["nombre"]) else f"{p['nombre']}: {a}" for a in medida.avisos]
        estimacion.medicion = {"pisos": pisos, "avisos": avisos}
        estimacion.paso = "formulario"
        if estimacion.formulario is None:
            estimacion.formulario = computos.Formulario().como_dict()
    else:
        pisos = []
        for p in incluidas:
            medido = dict(estimacion.lectura["pisos"][p["indice"]]["medido"])
            medido.update(nombre=p["nombre"], repeticiones=p["repeticiones"])
            pisos.append({"medido": medido, "geometria": None})
        estimacion.medicion = {"pisos": pisos, "avisos": []}
        estimacion.paso = "cantidades"
    sesion.commit()


def aplicar_formulario(sesion: Session, estimacion: Estimacion, formulario: dict) -> None:
    if estimacion.tipo_archivo != "dxf":
        raise HTTPException(status.HTTP_409_CONFLICT, "Los planos BIM no llevan formulario: el modelo ya los trae.")
    _exigir_paso(estimacion, "formulario")
    estimacion.formulario = computos.Formulario.desde_dict(formulario).como_dict()
    estimacion.paso = "cantidades"
    sesion.commit()


def aplicar_cantidades(sesion: Session, estimacion: Estimacion, ediciones: dict[str, float], confirmar: bool):
    """Guarda las correcciones a mano. Las claves que ya no existen se descartan."""
    _exigir_paso(estimacion, "cantidades")
    claves = {c.clave for c in _cantidades_calculadas(estimacion)}
    estimacion.ediciones = {k: round(v, 2) for k, v in ediciones.items() if k in claves}
    if confirmar:
        estimacion.paso = "confirmada"
    elif estimacion.paso == "confirmada":
        estimacion.paso = "cantidades"
    sesion.commit()


def borrar(sesion: Session, estimacion: Estimacion) -> None:
    _ruta(estimacion).unlink(missing_ok=True)
    _dibujo.cache_clear()
    sesion.delete(estimacion)
    sesion.commit()


# --- Salida ---


def _cantidades_calculadas(estimacion: Estimacion) -> list[computos.Cantidad]:
    if not estimacion.medicion or estimacion.formulario is None:
        return []
    pisos = [computos.PisoMedido.desde_dict(p["medido"]) for p in estimacion.medicion["pisos"]]
    origen = "formulario" if estimacion.tipo_archivo == "dxf" else "proporcion"
    return computos.calcular(pisos, computos.Formulario.desde_dict(estimacion.formulario), origen)


def cantidades(estimacion: Estimacion) -> list[dict]:
    salida = []
    for c in _cantidades_calculadas(estimacion):
        fila = {**c.__dict__, "cantidad_original": None, "origen_original": None}
        if c.clave in estimacion.ediciones:
            fila.update(
                cantidad=estimacion.ediciones[c.clave],
                cantidad_original=c.cantidad,
                origen_original=c.origen,
                origen="editada",
            )
        salida.append(fila)
    return salida


def salida(estimacion: Estimacion) -> dict:
    lectura = estimacion.lectura
    if estimacion.tipo_archivo == "dxf":
        capas = [{**c, "rol": estimacion.capas.get(c["nombre"], "ignorar")} for c in lectura["capas"]]
        zonas = lectura.get("regiones", [])
        plantas = [
            {
                **p,
                "ancho": zonas[p["indice"]]["ancho"],
                "alto": zonas[p["indice"]]["alto"],
                "detalle": "con muros" if zonas[p["indice"]]["tiene_muros"] else "sin muros",
            }
            for p in estimacion.plantas
        ]
    else:
        capas = []
        plantas = [
            {**p, "ancho": None, "alto": None, "detalle": _detalle_piso(lectura["pisos"][p["indice"]])}
            for p in estimacion.plantas
        ]
    medidos = [p["medido"] for p in (estimacion.medicion or {}).get("pisos", [])]
    return {
        "id": estimacion.id,
        "obra_id": estimacion.obra_id,
        "tipo_archivo": estimacion.tipo_archivo,
        "nombre_archivo": estimacion.nombre_archivo,
        "paso": estimacion.paso,
        "pasos": list(PASOS_DXF if estimacion.tipo_archivo == "dxf" else PASOS_IFC),
        "unidades": estimacion.unidades,
        "unidades_deducidas": lectura.get("unidades_deducidas", False),
        "capas": capas,
        "plantas": plantas,
        "formulario": estimacion.formulario,
        "datos_del_modelo": lectura.get("datos_del_modelo", []),
        "pisos_medidos": [_resumen_medido(m) for m in medidos],
        "cantidades": cantidades(estimacion),
        "avisos": lectura.get("avisos", []) + (estimacion.medicion or {}).get("avisos", []),
        "creado_en": estimacion.creado_en,
    }


_SINGULAR = {
    "muros": "muro",
    "losas": "losa",
    "puertas": "puerta",
    "ventanas": "ventana",
    "columnas": "columna",
    "vigas": "viga",
    "ambientes": "ambiente",
}


def _detalle_piso(piso: dict) -> str:
    """Qué trae un piso del modelo, en palabras: "4 muros, 1 puerta, cubierta"."""
    partes = []
    for tipo, n in piso["elementos"].items():
        if n:
            partes.append("cubierta" if tipo == "cubierta" else f"{n} {_SINGULAR.get(tipo, tipo) if n == 1 else tipo}")
    return ", ".join(partes) or "vacío"


def _resumen_medido(m: dict) -> dict:
    return {
        "nombre": m["nombre"],
        "repeticiones": m["repeticiones"],
        "area_planta": m["area_planta"],
        "largo_muros": m["largo_muros"],
        "perimetro_exterior": m["perimetro_exterior"],
        "ambientes": len(m["ambientes"]),
        "banos": m["banos"],
        "cocinas": m["cocinas"],
        "puertas": len(m["puertas"]),
        "ventanas": len(m["ventanas"]),
    }


def geometria(estimacion: Estimacion) -> dict:
    """Lo necesario para dibujar el plano en el navegador: zonas para elegir plantas y plantas medidas."""
    return {
        "zonas": [
            {"indice": i, "ancho": r["ancho"], "alto": r["alto"], "muros": r["muros"]}
            for i, r in enumerate(estimacion.lectura.get("regiones", []))
        ],
        "plantas": [
            {"nombre": p["medido"]["nombre"], **p["geometria"]}
            for p in (estimacion.medicion or {}).get("pisos", [])
            if p["geometria"]
        ],
    }
