"""Hoja de registro de la prueba de uso del kit (usabilidad, no impacto): tiempos, errores por tipo, SUS y comentarios.

Una hoja por participante (P1–P3) y un Resumen con fórmulas, para llenar durante la prueba en una laptop.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

LLENAR = PatternFill("solid", fgColor="FFF4CC")
ENCABEZADO = PatternFill("solid", fgColor="E7E5E4")
NEGRITA = Font(bold=True)
TITULO = Font(bold=True, size=14)
GRIS = Font(color="78716C", italic=True)
PARTICIPANTES = 3

# (n°, tarea tal como se lee, se completa cuando…, meta en minutos). Máximo = 2 × meta.
TAREAS = [
    (1, "Carga la obra desde el archivo obra-pyme.xlsx del escritorio.", "La obra aparece en Mis obras", 4),
    (
        2,
        "Esta obra ya tiene planos estructurales completos. Actualiza la clasificación y dime qué clase de estimado es "
        "y entre qué montos puede terminar.",
        "Dice la clase y el rango correctos",
        3,
    ),
    (
        3,
        "Aprueba la línea base del presupuesto y dime cuánto dinero debería estar ejecutado al final de la semana 8.",
        "Dice el PV acumulado de la semana 8",
        3,
    ),
    (
        4,
        "Registra que la excavación de cimientos está al 100 % y que se gastaron Bs 2.000 en ella. Luego dime si la "
        "obra va bien de costo y cuánto costará al final.",
        "Lee CPI, SPI y EAC y los interpreta",
        5,
    ),
    (
        5,
        "Registra el riesgo 'suba del precio del fierro' y un cambio pedido por el cliente: "
        "'agregar un baño de visitas'.",
        "Ambos quedan guardados",
        5,
    ),
]
TIPOS_ERROR = [
    ("D", "Dato mal cargado"),
    ("P", "Paso omitido"),
    ("A", "Pidió ayuda"),
    ("S", "Error del sistema"),
]
SUS = [
    "Creo que me gustaría usar este sistema con frecuencia.",
    "El sistema me pareció innecesariamente complejo.",
    "El sistema me pareció fácil de usar.",
    "Creo que necesitaría ayuda de una persona técnica para poder usar este sistema.",
    "Las distintas funciones del sistema están bien integradas.",
    "El sistema me pareció demasiado inconsistente.",
    "Imagino que la mayoría de las personas aprendería a usar este sistema muy rápido.",
    "El sistema me pareció muy engorroso de usar.",
    "Me sentí muy seguro(a) usando el sistema.",
    "Tuve que aprender muchas cosas antes de poder usar el sistema.",
]
PREGUNTAS = [
    "¿Qué fue lo más difícil o confuso? ¿En qué tarea?",
    "¿Qué parte te sería más útil en tus obras reales? ¿Cuál no usarías?",
    "¿La plantilla Excel se parece a cómo presupuestas hoy? ¿Qué le cambiarías?",
    "¿Se entendió qué es la clase del estimado y la línea base? ¿Cómo lo explicarías a un colega?",
    "¿Pagarías por algo así o lo usarías si fuera gratis? ¿Qué le falta para que lo uses?",
]
PERFIL = [
    "Código del participante",
    "Cargo",
    "Años de experiencia en obra",
    "Cómo presupuesta hoy (Excel propio, programa, a mano)",
    "Conoce valor ganado (sí / de oído / no)",
    "Fecha de la prueba",
    "Moderador",
    "Observador",
]

# Filas fijas de cada hoja de participante (las usa el Resumen).
FILA_TAREAS = 13  # encabezado; tareas en 14–18
FILA_SUS = 22  # encabezado; frases en 23–32; puntaje en 33


def _encabezado(hoja: Worksheet, fila: int, titulos: list[str]) -> None:
    for col, t in enumerate(titulos, 1):
        c = hoja.cell(row=fila, column=col, value=t)
        c.font, c.fill = NEGRITA, ENCABEZADO
        c.alignment = Alignment(wrap_text=True, vertical="center")


def _lista(hoja: Worksheet, opciones: list[str], rango: str) -> None:
    v = DataValidation(type="list", formula1='"' + ",".join(opciones) + '"', allow_blank=True)
    v.error, v.showErrorMessage = f"Elige: {', '.join(opciones)}", True
    hoja.add_data_validation(v)
    v.add(rango)


def _hoja_participante(libro: Workbook, numero: int) -> None:
    h = libro.create_sheet(f"P{numero}")
    h["A1"], h["A1"].font = f"Participante P{numero}", TITULO
    for i, campo in enumerate(PERFIL, 3):
        h.cell(row=i, column=1, value=campo).font = NEGRITA
        h.cell(row=i, column=2).fill = LLENAR
    h.cell(row=3, column=2, value=f"P{numero}")
    h.cell(row=8, column=2).number_format = "DD/MM/YYYY"

    _encabezado(
        h,
        FILA_TAREAS,
        ["N°", "Tarea", "Meta (min)", "Máx. (min)", "Inicio (hh:mm)", "Fin (hh:mm)", "Tiempo (min)", "¿Completó?"]
        + [f"{c} · {n}" for c, n in TIPOS_ERROR]
        + ["Dentro de la meta", "Observaciones (qué hizo, dónde dudó, qué dijo)"],
    )
    for i, (n, tarea, _, meta) in enumerate(TAREAS):
        f = FILA_TAREAS + 1 + i
        h.cell(row=f, column=1, value=n)
        h.cell(row=f, column=2, value=tarea).alignment = Alignment(wrap_text=True, vertical="top")
        h.cell(row=f, column=3, value=meta)
        h.cell(row=f, column=4, value=meta * 2)
        for col in (5, 6):
            c = h.cell(row=f, column=col)
            c.fill, c.number_format = LLENAR, "hh:mm"
        h.cell(row=f, column=7, value=f'=IF(OR(E{f}="",F{f}=""),"",ROUND((F{f}-E{f})*24*60,1))').number_format = "0.0"
        for col in range(8, 13):
            h.cell(row=f, column=col).fill = LLENAR
        h.cell(row=f, column=14).fill = LLENAR
        h.cell(row=f, column=13, value=f'=IF(G{f}="","",IF(G{f}<=C{f},"Sí","No"))')
        h.row_dimensions[f].height = 48
    ultima = FILA_TAREAS + len(TAREAS)
    _lista(h, ["Sí", "Con ayuda", "No"], f"H{FILA_TAREAS + 1}:H{ultima}")
    v = DataValidation(type="whole", operator="between", formula1="0", formula2="50")
    v.error, v.showErrorMessage = "Cantidad de errores (0 a 50).", True
    h.add_data_validation(v)
    v.add(f"I{FILA_TAREAS + 1}:L{ultima}")
    total = ultima + 1
    h.cell(row=total, column=2, value="TOTAL").font = NEGRITA
    h.cell(row=total, column=7, value=f"=SUM(G{FILA_TAREAS + 1}:G{ultima})").font = NEGRITA
    for col in "IJKL":
        h[f"{col}{total}"] = f"=SUM({col}{FILA_TAREAS + 1}:{col}{ultima})"
        h[f"{col}{total}"].font = NEGRITA

    _encabezado(h, FILA_SUS, ["N°", "Afirmación (SUS)", "Respuesta 1–5", "Aporte"])
    for i, frase in enumerate(SUS, 1):
        f = FILA_SUS + i
        h.cell(row=f, column=1, value=i)
        h.cell(row=f, column=2, value=frase)
        h.cell(row=f, column=3).fill = LLENAR
        # Impares: respuesta − 1. Pares: 5 − respuesta.
        aporte = f"C{f}-1" if i % 2 else f"5-C{f}"
        h.cell(row=f, column=4, value=f'=IF(C{f}="","",{aporte})')
    v = DataValidation(type="whole", operator="between", formula1="1", formula2="5")
    v.error, v.showErrorMessage = "Del 1 (totalmente en desacuerdo) al 5 (totalmente de acuerdo).", True
    h.add_data_validation(v)
    v.add(f"C{FILA_SUS + 1}:C{FILA_SUS + 10}")
    puntaje = FILA_SUS + 11
    h.cell(row=puntaje, column=2, value="Puntaje SUS (0–100)").font = NEGRITA
    rango = f"C{FILA_SUS + 1}:C{FILA_SUS + 10}"
    h.cell(
        row=puntaje, column=4, value=f'=IF(COUNT({rango})<10,"",SUM(D{FILA_SUS + 1}:D{FILA_SUS + 10})*2.5)'
    ).font = NEGRITA
    h.cell(row=puntaje + 1, column=2, value="1 = totalmente en desacuerdo · 5 = totalmente de acuerdo").font = GRIS

    inicio = puntaje + 3
    _encabezado(h, inicio, ["N°", "Pregunta abierta", "Respuesta"])
    for i, p in enumerate(PREGUNTAS, 1):
        f = inicio + i
        h.cell(row=f, column=1, value=i)
        h.cell(row=f, column=2, value=p).alignment = Alignment(wrap_text=True, vertical="top")
        c = h.cell(row=f, column=3)
        c.fill, c.alignment = LLENAR, Alignment(wrap_text=True, vertical="top")
        h.row_dimensions[f].height = 45
    h.merge_cells(start_row=inicio, start_column=3, end_row=inicio, end_column=14)
    for f in range(inicio + 1, inicio + len(PREGUNTAS) + 1):
        h.merge_cells(start_row=f, start_column=3, end_row=f, end_column=14)

    for col, ancho in zip("ABCDEFGHIJKLMN", (24, 60, 11, 11, 11, 11, 11, 12, 9, 9, 9, 9, 11, 50), strict=True):
        h.column_dimensions[col].width = ancho
    h.freeze_panes = "A3"


def _resumen(libro: Workbook) -> None:
    h = libro.create_sheet("Resumen", 1)
    h["A1"], h["A1"].font = "Resumen de la prueba de uso", TITULO
    h["A2"] = "Mide usabilidad (tiempo, errores, satisfacción), no el impacto en los costos de la empresa."
    h["A2"].font = GRIS
    hojas = [f"P{i}" for i in range(1, PARTICIPANTES + 1)]
    _encabezado(
        h,
        4,
        [
            "N°",
            "Tarea",
            "Meta (min)",
            "Tiempo medio (min)",
            "Dentro de la meta",
            "Completadas sin ayuda",
            "Con ayuda",
            "No",
        ]
        + [f"{c} · {n}" for c, n in TIPOS_ERROR],
    )
    for i, (n, tarea, _, meta) in enumerate(TAREAS):
        f = 5 + i
        fila = FILA_TAREAS + 1 + i
        h.cell(row=f, column=1, value=n)
        h.cell(row=f, column=2, value=tarea[:70] + ("…" if len(tarea) > 70 else ""))
        h.cell(row=f, column=3, value=meta)
        tiempos = ",".join(f"'{p}'!G{fila}" for p in hojas)
        h.cell(row=f, column=4, value=f'=IFERROR(ROUND(AVERAGE({tiempos}),1),"")')
        h.cell(row=f, column=5, value="=" + "+".join(f"COUNTIF('{p}'!M{fila},\"Sí\")" for p in hojas))
        for col, valor in ((6, "Sí"), (7, "Con ayuda"), (8, "No")):
            h.cell(row=f, column=col, value="=" + "+".join(f"COUNTIF('{p}'!H{fila},\"{valor}\")" for p in hojas))
        for j, letra in enumerate("IJKL"):
            h.cell(row=f, column=9 + j, value="=" + "+".join(f"N('{p}'!{letra}{fila})" for p in hojas))
    total = 5 + len(TAREAS)
    h.cell(row=total, column=2, value="TOTAL").font = NEGRITA
    for col in "FGHIJKL":
        h[f"{col}{total}"] = f"=SUM({col}5:{col}{total - 1})"
        h[f"{col}{total}"].font = NEGRITA

    f = total + 2
    _encabezado(h, f, ["Participante", "Puntaje SUS"])
    celda_sus = f"D{FILA_SUS + 11}"
    for i, p in enumerate(hojas, 1):
        h.cell(row=f + i, column=1, value=p)
        h.cell(row=f + i, column=2, value=f"='{p}'!{celda_sus}")
    media = f + len(hojas) + 1
    h.cell(row=media, column=1, value="Promedio SUS").font = NEGRITA
    h.cell(row=media, column=2, value=f'=IFERROR(ROUND(AVERAGE(B{f + 1}:B{f + len(hojas)}),1),"")').font = NEGRITA
    h.cell(row=media + 1, column=1, value="Referencia: 68 = promedio; más de 80 = bueno.").font = GRIS
    for col, ancho in zip("ABCDEFGHIJKL", (14, 60, 11, 14, 12, 14, 11, 8, 10, 10, 10, 10), strict=True):
        h.column_dimensions[col].width = ancho


def escribir_hoja_prueba() -> bytes:
    libro = Workbook()
    h = libro.active
    h.title = "Instrucciones"
    lineas = [
        "Hoja de registro — Prueba de uso del Kit TCM",
        "",
        "1. Una hoja por participante (P1, P2, P3). Llena solo las celdas amarillas.",
        "2. Tareas: anota la hora de inicio y fin (hh:mm); el tiempo y si quedó dentro de la meta se calculan solos.",
        "   Si pasa el tiempo máximo, detén la tarea y marca ¿Completó? = No.",
        "3. Errores: cuenta cuántas veces ocurre cada tipo en la tarea:",
        "   D = dato mal cargado · P = paso omitido · A = pidió ayuda · S = error del sistema.",
        "4. SUS: el participante responde del 1 al 5; el puntaje (0–100) se calcula solo.",
        "5. Preguntas abiertas: anota las respuestas con sus palabras.",
        "6. La hoja Resumen junta a todos los participantes: tiempo medio frente a la meta, éxito, errores y SUS.",
        "",
        "Esta prueba mide USABILIDAD (tiempo, errores, satisfacción). No mide el impacto en los costos de la pyme.",
    ]
    for i, linea in enumerate(lineas, 1):
        h.cell(row=i, column=1, value=linea).font = TITULO if i == 1 else Font()
    h.column_dimensions["A"].width = 110
    for n in range(1, PARTICIPANTES + 1):
        _hoja_participante(libro, n)
    _resumen(libro)
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
