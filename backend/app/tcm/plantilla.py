"""Plantilla Excel del Kit TCM: se descarga vacía, se llena y se vuelve a subir.

`escribir_plantilla(datos)` arma el libro (vacío o lleno con una obra, como el ejemplo del kit) y
`leer_plantilla(bytes)` lo lee y valida fila por fila sin tocar la base de datos.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from app.calculos import cronograma as cr
from app.tcm import clasificacion as cl

# Colores: amarillo claro = llenar; gris = no tocar.
LLENAR = PatternFill("solid", fgColor="FFF4CC")
ENCABEZADO = PatternFill("solid", fgColor="E7E5E4")
NEGRITA = Font(bold=True)
TITULO = Font(bold=True, size=14)
GRIS = Font(color="78716C", italic=True)
BORDE = Border(bottom=Side(style="thin", color="D6D3D1"))
FILAS_DATOS = 300  # filas preparadas con color y validaciones en Actividades e Insumos

HOJA_INSTRUCCIONES = "Instrucciones"
HOJA_OBRA = "Datos de obra"
HOJA_CLASIFICACION = "Clasificación"
HOJA_ACTIVIDADES = "Actividades"
HOJA_INSUMOS = "APU-Insumos"
HOJA_BASE = "Base del estimado"

# (clave, etiqueta, ayuda). Porcentajes de 0 a 100.
CAMPOS_OBRA = [
    ("nombre", "Nombre de la obra *", "Ej. Vivienda Familia Rojas"),
    ("cliente", "Cliente", ""),
    ("ubicacion", "Ubicación", "Barrio, ciudad"),
    ("fecha_inicio", "Fecha de inicio *", "dd/mm/aaaa"),
    ("moneda", "Moneda *", "Bs o USD"),
    ("cargas_sociales", "Cargas sociales (% de la mano de obra)", "Usual en Bolivia: 55 % a 71,18 %"),
    ("iva_mano_obra", "IVA de la mano de obra (%)", "Usual: 14,94 %; 0 si no aplica"),
    ("herramientas", "Herramientas menores (% de la mano de obra)", "Usual: 5 %"),
    ("gastos_generales", "Gastos generales (% del costo directo)", "Usual: 8 % a 15 %"),
    ("utilidad", "Utilidad (%)", "Usual: 7 % a 10 %"),
    ("impuestos", "Impuestos IT (%)", "IT: 3,09 %"),
]
PARAMETROS = ["cargas_sociales", "iva_mano_obra", "herramientas", "gastos_generales", "utilidad", "impuestos"]

COLUMNAS_ACTIVIDADES = [
    ("Código *", 10, "Único. Ej. 1.1, 1.2, 2.1"),
    ("Fase *", 22, "Agrupa actividades (WBS). Ej. Obra gruesa"),
    ("Actividad *", 40, ""),
    ("Unidad *", 9, "m², m³, ml, pza, glb…"),
    ("Cómputo *", 11, "Cantidad de obra en esa unidad"),
    ("Duración *", 10, "Número mayor a 0"),
    ("Unidad de duración *", 14, "días, semanas o meses"),
    ("Predecesoras", 16, "Códigos separados por coma. Ej. 1.1, 1.2"),
    ("Inicio fijo", 13, "Opcional, dd/mm/aaaa. Solo si no tiene predecesoras"),
    ("Regla de medición", 13, "Cómo se gana el valor: % físico (por defecto), 0/100 o 50/50"),
]
REGLAS_TEXTO = {"porcentaje": "% físico", "0_100": "0/100", "50_50": "50/50"}
REGLA_DE_TEXTO = {"%fisico": "porcentaje", "fisico": "porcentaje", "porcentaje": "porcentaje", "0/100": "0_100",
                  "50/50": "50_50"}  # fmt: skip
COLUMNAS_INSUMOS = [
    ("Código de actividad *", 12, "El de la hoja Actividades"),
    ("Tipo *", 14, "Material, Mano de obra o Equipo"),
    ("Insumo *", 34, "Ej. Cemento, Albañil, Mezcladora"),
    ("Unidad *", 9, "bolsa, hr, m³…"),
    ("Cantidad por unidad de actividad *", 16, "Rendimiento. Ej. 0,25 bolsas por m²"),
    ("Precio unitario *", 13, "En la moneda de la obra"),
]
TIPOS_INSUMO = {"material": "Material", "mano de obra": "Mano de obra", "equipo": "Equipo"}
CLAVE_TIPO = {"material": "material", "mano de obra": "mano_obra", "equipo": "equipo"}
UNIDADES_DURACION = {
    "dias": "dias",
    "dia": "dias",
    "semanas": "semanas",
    "semana": "semanas",
    "meses": "meses",
    "mes": "meses",
}

CAMPOS_BASE = [
    ("proposito", "Propósito del estimado"),
    ("alcance", "Alcance"),
    ("metodologia", "Metodología"),
    ("base_diseno", "Base de diseño (documentos usados)"),
    ("base_planificacion", "Base de planificación (cómo se ejecutará)"),
    ("fuentes_precios", "Fuentes de precios"),
    ("fecha_precios", "Fecha de los precios (dd/mm/aaaa)"),
    ("supuestos", "Supuestos"),
    ("exclusiones", "Exclusiones"),
    ("riesgos_oportunidades", "Riesgos y oportunidades"),
    ("contingencia_porcentaje", "Contingencia (% del estimado)"),
    ("contingencia_nota", "Contingencia: criterio"),
]

INSTRUCCIONES = [
    "Kit TCM para pymes constructoras — Plantilla del estimado",
    "",
    "1. Llena solo las celdas AMARILLAS. Los campos con * son obligatorios.",
    "2. 'Datos de obra': nombre, fecha de inicio, moneda y los porcentajes del APU de tu empresa.",
    "3. 'Clasificación': marca qué entregables tienes (no / parcial / completo). Con eso se calcula la clase",
    "    del estimado (AACE 56R-08 / 17R-97) y su rango de exactitud.",
    "4. 'Actividades': una fila por actividad (WBS). El código debe ser único; las predecesoras se escriben",
    "    con los códigos de otras actividades, separados por coma.",
    "5. 'APU-Insumos': los materiales, mano de obra y equipo de cada actividad, POR UNIDAD de la actividad",
    "    (ej. bolsas de cemento por m² de muro). El sistema multiplica por el cómputo.",
    "6. 'Base del estimado' (AACE 34R-05): documenta cómo armaste el estimado.",
    "7. Sube el archivo en Verdad Contable → Obras → Importar desde Excel. Verás los errores fila por fila",
    "    antes de confirmar; no se graba nada hasta que confirmes.",
    "",
    "No cambies los nombres de las hojas ni el orden de las columnas.",
]


# --- Datos leídos ---


@dataclass
class ActividadLeida:
    fila: int
    codigo: str
    fase: str
    nombre: str
    unidad: str
    computo: Decimal
    duracion: Decimal
    unidad_duracion: str
    predecesoras: list[str]
    inicio: date | None
    regla: str = "porcentaje"


@dataclass
class InsumoLeido:
    fila: int
    codigo_actividad: str
    tipo: str  # material | mano_obra | equipo
    descripcion: str
    unidad: str
    rendimiento: Decimal
    precio: Decimal


@dataclass
class ObraLeida:
    nombre: str = ""
    cliente: str = ""
    ubicacion: str = ""
    fecha_inicio: date | None = None
    moneda: str = "Bs"
    parametros: dict[str, Decimal] = field(default_factory=dict)
    clasificacion: dict[str, str] = field(default_factory=dict)
    actividades: list[ActividadLeida] = field(default_factory=list)
    insumos: list[InsumoLeido] = field(default_factory=list)
    base: dict[str, str] = field(default_factory=dict)
    fecha_precios: date | None = None
    contingencia_porcentaje: Decimal = Decimal("0")


@dataclass(frozen=True)
class Problema:
    hoja: str
    fila: int | None
    columna: str
    mensaje: str


@dataclass
class Lectura:
    obra: ObraLeida
    errores: list[Problema]
    advertencias: list[Problema]

    @property
    def valida(self) -> bool:
        return not self.errores


# --- Escribir la plantilla ---


def _ancho(hoja: Worksheet, anchos: list[int]) -> None:
    for i, ancho in enumerate(anchos, 1):
        hoja.column_dimensions[get_column_letter(i)].width = ancho


def _encabezados(hoja: Worksheet, columnas: list[tuple[str, int, str]]) -> None:
    for i, (titulo, _, ayuda) in enumerate(columnas, 1):
        celda = hoja.cell(row=1, column=i, value=titulo)
        celda.font = NEGRITA
        celda.fill = ENCABEZADO
        celda.alignment = Alignment(wrap_text=True, vertical="center")
        if ayuda:
            celda.comment = Comment(ayuda, "Kit TCM")
    hoja.row_dimensions[1].height = 32
    hoja.freeze_panes = "A2"
    _ancho(hoja, [c[1] for c in columnas])


def _pintar(hoja: Worksheet, columnas: int, filas: int, desde: int = 2) -> None:
    for fila in range(desde, desde + filas):
        for col in range(1, columnas + 1):
            hoja.cell(row=fila, column=col).fill = LLENAR


def _lista(hoja: Worksheet, opciones: list[str], rango: str, titulo: str) -> None:
    v = DataValidation(type="list", formula1='"' + ",".join(opciones) + '"', allow_blank=True)
    v.error, v.errorTitle, v.showErrorMessage = f"Elige una opción de la lista: {', '.join(opciones)}", titulo, True
    hoja.add_data_validation(v)
    v.add(rango)


def _numero(hoja: Worksheet, rango: str, minimo: float = 0, maximo: float | None = None, mayor: bool = False) -> None:
    if maximo is None:
        v = DataValidation(
            type="decimal", operator="greaterThan" if mayor else "greaterThanOrEqual", formula1=str(minimo)
        )
    else:
        v = DataValidation(type="decimal", operator="between", formula1=str(minimo), formula2=str(maximo))
    v.error, v.errorTitle, v.showErrorMessage = "Escribe un número válido.", "Número", True
    hoja.add_data_validation(v)
    v.add(rango)


def _fecha(hoja: Worksheet, rango: str) -> None:
    v = DataValidation(type="date", operator="greaterThan", formula1="36526")  # después del 01/01/2000
    v.error, v.errorTitle, v.showErrorMessage = "Escribe una fecha dd/mm/aaaa.", "Fecha", True
    hoja.add_data_validation(v)
    v.add(rango)


def escribir_plantilla(datos: ObraLeida | None = None) -> bytes:
    """Libro .xlsx de la plantilla; si se pasan `datos`, sale lleno con esa obra."""
    d = datos or ObraLeida()
    tabla = cl.tabla()
    libro = Workbook()

    hoja = libro.active
    hoja.title = HOJA_INSTRUCCIONES
    for i, linea in enumerate(INSTRUCCIONES, 1):
        hoja.cell(row=i, column=1, value=linea).font = TITULO if i == 1 else Font()
    leyenda = hoja.cell(row=len(INSTRUCCIONES) + 2, column=1, value="Celda a llenar")
    leyenda.fill = LLENAR
    hoja.column_dimensions["A"].width = 110

    # Datos de obra
    hoja = libro.create_sheet(HOJA_OBRA)
    hoja.append(["Dato", "Valor", "Ayuda"])
    for celda in hoja[1]:
        celda.font, celda.fill = NEGRITA, ENCABEZADO
    valores = {
        "nombre": d.nombre,
        "cliente": d.cliente,
        "ubicacion": d.ubicacion,
        "fecha_inicio": d.fecha_inicio,
        "moneda": d.moneda,
        **{k: (float(v) if v is not None else None) for k, v in d.parametros.items()},
    }
    for fila, (clave, etiqueta, ayuda) in enumerate(CAMPOS_OBRA, 2):
        hoja.cell(row=fila, column=1, value=etiqueta).font = NEGRITA
        celda = hoja.cell(row=fila, column=2, value=valores.get(clave))
        celda.fill = LLENAR
        if clave == "fecha_inicio":
            celda.number_format = "DD/MM/YYYY"
        hoja.cell(row=fila, column=3, value=ayuda).font = GRIS
    fila_moneda = 2 + [c[0] for c in CAMPOS_OBRA].index("moneda")
    _lista(hoja, ["Bs", "USD"], f"B{fila_moneda}", "Moneda")
    _fecha(hoja, f"B{2 + [c[0] for c in CAMPOS_OBRA].index('fecha_inicio')}")
    primera_pct = 2 + [c[0] for c in CAMPOS_OBRA].index(PARAMETROS[0])
    _numero(hoja, f"B{primera_pct}:B{primera_pct + len(PARAMETROS) - 1}", 0, 100)
    _ancho(hoja, [44, 30, 40])

    # Clasificación
    hoja = libro.create_sheet(HOJA_CLASIFICACION)
    hoja.append(["Entregable", "Estado", "Peso (%)", "Clave (no tocar)"])
    for celda in hoja[1]:
        celda.font, celda.fill = NEGRITA, ENCABEZADO
    for fila, e in enumerate(tabla.entregables, 2):
        hoja.cell(row=fila, column=1, value=e.nombre)
        hoja.cell(row=fila, column=2, value=d.clasificacion.get(e.clave, "no")).fill = LLENAR
        hoja.cell(row=fila, column=3, value=float(e.peso))
        hoja.cell(row=fila, column=4, value=e.clave).font = GRIS
    _lista(hoja, list(cl.ESTADOS), f"B2:B{1 + len(tabla.entregables)}", "Estado")
    nota = 3 + len(tabla.entregables)
    hoja.cell(
        row=nota, column=1, value="no = no existe · parcial = preliminar o incompleto · completo = terminado y revisado"
    ).font = GRIS
    _ancho(hoja, [48, 14, 10, 24])

    # Actividades
    hoja = libro.create_sheet(HOJA_ACTIVIDADES)
    _encabezados(hoja, COLUMNAS_ACTIVIDADES)
    _pintar(hoja, len(COLUMNAS_ACTIVIDADES), max(FILAS_DATOS, len(d.actividades) + 50))
    for fila, a in enumerate(d.actividades, 2):
        valores_fila = [
            a.codigo,
            a.fase,
            a.nombre,
            a.unidad,
            float(a.computo),
            float(a.duracion),
            {"dias": "días"}.get(a.unidad_duracion, a.unidad_duracion),
            ", ".join(a.predecesoras),
            a.inicio,
            REGLAS_TEXTO.get(a.regla, "% físico"),
        ]
        for col, valor in enumerate(valores_fila, 1):
            hoja.cell(row=fila, column=col, value=valor)
        hoja.cell(row=fila, column=9).number_format = "DD/MM/YYYY"
    ultima = 1 + max(FILAS_DATOS, len(d.actividades) + 50)
    _numero(hoja, f"E2:E{ultima}", 0, mayor=True)
    _numero(hoja, f"F2:F{ultima}", 0, mayor=True)
    _lista(hoja, ["días", "semanas", "meses"], f"G2:G{ultima}", "Unidad de duración")
    _fecha(hoja, f"I2:I{ultima}")
    _lista(hoja, list(REGLAS_TEXTO.values()), f"J2:J{ultima}", "Regla de medición")

    # APU-Insumos
    hoja = libro.create_sheet(HOJA_INSUMOS)
    _encabezados(hoja, COLUMNAS_INSUMOS)
    _pintar(hoja, len(COLUMNAS_INSUMOS), max(FILAS_DATOS * 3, len(d.insumos) + 100))
    for fila, r in enumerate(d.insumos, 2):
        tipo = {"mano_obra": "Mano de obra", "material": "Material", "equipo": "Equipo"}[r.tipo]
        for col, valor in enumerate(
            [r.codigo_actividad, tipo, r.descripcion, r.unidad, float(r.rendimiento), float(r.precio)], 1
        ):
            hoja.cell(row=fila, column=col, value=valor)
    ultima = 1 + max(FILAS_DATOS * 3, len(d.insumos) + 100)
    _lista(hoja, list(TIPOS_INSUMO.values()), f"B2:B{ultima}", "Tipo")
    _numero(hoja, f"E2:E{ultima}", 0, mayor=True)
    _numero(hoja, f"F2:F{ultima}", 0)

    # Base del estimado
    hoja = libro.create_sheet(HOJA_BASE)
    hoja.append(["Campo", "Contenido", "Clave (no tocar)"])
    for celda in hoja[1]:
        celda.font, celda.fill = NEGRITA, ENCABEZADO
    base = {
        **d.base,
        "fecha_precios": d.fecha_precios,
        "contingencia_porcentaje": float(d.contingencia_porcentaje) if d.base or datos else None,
    }
    for fila, (clave, etiqueta) in enumerate(CAMPOS_BASE, 2):
        hoja.cell(row=fila, column=1, value=etiqueta).font = NEGRITA
        celda = hoja.cell(row=fila, column=2, value=base.get(clave) or None)
        celda.fill = LLENAR
        celda.alignment = Alignment(wrap_text=True, vertical="top")
        if clave == "fecha_precios":
            celda.number_format = "DD/MM/YYYY"
        hoja.cell(row=fila, column=3, value=clave).font = GRIS
        hoja.row_dimensions[fila].height = 45
    _fecha(hoja, f"B{2 + [c[0] for c in CAMPOS_BASE].index('fecha_precios')}")
    _numero(hoja, f"B{2 + [c[0] for c in CAMPOS_BASE].index('contingencia_porcentaje')}", 0, 100)
    _ancho(hoja, [40, 90, 22])

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# --- Leer y validar ---


def _normal(texto: object) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def _texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _decimal(valor: object) -> Decimal | None:
    """Número de Excel o texto con coma o punto decimal. None si está vacío; ValueError si no es número."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, bool):
        raise ValueError
    if isinstance(valor, int | float):
        return Decimal(str(valor))
    texto = str(valor).strip().replace(" ", "").replace("%", "")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise ValueError from None


