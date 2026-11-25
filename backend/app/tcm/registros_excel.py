"""Riesgos y cambios de una obra en Excel: se descargan (con lo ya cargado), se editan y se vuelven a importar.

Reglas de la importación:
- Fila con código (R-03, C-02) = actualizar ese registro; fila sin código = registro nuevo.
- Un cambio nuevo entra siempre "pendiente": aprobarlo crea una versión de la línea base y eso se hace en la app.
- Un cambio ya aprobado o rechazado no se modifica desde el Excel (se avisa y se salta).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.modelos import Cambio, Riesgo
from app.tcm import riesgos as rg
from app.tcm.plantilla import (
    GRIS,
    LLENAR,
    Problema,
    _decimal,
    _encabezados,
    _fecha,
    _fecha_de,
    _fila_vacia,
    _lista,
    _normal,
    _numero,
    _texto,
)

HOJA_RIESGOS = "Riesgos"
HOJA_CAMBIOS = "Cambios"
FILAS_EXTRA = 100

COLUMNAS_RIESGOS = [
    ("Código", 8, "Vacío = riesgo nuevo. Con código = se actualiza ese riesgo."),
    ("Descripción *", 34, ""),
    ("Causa", 26, ""),
    ("Probabilidad (%) *", 12, "0 a 100"),
    ("Impacto en costo", 14, "En la moneda de la obra"),
    ("Impacto en plazo (días)", 12, ""),
    ("Responsable", 18, ""),
    ("Estrategia", 12, "Evitar, Mitigar, Transferir o Aceptar"),
    ("Respuesta", 34, "Qué se hará"),
    ("Estado", 11, "Abierto, Ocurrido o Cerrado"),
    ("Valor esperado P × I", 14, "Se calcula solo"),
]
COLUMNAS_CAMBIOS = [
    ("Código", 8, "Vacío = cambio nuevo (entra pendiente). Con código = se actualiza, solo si sigue pendiente."),
    ("Fecha *", 12, "dd/mm/aaaa"),
    ("Solicitante *", 18, "Quién pide el cambio: cliente, residente…"),
    ("Descripción *", 40, ""),
    ("Impacto en costo", 14, "Negativo si quita alcance"),
    ("Impacto en plazo (días)", 12, "Negativo si acorta"),
    ("Estado", 11, "Se aprueba o rechaza en la app (no tocar)"),
    ("Aprobador", 16, "No tocar"),
    ("Línea base generada", 12, "No tocar"),
]
ESTRATEGIAS = {_normal(v): k for k, v in rg.ESTRATEGIAS.items()}
ESTADOS_RIESGO = {_normal(v): k for k, v in rg.ESTADOS.items()}


def _escribir_riesgos(hoja: Worksheet, riesgos: Sequence[Riesgo]) -> None:
    _encabezados(hoja, COLUMNAS_RIESGOS)
    filas = len(riesgos) + FILAS_EXTRA
    for fila in range(2, filas + 2):
        for col in range(2, 11):
            hoja.cell(row=fila, column=col).fill = LLENAR
        hoja.cell(row=fila, column=11, value=f'=IF(OR(D{fila}="",E{fila}=""),"",D{fila}/100*E{fila})').font = GRIS
        hoja.cell(row=fila, column=11).number_format = "#,##0.00"
    for fila, r in enumerate(riesgos, 2):
        valores = [
            f"R-{r.numero:02d}", r.descripcion, r.causa, float(r.probabilidad), float(r.impacto_costo),
            r.impacto_dias, r.responsable, rg.ESTRATEGIAS.get(r.estrategia, r.estrategia), r.respuesta,
            rg.ESTADOS.get(r.estado, r.estado),
        ]  # fmt: skip
        for col, valor in enumerate(valores, 1):
            hoja.cell(row=fila, column=col, value=valor)
    ultima = filas + 1
    _numero(hoja, f"D2:D{ultima}", 0, 100)
    _numero(hoja, f"E2:E{ultima}", 0)
    _numero(hoja, f"F2:F{ultima}", 0)
    _lista(hoja, list(rg.ESTRATEGIAS.values()), f"H2:H{ultima}", "Estrategia")
    _lista(hoja, list(rg.ESTADOS.values()), f"J2:J{ultima}", "Estado")
    for celda in hoja["E"][1:]:
        celda.number_format = "#,##0.00"


def _escribir_cambios(hoja: Worksheet, cambios: Sequence[Cambio], versiones: dict[int, int]) -> None:
    from app.modelos import ESTADOS_CAMBIO

    _encabezados(hoja, COLUMNAS_CAMBIOS)
    filas = len(cambios) + FILAS_EXTRA
    for fila in range(2, filas + 2):
        for col in range(2, 7):
            hoja.cell(row=fila, column=col).fill = LLENAR
        hoja.cell(row=fila, column=2).number_format = "DD/MM/YYYY"
        hoja.cell(row=fila, column=5).number_format = "#,##0.00"
    for fila, c in enumerate(cambios, 2):
        version = versiones.get(c.id)
        valores = [
            f"C-{c.numero:02d}", c.fecha, c.solicitante, c.descripcion, float(c.impacto_costo), c.impacto_dias,
            ESTADOS_CAMBIO.get(c.estado, c.estado), c.aprobador, f"v{version}" if version else "",
        ]  # fmt: skip
        for col, valor in enumerate(valores, 1):
            hoja.cell(row=fila, column=col, value=valor)
        if c.estado != "pendiente":  # ya resuelto: se ve gris, no se edita
            for col in range(1, 10):
                hoja.cell(row=fila, column=col).fill = LLENAR.__class__()
                hoja.cell(row=fila, column=col).font = GRIS
    ultima = filas + 1
    _fecha(hoja, f"B2:B{ultima}")
    _numero(hoja, f"F2:F{ultima}", -3650, 3650)


def agregar_hojas(libro: Workbook, riesgos: Sequence[Riesgo], cambios: Sequence[Cambio], versiones: dict[int, int]):
    _escribir_riesgos(libro.create_sheet(HOJA_RIESGOS), riesgos)
    _escribir_cambios(libro.create_sheet(HOJA_CAMBIOS), cambios, versiones)


def escribir_registros(riesgos: Sequence[Riesgo], cambios: Sequence[Cambio], versiones: dict[int, int]) -> bytes:
    libro = Workbook()
    libro.remove(libro.active)
    agregar_hojas(libro, riesgos, cambios, versiones)
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# --- Leer ---


@dataclass
class RiesgoLeido:
    fila: int
    numero: int | None  # None = nuevo
    datos: dict


@dataclass
class CambioLeido:
    fila: int
    numero: int | None
    datos: dict


@dataclass
class LecturaRegistros:
    riesgos: list[RiesgoLeido] = field(default_factory=list)
    cambios: list[CambioLeido] = field(default_factory=list)
    errores: list[Problema] = field(default_factory=list)
    advertencias: list[Problema] = field(default_factory=list)

    @property
    def valida(self) -> bool:
        return not self.errores


def _numero_de(codigo: str, prefijo: str) -> int | None:
    texto = codigo.strip().upper().replace(" ", "")
    if not texto.startswith(prefijo):
        return None
    try:
        return int(texto[len(prefijo) :].lstrip("-"))
    except ValueError:
        return None


def _num(lec: LecturaRegistros, hoja: str, fila: int, columna: str, valor, obligatorio=False, minimo=None, maximo=None):
    try:
        n = _decimal(valor)
    except ValueError:
        lec.errores.append(Problema(hoja, fila, columna, f"'{valor}' no es un número."))
        return None
    if n is None:
        if obligatorio:
            lec.errores.append(Problema(hoja, fila, columna, "Está vacío."))
        return None
    if (minimo is not None and n < minimo) or (maximo is not None and n > maximo):
        lec.errores.append(Problema(hoja, fila, columna, f"Debe estar entre {minimo} y {maximo}."))
        return None
    return n


def _distinto(registro, datos: dict) -> bool:
    """Solo se cuentan y graban las filas que cambian algo respecto a lo guardado."""
    return any(getattr(registro, k) != v for k, v in datos.items())


def _leer_riesgos(hoja: Worksheet, existentes: dict[int, Riesgo], lec: LecturaRegistros) -> None:
    h = HOJA_RIESGOS
    vistos: set[int] = set()
    for fila in hoja.iter_rows(min_row=2, max_col=10):
        valores = tuple(c.value for c in fila)
        if _fila_vacia(valores):
            continue
        n = fila[0].row
        numero = None
        if _texto(valores[0]):
            numero = _numero_de(_texto(valores[0]), "R")
            if numero is None or numero not in existentes:
                lec.errores.append(
                    Problema(h, n, "Código", f"No existe el riesgo {valores[0]}: déjalo vacío si es nuevo.")
                )
                continue
            if numero in vistos:
                lec.errores.append(Problema(h, n, "Código", f"El riesgo {valores[0]} está repetido."))
                continue
            vistos.add(numero)
        descripcion = _texto(valores[1])
        if len(descripcion) < 3:
            lec.errores.append(Problema(h, n, "Descripción", "Está vacía o es muy corta."))
        prob = _num(lec, h, n, "Probabilidad", valores[3], obligatorio=True, minimo=0, maximo=100)
        costo = _num(lec, h, n, "Impacto en costo", valores[4], minimo=0, maximo=Decimal("999999999999"))
        dias = _num(lec, h, n, "Impacto en plazo", valores[5], minimo=0, maximo=3650)
        estrategia = ESTRATEGIAS.get(_normal(valores[7]) or "mitigar")
        if estrategia is None:
            lec.errores.append(Problema(h, n, "Estrategia", "Debe ser Evitar, Mitigar, Transferir o Aceptar."))
        estado = ESTADOS_RIESGO.get(_normal(valores[9]) or "abierto")
        if estado is None:
            lec.errores.append(Problema(h, n, "Estado", "Debe ser Abierto, Ocurrido o Cerrado."))
        if len(descripcion) >= 3 and prob is not None and estrategia and estado:
            leido = RiesgoLeido(
                n,
                numero,
                {
                    "descripcion": descripcion[:300],
                    "causa": _texto(valores[2])[:2000],
                    "probabilidad": prob,
                    "impacto_costo": costo or Decimal("0"),
                    "impacto_dias": int(dias or 0),
                    "responsable": _texto(valores[6])[:120],
                    "estrategia": estrategia,
                    "respuesta": _texto(valores[8])[:2000],
                    "estado": estado,
                },
            )
            if numero is None or _distinto(existentes[numero], leido.datos):
                lec.riesgos.append(leido)


def _leer_cambios(hoja: Worksheet, existentes: dict[int, Cambio], lec: LecturaRegistros) -> None:
    h = HOJA_CAMBIOS
    vistos: set[int] = set()
    for fila in hoja.iter_rows(min_row=2, max_col=6):
        valores = tuple(c.value for c in fila)
        if _fila_vacia(valores):
            continue
        n = fila[0].row
        numero = None
        if _texto(valores[0]):
            numero = _numero_de(_texto(valores[0]), "C")
            if numero is None or numero not in existentes:
                lec.errores.append(
                    Problema(h, n, "Código", f"No existe el cambio {valores[0]}: déjalo vacío si es nuevo.")
                )
                continue
            if numero in vistos:
                lec.errores.append(Problema(h, n, "Código", f"El cambio {valores[0]} está repetido."))
                continue
            vistos.add(numero)
        try:
            fecha: date | None = _fecha_de(valores[1])
        except ValueError:
            lec.errores.append(Problema(h, n, "Fecha", f"'{valores[1]}' no es una fecha (usa dd/mm/aaaa)."))
            continue
        if fecha is None:
            lec.errores.append(Problema(h, n, "Fecha", "Está vacía."))
        solicitante, descripcion = _texto(valores[2]), _texto(valores[3])
        if len(solicitante) < 2:
            lec.errores.append(Problema(h, n, "Solicitante", "Está vacío."))
        if len(descripcion) < 3:
            lec.errores.append(Problema(h, n, "Descripción", "Está vacía o es muy corta."))
        costo = _num(
            lec, h, n, "Impacto en costo", valores[4], minimo=Decimal("-999999999999"), maximo=Decimal("999999999999")
        )
        dias = _num(lec, h, n, "Impacto en plazo", valores[5], minimo=-3650, maximo=3650)
        datos = {
            "fecha": fecha,
            "solicitante": solicitante[:120],
            "descripcion": descripcion[:2000],
            "impacto_costo": costo or Decimal("0"),
            "impacto_dias": int(dias or 0),
        }
        if numero is not None and existentes[numero].estado != "pendiente":
            c = existentes[numero]
            actual = {k: getattr(c, k) for k in datos}
            if actual != datos:
                lec.advertencias.append(
                    Problema(h, n, "Código", f"C-{numero:02d} ya fue {c.estado}: no se modifica desde el Excel.")
                )
            continue
        if fecha and len(solicitante) >= 2 and len(descripcion) >= 3:
            if numero is None or _distinto(existentes[numero], datos):
                lec.cambios.append(CambioLeido(n, numero, datos))


def leer_registros(contenido: bytes, riesgos: Sequence[Riesgo], cambios: Sequence[Cambio]) -> LecturaRegistros:
    lec = LecturaRegistros()
    try:
        libro = load_workbook(BytesIO(contenido), data_only=True)
    except Exception:  # openpyxl lanza varios tipos según el daño del archivo
        lec.errores.append(Problema("", None, "", "El archivo no es un Excel .xlsx válido."))
        return lec
    hojas = {_normal(n): libro[n] for n in libro.sheetnames}
    hoja_r, hoja_c = hojas.get(_normal(HOJA_RIESGOS)), hojas.get(_normal(HOJA_CAMBIOS))
    if hoja_r is None and hoja_c is None:
        lec.errores.append(Problema("", None, "", "El archivo no tiene las hojas 'Riesgos' ni 'Cambios'."))
        return lec
    if hoja_r is not None:
        _leer_riesgos(hoja_r, {r.numero: r for r in riesgos}, lec)
    if hoja_c is not None:
        _leer_cambios(hoja_c, {c.numero: c for c in cambios}, lec)
    return lec
