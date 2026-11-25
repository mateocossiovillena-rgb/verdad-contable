"""Kit TCM fase 5: generación de los archivos del kit y hoja de registro de la prueba de uso."""

from io import BytesIO

from openpyxl import load_workbook

from app.tcm import hoja_prueba, kit
from app.tcm import plantilla as pl


def test_generar_el_kit_crea_todos_los_archivos(tmp_path):
    archivos = kit.generar(tmp_path)
    nombres = {a.relative_to(tmp_path).as_posix() for a in archivos}
    assert nombres == {
        "plantillas/plantilla-kit-tcm.xlsx",
        "plantillas/riesgos-y-cambios.xlsx",
        "ejemplo/vivienda-120m2.xlsx",
        "ejemplo/estimado-vivienda-en-ejecucion.xlsx",
        "prueba/hoja-de-registro.xlsx",
    }
    # El ejemplo del kit pasa la validación del importador sin errores.
    assert pl.leer_plantilla((tmp_path / "ejemplo/vivienda-120m2.xlsx").read_bytes()).valida
    exportado = load_workbook(tmp_path / "ejemplo/estimado-vivienda-en-ejecucion.xlsx")
    assert {"Valor ganado", "Riesgos", "Cambios", "Línea base"} <= set(exportado.sheetnames)
    assert exportado["Cambios"]["I2"].value == "v2"  # C-01 aprobado generó la línea base v2


def test_hoja_de_registro_tiene_las_tareas_el_sus_y_el_resumen():
    libro = load_workbook(BytesIO(hoja_prueba.escribir_hoja_prueba()))
    assert libro.sheetnames == ["Instrucciones", "Resumen", "P1", "P2", "P3"]
    p1 = libro["P1"]
    f = hoja_prueba.FILA_TAREAS + 1
    assert p1[f"A{f}"].value == 1 and p1[f"C{f}"].value == 4 and p1[f"D{f}"].value == 8
    assert p1[f"G{f}"].value.startswith("=IF(")  # tiempo calculado
    sus = hoja_prueba.FILA_SUS
    assert p1[f"D{sus + 1}"].value == f'=IF(C{sus + 1}="","",C{sus + 1}-1)'  # frase impar
    assert p1[f"D{sus + 2}"].value == f'=IF(C{sus + 2}="","",5-C{sus + 2})'  # frase par
    assert "*2.5" in p1[f"D{sus + 11}"].value
    resumen = libro["Resumen"]
    assert "AVERAGE('P1'!G14,'P2'!G14,'P3'!G14)" in resumen["D5"].value
    tipos = [resumen.cell(row=4, column=c).value for c in range(9, 13)]
    assert tipos == ["D · Dato mal cargado", "P · Paso omitido", "A · Pidió ayuda", "S · Error del sistema"]