def _fecha_de(valor: object) -> date | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError


def _fila_vacia(valores: tuple) -> bool:
    return all(v is None or (isinstance(v, str) and not v.strip()) for v in valores)


class _Validador:
    def __init__(self) -> None:
        self.errores: list[Problema] = []
        self.advertencias: list[Problema] = []

    def error(self, hoja: str, fila: int | None, columna: str, mensaje: str) -> None:
        self.errores.append(Problema(hoja, fila, columna, mensaje))

    def aviso(self, hoja: str, fila: int | None, columna: str, mensaje: str) -> None:
        self.advertencias.append(Problema(hoja, fila, columna, mensaje))

    def numero(self, hoja, fila, columna, valor, obligatorio=True, minimo=None, mayor_que=None, maximo=None):
        try:
            numero = _decimal(valor)
        except ValueError:
            self.error(hoja, fila, columna, f"'{valor}' no es un número.")
            return None
        if numero is None:
            if obligatorio:
                self.error(hoja, fila, columna, "Está vacío.")
            return None
        if mayor_que is not None and numero <= mayor_que:
            self.error(hoja, fila, columna, f"Debe ser mayor que {mayor_que}.")
            return None
        if minimo is not None and numero < minimo:
            self.error(hoja, fila, columna, f"No puede ser menor que {minimo}.")
            return None
        if maximo is not None and numero > maximo:
            self.error(hoja, fila, columna, f"No puede ser mayor que {maximo}.")
            return None
        return numero

    def fecha(self, hoja, fila, columna, valor, obligatorio=False):
        try:
            f = _fecha_de(valor)
        except ValueError:
            self.error(hoja, fila, columna, f"'{valor}' no es una fecha (usa dd/mm/aaaa).")
            return None
        if f is None and obligatorio:
            self.error(hoja, fila, columna, "Está vacía.")
        return f


