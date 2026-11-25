"""Exportar a Excel el estimado de una obra: clase, APU, base del estimado, línea base, PV semanal y curva S."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from app import servicios
from app.calculos import valor_ganado as vg
from app.modelos import LineaBase, Obra
from app.tcm import clasificacion as cl
from app.tcm import servicio as ts

NEGRITA = Font(bold=True)
TITULO = Font(bold=True, size=14)
ENCABEZADO = PatternFill("solid", fgColor="E7E5E4")
DINERO = "#,##0.00"
FECHA = "DD/MM/YYYY"


def _encabezado(hoja: Worksheet, titulos: list[str], anchos: list[int], fila: int = 1) -> None:
    for i, (t, ancho) in enumerate(zip(titulos, anchos, strict=True), 1):
        celda = hoja.cell(row=fila, column=i, value=t)
        celda.font, celda.fill = NEGRITA, ENCABEZADO
        celda.alignment = Alignment(wrap_text=True, vertical="center")
        hoja.column_dimensions[get_column_letter(i)].width = ancho
    hoja.freeze_panes = hoja.cell(row=fila + 1, column=1)


def _formato(hoja: Worksheet, columnas: str, formato: str, desde: int = 2) -> None:
    for col in columnas:
        for celda in hoja[col][desde - 1 :]:
            celda.number_format = formato


def exportar_estimado(sesion: Session, obra: Obra, base: LineaBase | None, registros: tuple | None = None) -> bytes:
    """`registros` = (riesgos, cambios, versión de línea base por cambio) para agregar sus hojas."""
    est = ts.estimado(sesion, obra)
    resultado = ts.clasificar(sesion, obra, est.total)
    tabla = cl.tabla()
    lista = ts.checklist(sesion, obra.id)
    libro = Workbook()

    # Resumen y clasificación
    hoja = libro.active
    hoja.title = "Resumen"
    hoja["A1"], hoja["A1"].font = f"Estimado — {obra.nombre}", TITULO
    filas = [
        ("Cliente", obra.cliente),
        ("Ubicación", obra.ubicacion),
        ("Moneda", obra.moneda),
        ("Inicio", obra.fecha_inicio),
        ("Fin según cronograma", obra.fecha_fin),
        ("Total del estimado (precio)", float(est.total)),
        ("", ""),
        ("Clasificación del estimado (AACE 56R-08 / 17R-97)", ""),
        ("% de definición del proyecto", float(resultado.porcentaje_definicion) / 100),
        ("Clase", resultado.clase.clase),
        ("Rango de madurez según la norma", resultado.clase.definicion_norma),
        ("Uso típico", resultado.clase.uso),
        ("Metodología típica", resultado.clase.metodologia),
        (
            "Exactitud",
            f"{resultado.clase.exactitud_baja[0]} % a {resultado.clase.exactitud_baja[1]} % / "
            f"+{resultado.clase.exactitud_alta[0]} % a +{resultado.clase.exactitud_alta[1]} %",
        ),
        ("Total mínimo probable", float(resultado.minimo) if resultado.minimo is not None else None),
        ("Total máximo probable", float(resultado.maximo) if resultado.maximo is not None else None),
        ("", ""),
        ("Línea base vigente", f"Versión {base.version}" if base else "Sin aprobar"),
        ("Aprobada el", base.aprobada_en.date() if base else None),
        ("BAC de la línea base", float(base.bac) if base else None),
    ]
    for i, (etiqueta, valor) in enumerate(filas, 3):
        hoja.cell(row=i, column=1, value=etiqueta).font = NEGRITA
        celda = hoja.cell(row=i, column=2, value=valor)
        if isinstance(valor, float):
            celda.number_format = "0.0 %" if etiqueta.startswith("%") else DINERO
        elif etiqueta in ("Inicio", "Fin según cronograma", "Aprobada el"):
            celda.number_format = FECHA
    fila = len(filas) + 5
    hoja.cell(row=fila, column=1, value="Entregable").font = NEGRITA
    hoja.cell(row=fila, column=2, value="Estado").font = NEGRITA
    hoja.cell(row=fila, column=3, value="Peso (%)").font = NEGRITA
    for e in tabla.entregables:
        fila += 1
        hoja.cell(row=fila, column=1, value=e.nombre)
        hoja.cell(row=fila, column=2, value=lista.get(e.clave, "no"))
        hoja.cell(row=fila, column=3, value=float(e.peso))
    hoja.column_dimensions["A"].width = 48
    hoja.column_dimensions["B"].width = 60

    # Estimado por actividad (APU resumido)
    hoja = libro.create_sheet("Estimado APU")
    titulos = [
        "Código", "Fase", "Actividad", "Unidad", "Cómputo", "Materiales", "Mano de obra", "Cargas sociales",
        "IVA m. de obra", "Equipo", "Herramientas", "Costo directo", "Gastos generales", "Utilidad",
        "Impuestos", "Total", "Precio unitario",
    ]  # fmt: skip
    _encabezado(hoja, titulos, [9, 20, 36, 8, 10] + [13] * 12)
    for f in est.fases:
        for a in f.actividades:
            apu, act = a.apu, a.actividad
            hoja.append(
                [
                    act.codigo, f.fase.nombre, act.nombre, act.unidad,
                    float(act.computo) if act.computo is not None else None,
                    float(apu.materiales), float(apu.mano_obra), float(apu.cargas_sociales),
                    float(apu.iva_mano_obra), float(apu.equipo), float(apu.herramientas),
                    float(apu.costo_directo), float(apu.gastos_generales), float(apu.utilidad),
                    float(apu.impuestos), float(apu.total),
                    float(a.precio_unitario) if a.precio_unitario is not None else None,
                ]
            )  # fmt: skip
    ultima = hoja.max_row
    total = ultima + 1
    hoja.cell(row=total, column=3, value="TOTAL").font = NEGRITA
    for col in range(6, 17):
        letra = get_column_letter(col)
        hoja.cell(row=total, column=col, value=f"=SUM({letra}2:{letra}{ultima})").font = NEGRITA
    _formato(hoja, "FGHIJKLMNOPQ", DINERO)
    p = est.parametros
    nota = total + 2
    hoja.cell(row=nota, column=1, value="Porcentajes del APU").font = NEGRITA
    for i, (etiqueta, valor) in enumerate(
        [
            ("Cargas sociales (% m. de obra)", p.cargas_sociales),
            ("IVA de la mano de obra (%)", p.iva_mano_obra),
            ("Herramientas menores (% m. de obra)", p.herramientas),
            ("Gastos generales (% costo directo)", p.gastos_generales),
            ("Utilidad (%)", p.utilidad),
            ("Impuestos IT (%)", p.impuestos),
        ],
        nota + 1,
    ):
        hoja.cell(row=i, column=1, value=etiqueta)
        hoja.cell(row=i, column=5, value=float(valor))

    # Insumos
    hoja = libro.create_sheet("Insumos")
    _encabezado(
        hoja,
        [
            "Código",
            "Actividad",
            "Tipo",
            "Insumo",
            "Unidad",
            "Por unidad",
            "Cantidad total",
            "Precio unitario",
            "Parcial",
        ],
        [9, 36, 13, 30, 9, 11, 13, 13, 13],
    )
    tipos = {"mano_obra": "Mano de obra", "material": "Material", "equipo": "Equipo"}
    for a in est.actividades:
        for r in a.recursos:
            n = hoja.max_row + 1
            hoja.append(
                [
                    a.actividad.codigo, a.actividad.nombre, tipos.get(r.tipo, r.tipo), r.descripcion, r.unidad,
                    float(r.rendimiento) if r.rendimiento is not None else None, float(r.cantidad),
                    float(r.precio_unitario), f"=G{n}*H{n}",
                ]
            )  # fmt: skip
    _formato(hoja, "HI", DINERO)

    # Base del estimado
    hoja = libro.create_sheet("Base del estimado")
    hoja["A1"], hoja["A1"].font = "Base del estimado (AACE 34R-05)", TITULO
    b = ts.base_del_estimado(sesion, obra.id)
    contenido = [(etiqueta, getattr(b, campo)) for campo, etiqueta in ts.CAMPOS_BASE.items()]
    contenido.insert(6, ("Fecha de los precios", b.fecha_precios))
    contenido.append(("Contingencia (% del estimado)", float(b.contingencia_porcentaje)))
    contenido.append(("Contingencia (monto)", float(est.total * b.contingencia_porcentaje / 100)))
    for i, (etiqueta, valor) in enumerate(contenido, 3):
        hoja.cell(row=i, column=1, value=etiqueta).font = NEGRITA
        celda = hoja.cell(row=i, column=2, value=valor)
        celda.alignment = Alignment(wrap_text=True, vertical="top")
        if etiqueta == "Fecha de los precios":
            celda.number_format = FECHA
        elif etiqueta == "Contingencia (monto)":
            celda.number_format = DINERO
    hoja.column_dimensions["A"].width = 40
    hoja.column_dimensions["B"].width = 100

    if base is not None:
        # Línea base
        hoja = libro.create_sheet("Línea base")
        hoja["A1"] = (
            f"Línea base v{base.version} — aprobada el {base.aprobada_en:%d/%m/%Y}. Motivo: {base.motivo or '—'}"
        )
        hoja["A1"].font = NEGRITA
        _encabezado(hoja, ["Código", "Partida", "Fase", "Inicio", "Fin", "Presupuesto"], [9, 36, 20, 12, 12, 14], 3)
        for lp in base.partidas:
            hoja.append([lp.codigo, lp.nombre, lp.fase, lp.fecha_inicio, lp.fecha_fin, float(lp.presupuesto)])
        ultima = hoja.max_row
        hoja.cell(row=ultima + 1, column=2, value="BAC").font = NEGRITA
        hoja.cell(row=ultima + 1, column=6, value=f"=SUM(F4:F{ultima})").font = NEGRITA
        _formato(hoja, "DE", FECHA, 4)
        _formato(hoja, "F", DINERO, 4)

        # PV semanal y curva S
        hoja = libro.create_sheet("PV semanal")
        _encabezado(
            hoja,
            ["Semana", "Desde", "Hasta", "PV de la semana", "PV acumulado", "% acumulado"],
            [9, 12, 12, 15, 15, 12],
        )
        semanas = ts.pv_semanal(base)
        for s in semanas:
            hoja.append(
                [
                    s.numero, s.inicio, s.fin, float(s.pv), float(s.pv_acumulado),
                    float(s.porcentaje_acumulado) / 100 if s.porcentaje_acumulado is not None else None,
                ]
            )  # fmt: skip
        _formato(hoja, "BC", FECHA)
        _formato(hoja, "DE", DINERO)
        _formato(hoja, "F", "0.0 %")
        if semanas:
            grafico = LineChart()
            grafico.title = f"Curva S — línea base v{base.version}"
            grafico.y_axis.title = f"PV acumulado ({obra.moneda})"
            grafico.x_axis.title = "Semana"
            grafico.height, grafico.width = 9, 18
            grafico.add_data(Reference(hoja, min_col=5, min_row=1, max_row=len(semanas) + 1), titles_from_data=True)
            grafico.set_categories(Reference(hoja, min_col=1, min_row=2, max_row=len(semanas) + 1))
            hoja.add_chart(grafico, "H2")

    _hoja_valor_ganado(libro, sesion, obra, base)
    if registros is not None:
        from app.tcm import registros_excel

        registros_excel.agregar_hojas(libro, *registros)

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _hoja_valor_ganado(libro: Workbook, sesion: Session, obra: Obra, base: LineaBase | None) -> None:
    """Valor ganado (82R-13) a hoy, pronósticos (80R-13) y curva S con PV, EV y AC."""
    from app.tcm import pronostico as pr

    hoy = servicios.hoy()
    datos, resultado = servicios.calcular(sesion, obra, hoy)
    i = resultado.indicadores
    hoja = libro.create_sheet("Valor ganado")
    hoja["A1"], hoja["A1"].font = f"Valor ganado al {hoy:%d/%m/%Y}", TITULO
    hoja["A2"] = (
        f"Medido contra la línea base v{base.version}" if base else "Sin línea base aprobada: mide contra el plan"
    )
    filas = [
        ("BAC (presupuesto a la conclusión)", "BAC", i.bac),
        ("PV (valor planificado)", "BCWS", i.pv),
        ("EV (valor ganado)", "BCWP", i.ev),
        ("AC (costo real)", "ACWP", i.ac),
        ("CV = EV − AC", "", i.cv),
        ("SV = EV − PV", "", i.sv),
        ("CPI = EV / AC", "", i.cpi),
        ("SPI = EV / PV", "", i.spi),
        ("TCPI = (BAC − EV) / (BAC − AC)", "", pr.tcpi(i)),
    ]
    _encabezado(hoja, ["Indicador (AACE 82R-13)", "Equivalencia", "Valor"], [40, 14, 16], 4)
    for n, (nombre, equivalente, valor) in enumerate(filas, 5):
        hoja.cell(row=n, column=1, value=nombre)
        hoja.cell(row=n, column=2, value=equivalente)
        celda = hoja.cell(row=n, column=3, value=None if valor is None else float(valor))
        celda.number_format = "0.000" if nombre.split()[0] in ("CPI", "SPI", "TCPI") else DINERO
    fila = 5 + len(filas) + 1
    for col, titulo in enumerate(["Pronóstico (AACE 80R-13)", "Fórmula", "EAC", "ETC", "VAC", "Supuesto"], 1):
        celda = hoja.cell(row=fila, column=col, value=titulo)
        celda.font, celda.fill = NEGRITA, ENCABEZADO
    for p in pr.pronosticos(i):
        fila += 1
        valores = [p.nombre, p.formula, p.eac, p.etc, p.vac, p.supuesto]
        for col, valor in enumerate(valores, 1):
            celda = hoja.cell(
                row=fila, column=col, value=float(valor) if col in (3, 4, 5) and valor is not None else valor
            )
            if col in (3, 4, 5):
                celda.number_format = DINERO
    for col, ancho in zip("DEF", (16, 16, 70), strict=True):
        hoja.column_dimensions[col].width = ancho

    puntos = vg.calcular_curva([d for _, d in datos], servicios.fechas_curva(obra, hoy), hoy)
    if len(puntos) < 2:
        return
    inicio = fila + 3
    for col, titulo in enumerate(["Fecha", "PV", "EV", "AC"], 1):
        celda = hoja.cell(row=inicio, column=col, value=titulo)
        celda.font, celda.fill = NEGRITA, ENCABEZADO
    for n, pt in enumerate(puntos, inicio + 1):
        hoja.cell(row=n, column=1, value=pt.fecha).number_format = FECHA
        for col, valor in ((2, pt.pv), (3, pt.ev), (4, pt.ac)):
            hoja.cell(row=n, column=col, value=None if valor is None else float(vg.redondear_dinero(valor)))
            hoja.cell(row=n, column=col).number_format = DINERO
    ultima = inicio + len(puntos)
    grafico = LineChart()
    grafico.title = "Curva S: PV, EV y AC"
    grafico.y_axis.title = obra.moneda
    grafico.height, grafico.width = 9, 18
    grafico.add_data(Reference(hoja, min_col=2, max_col=4, min_row=inicio, max_row=ultima), titles_from_data=True)
    grafico.set_categories(Reference(hoja, min_col=1, min_row=inicio + 1, max_row=ultima))
    hoja.add_chart(grafico, f"H{inicio}")
