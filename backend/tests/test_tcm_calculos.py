"""Kit TCM: APU, clase del estimado y PV semanal (funciones puras)."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.calculos import valor_ganado as vg
from app.calculos.costos import (
    CostoActividad,
    DatosRecurso,
    ParametrosApu,
    calcular_apu,
    costo_actividad,
    precio_unitario,
)
from app.tcm import clasificacion as cl
from app.tcm.linea_base import PartidaPlan, pv_acumulado, pv_semanal

BOLIVIA = ParametrosApu(
    cargas_sociales=D("55"),
    iva_mano_obra=D("14.94"),
    herramientas=D("5"),
    gastos_generales=D("10"),
    utilidad=D("8"),
    impuestos=D("3.09"),
)


def test_apu_calculado_a_mano():
    apu = calcular_apu(CostoActividad(mano_obra=D("1000"), materiales=D("500"), equipo=D("100")), BOLIVIA)
    assert apu.cargas_sociales == D("550.00")  # 55 % de 1000
    assert apu.iva_mano_obra == D("231.57")  # 14,94 % de 1550
    assert apu.total_mano_obra == D("1781.57")
    assert apu.herramientas == D("89.08")  # 5 % de 1781,57
    assert apu.costo_directo == D("2470.65")  # 500 + 1781,57 + 100 + 89,08
    assert apu.gastos_generales == D("247.07")  # 10 % de 2470,65
    assert apu.utilidad == D("217.42")  # 8 % de 2717,72
    assert apu.impuestos == D("90.70")  # 3,09 % de 2935,14
    assert apu.total == D("3025.84")
    assert precio_unitario(apu, D("10")) == D("302.58")
    assert precio_unitario(apu, None) is None


def test_apu_sin_porcentajes_es_el_costo_directo():
    costo = CostoActividad(mano_obra=D("300"), materiales=D("700"))
    assert calcular_apu(costo, ParametrosApu()).total == D("1000")


def test_equipo_se_separa_de_materiales():
    c = costo_actividad(
        [
            DatosRecurso("material", D("2"), D("50")),
            DatosRecurso("equipo", D("3"), D("35")),
            DatosRecurso("mano_obra", D("1"), D("200"), por_dia=True),
        ],
        duracion_dias=2,
    )
    assert (c.materiales, c.equipo, c.mano_obra, c.total) == (D("100.00"), D("105.00"), D("400.00"), D("605.00"))


# --- Clasificación ---


def test_tabla_del_kit_es_valida_y_pesa_100():
    t = cl.tabla()
    assert sum(e.peso for e in t.entregables) == 100
    assert [c.clase for c in t.clases] == [5, 4, 3, 2, 1]


def test_sin_entregables_es_clase_5_y_todo_completo_es_clase_1():
    t = cl.tabla()
    assert cl.clasificar({}, t).clase.clase == 5
    completo = {e.clave: "completo" for e in t.entregables}
    r = cl.clasificar(completo, t, D("100000"))
    assert (r.porcentaje_definicion, r.clase.clase) == (D("100.0"), 1)
    assert (r.minimo, r.maximo) == (D("95000.00"), D("105000.00"))  # -5 % / +5 %


@pytest.mark.parametrize(
    ("porcentaje", "clase"),
    [("0", 5), ("1.9", 5), ("2", 4), ("14.9", 4), ("15", 3), ("39.9", 3), ("40", 2), ("74.9", 2), ("75", 1)],
)
def test_cortes_de_clase(porcentaje, clase):
    assert cl.clase_para(D(porcentaje), cl.tabla()).clase == clase


def test_parcial_cuenta_la_mitad_del_peso():
    t = cl.tabla()
    assert cl.porcentaje_definicion({"planos_arquitectonicos": "parcial", "anteproyecto": "completo"}, t) == D("15.0")


def test_tabla_con_pesos_que_no_suman_100_se_rechaza():
    texto = cl.ARCHIVO.read_text(encoding="utf-8").replace("peso = 5\n", "peso = 6\n", 1)
    with pytest.raises(cl.TablaInvalida):
        cl.leer_tabla(texto)


# --- PV semanal ---


def test_pv_semanal_reparte_todo_el_bac_y_coincide_con_la_curva():
    inicio = date(2026, 12, 7)
    partidas = [
        PartidaPlan(D("7000"), inicio, inicio + timedelta(days=13)),  # 2 semanas
        PartidaPlan(D("3000"), inicio + timedelta(days=7), inicio + timedelta(days=9)),
        PartidaPlan(D("500"), None, None),  # sin fechas: no se distribuye
    ]
    semanas = pv_semanal(partidas, inicio)
    assert len(semanas) == 2
    assert semanas[0].pv == D("3500.00")
    assert semanas[1].pv == D("6500.00")
    assert semanas[-1].pv_acumulado == D("10000.00")
    assert semanas[-1].porcentaje_acumulado == D("100.0")
    # Mismo PV que el reparto lineal del EVM en cualquier fecha.
    corte = inicio + timedelta(days=8)
    esperado = sum(
        p.presupuesto * vg.fraccion_planificada(p.fecha_inicio, p.fecha_fin, corte) for p in partidas if p.fecha_inicio
    )
    assert pv_acumulado(partidas, corte) == esperado


def test_pv_semanal_sin_fechas_no_tiene_semanas():
    assert pv_semanal([PartidaPlan(D("100"), None, None)], date(2026, 1, 1)) == []