def _leer_obra(hoja: Worksheet, obra: ObraLeida, v: _Validador) -> None:
    etiquetas = {_normal(etiqueta): clave for clave, etiqueta, _ in CAMPOS_OBRA}
    filas: dict[str, tuple[int, object]] = {}
    for fila in hoja.iter_rows(min_row=2, max_col=2):
        clave = etiquetas.get(_normal(fila[0].value))
        if clave:
            filas[clave] = (fila[0].row, fila[1].value)
    for clave, etiqueta, _ in CAMPOS_OBRA:
        if clave not in filas:
            v.error(HOJA_OBRA, None, etiqueta, "No se encontró esta fila: no cambies los textos de la columna A.")
    n, valor = filas.get("nombre", (None, None))
    obra.nombre = _texto(valor)
    if len(obra.nombre) < 2:
        v.error(HOJA_OBRA, n, "Nombre de la obra", "Está vacío o es muy corto.")
    obra.cliente = _texto(filas.get("cliente", (0, None))[1])[:160]
    obra.ubicacion = _texto(filas.get("ubicacion", (0, None))[1])[:200]
    n, valor = filas.get("fecha_inicio", (None, None))
    obra.fecha_inicio = v.fecha(HOJA_OBRA, n, "Fecha de inicio", valor, obligatorio=True)
    n, valor = filas.get("moneda", (None, None))
    moneda = _texto(valor) or "Bs"
    if moneda.lower() not in ("bs", "usd"):
        v.error(HOJA_OBRA, n, "Moneda", "Debe ser Bs o USD.")
    obra.moneda = "USD" if moneda.lower() == "usd" else "Bs"
    for clave in PARAMETROS:
        n, valor = filas.get(clave, (None, None))
        etiqueta = next(e for c, e, _ in CAMPOS_OBRA if c == clave)
        pct = v.numero(HOJA_OBRA, n, etiqueta, valor, obligatorio=False, minimo=0, maximo=100)
        obra.parametros[clave] = pct if pct is not None else Decimal("0")


def _leer_clasificacion(hoja: Worksheet, obra: ObraLeida, v: _Validador) -> None:
    tabla = cl.tabla()
    por_clave = {e.clave: e for e in tabla.entregables}
    por_nombre = {_normal(e.nombre): e.clave for e in tabla.entregables}
    for fila in hoja.iter_rows(min_row=2, max_col=4):
        clave = _texto(fila[3].value) or por_nombre.get(_normal(fila[0].value), "")
        if clave not in por_clave:
            continue
        estado = _normal(fila[1].value) or "no"
        if estado not in cl.ESTADOS:
            v.error(HOJA_CLASIFICACION, fila[0].row, "Estado", "Debe ser no, parcial o completo.")
            continue
        obra.clasificacion[clave] = estado


def _leer_actividades(hoja: Worksheet, obra: ObraLeida, v: _Validador) -> None:
    h = HOJA_ACTIVIDADES
    codigos: dict[str, int] = {}
    for fila in hoja.iter_rows(min_row=2, max_col=len(COLUMNAS_ACTIVIDADES), values_only=False):
        valores = tuple(c.value for c in fila)
        if _fila_vacia(valores):
            continue
        n = fila[0].row
        codigo, fase, nombre, unidad = (_texto(x) for x in valores[:4])
        for texto, columna in ((codigo, "Código"), (fase, "Fase"), (nombre, "Actividad"), (unidad, "Unidad")):
            if not texto:
                v.error(h, n, columna, "Está vacío.")
        if codigo in codigos:
            v.error(h, n, "Código", f"El código {codigo} está repetido (ya está en la fila {codigos[codigo]}).")
        elif codigo:
            codigos[codigo] = n
        computo = v.numero(h, n, "Cómputo", valores[4], mayor_que=0)
        duracion = v.numero(h, n, "Duración", valores[5], mayor_que=0, maximo=3650)
        unidad_dur = UNIDADES_DURACION.get(_normal(valores[6]))
        if unidad_dur is None:
            v.error(h, n, "Unidad de duración", "Debe ser días, semanas o meses.")
        elif duracion is not None and cr.a_dias(duracion, unidad_dur) > 3650:
            v.error(h, n, "Duración", "La duración no puede pasar de 10 años.")
        predecesoras = [p.strip() for p in _texto(valores[7]).replace(";", ",").split(",") if p.strip()]
        inicio = v.fecha(h, n, "Inicio fijo", valores[8])
        if inicio and predecesoras:
            v.aviso(h, n, "Inicio fijo", "Tiene predecesoras: el inicio fijo se ignora.")
        if obra.fecha_inicio and inicio and inicio < obra.fecha_inicio:
            v.error(h, n, "Inicio fijo", "Fecha incoherente: es anterior al inicio de la obra.")
        if len(nombre) > 160 or len(codigo) > 20 or len(unidad) > 20 or len(fase) > 120:
            v.error(h, n, "Texto", "Algún texto es demasiado largo.")
        regla = REGLA_DE_TEXTO.get(_normal(valores[9]).replace(" ", "")) if _texto(valores[9]) else "porcentaje"
        if regla is None:
            v.error(h, n, "Regla de medición", "Debe ser % físico, 0/100 o 50/50.")
        if codigo and computo is not None and duracion is not None and unidad_dur and regla:
            obra.actividades.append(
                ActividadLeida(
                    n, codigo, fase, nombre, unidad, computo, duracion, unidad_dur, predecesoras, inicio, regla
                )
            )
    if not obra.actividades and not any(e.hoja == h for e in v.errores):
        v.error(h, None, "", "No hay actividades cargadas.")


def _leer_insumos(hoja: Worksheet, obra: ObraLeida, v: _Validador) -> None:
    h = HOJA_INSUMOS
    for fila in hoja.iter_rows(min_row=2, max_col=len(COLUMNAS_INSUMOS)):
        valores = tuple(c.value for c in fila)
        if _fila_vacia(valores):
            continue
        n = fila[0].row
        codigo, tipo_texto, descripcion, unidad = (_texto(x) for x in valores[:4])
        if not codigo:
            v.error(h, n, "Código de actividad", "Está vacío.")
        tipo = CLAVE_TIPO.get(_normal(tipo_texto))
        if tipo is None:
            v.error(h, n, "Tipo", "Debe ser Material, Mano de obra o Equipo.")
        if not descripcion:
            v.error(h, n, "Insumo", "Está vacío.")
        if not unidad:
            v.error(h, n, "Unidad", "Está vacía.")
        rendimiento = v.numero(h, n, "Cantidad por unidad", valores[4], mayor_que=0)
        precio = v.numero(h, n, "Precio unitario", valores[5], minimo=0)
        if len(descripcion) > 160 or len(unidad) > 20:
            v.error(h, n, "Texto", "Algún texto es demasiado largo.")
        if codigo and tipo and descripcion and rendimiento is not None and precio is not None:
            obra.insumos.append(InsumoLeido(n, codigo, tipo, descripcion, unidad, rendimiento, precio))


def _leer_base(hoja: Worksheet, obra: ObraLeida, v: _Validador) -> None:
    por_etiqueta = {_normal(e): c for c, e in CAMPOS_BASE}
    claves = {c for c, _ in CAMPOS_BASE}
    for fila in hoja.iter_rows(min_row=2, max_col=3):
        clave = _texto(fila[2].value)
        if clave not in claves:
            clave = por_etiqueta.get(_normal(fila[0].value), "")
        if not clave:
            continue
        n, valor = fila[0].row, fila[1].value
        if clave == "fecha_precios":
            obra.fecha_precios = v.fecha(HOJA_BASE, n, "Fecha de los precios", valor)
        elif clave == "contingencia_porcentaje":
            pct = v.numero(HOJA_BASE, n, "Contingencia", valor, obligatorio=False, minimo=0, maximo=100)
            obra.contingencia_porcentaje = pct or Decimal("0")
        else:
            obra.base[clave] = _texto(valor)


def _validar_relaciones(obra: ObraLeida, v: _Validador) -> None:
    codigos = {a.codigo: a for a in obra.actividades}
    for a in obra.actividades:
        for p in a.predecesoras:
            if p == a.codigo:
                v.error(HOJA_ACTIVIDADES, a.fila, "Predecesoras", "Una actividad no puede ser predecesora de sí misma.")
            elif p not in codigos:
                v.error(HOJA_ACTIVIDADES, a.fila, "Predecesoras", f"No existe la actividad con código {p}.")
    numero = {c: i for i, c in enumerate(codigos, 1)}
    try:
        cr.orden_topologico(
            [
                cr.DatosActividad(
                    numero[a.codigo],
                    1,
                    predecesoras=tuple(cr.Enlace(numero[p]) for p in a.predecesoras if p in numero and p != a.codigo),
                )
                for a in obra.actividades
            ]
        )
    except cr.DependenciaCircular as e:
        nombres = {i: c for c, i in numero.items()}
        recorrido = " → ".join(nombres[i] for i in e.ciclo + e.ciclo[:1])
        fila = codigos[nombres[e.ciclo[0]]].fila
        v.error(HOJA_ACTIVIDADES, fila, "Predecesoras", f"Dependencia circular: {recorrido}.")

    costo: dict[str, Decimal] = {}
    for r in obra.insumos:
        if r.codigo_actividad not in codigos:
            v.error(HOJA_INSUMOS, r.fila, "Código de actividad", f"No existe la actividad {r.codigo_actividad}.")
            continue
        costo[r.codigo_actividad] = costo.get(r.codigo_actividad, Decimal("0")) + r.rendimiento * r.precio
    for a in obra.actividades:
        if costo.get(a.codigo, Decimal("0")) <= 0:
            v.error(
                HOJA_ACTIVIDADES,
                a.fila,
                "Costo",
                f"La actividad {a.codigo} no tiene costo: agrégale insumos con precio.",
            )

    if obra.fecha_precios and obra.fecha_inicio and (obra.fecha_inicio - obra.fecha_precios).days > 180:
        v.aviso(
            HOJA_BASE, None, "Fecha de los precios", "Los precios tienen más de 6 meses respecto al inicio de la obra."
        )
    if obra.fecha_precios and obra.fecha_inicio and obra.fecha_precios > obra.fecha_inicio:
        v.aviso(HOJA_BASE, None, "Fecha de los precios", "La fecha de los precios es posterior al inicio de la obra.")


def leer_plantilla(contenido: bytes) -> Lectura:
    v = _Validador()
    obra = ObraLeida()
    try:
        libro = load_workbook(BytesIO(contenido), data_only=True, read_only=False)
    except Exception:  # openpyxl lanza varios tipos según el daño del archivo
        v.error("", None, "", "El archivo no es un Excel .xlsx válido.")
        return Lectura(obra, v.errores, v.advertencias)
    hojas = {_normal(n): libro[n] for n in libro.sheetnames}

    def hoja(nombre: str) -> Worksheet | None:
        encontrada = hojas.get(_normal(nombre))
        if encontrada is None:
            v.error(nombre, None, "", f"Falta la hoja '{nombre}'. Usa la plantilla del kit sin cambiar los nombres.")
        return encontrada

    if (h := hoja(HOJA_OBRA)) is not None:
        _leer_obra(h, obra, v)
    if (h := hoja(HOJA_CLASIFICACION)) is not None:
        _leer_clasificacion(h, obra, v)
    if (h := hoja(HOJA_ACTIVIDADES)) is not None:
        _leer_actividades(h, obra, v)
    if (h := hoja(HOJA_INSUMOS)) is not None:
        _leer_insumos(h, obra, v)
    if (h := hoja(HOJA_BASE)) is not None:
        _leer_base(h, obra, v)
    _validar_relaciones(obra, v)
    return Lectura(obra, v.errores, v.advertencias)
