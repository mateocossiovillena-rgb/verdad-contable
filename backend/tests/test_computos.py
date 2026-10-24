import pytest

from app.calculos.computos import Abertura, Formulario, PisoMedido, calcular


def _casa(**extra) -> PisoMedido:
    datos = dict(
        nombre="Planta baja",
        largo_muros=40.0,
        perimetro_exterior=36.0,
        espesor_muros=0.18,
        area_planta=80.0,
        ambientes=["Dormitorio", "Baño"],
        banos=1,
        puertas=[Abertura(0.9)],
        ventanas=[Abertura(1.2, 1.0)],
    )
    datos.update(extra)
    return PisoMedido(**datos)


def _por_clave(cantidades):
    return {c.clave: c for c in cantidades}


def test_muros_suman_dinteles_y_antepechos():
    c = _por_clave(calcular([_casa()], Formulario(altura_piso=2.5)))
    # 40 × 2,5 + puerta 0,9 × 0,4 + ventana 1,2 × 1,5
    assert c["muros:Planta baja"].cantidad == pytest.approx(100 + 0.36 + 1.8)
    assert c["muros:Planta baja"].origen == "plano"
    assert c["revoque_exterior:Planta baja"].cantidad == pytest.approx(90)


def test_zapatas_por_proporcion_si_el_plano_no_marca_columnas():
    c = _por_clave(calcular([_casa()], Formulario()))
    # 80 m² / 12 m² por zapata = 7 zapatas de 1 × 1 × 0,35 m
    assert c["zapatas"].cantidad == pytest.approx(7 * 0.35)
    assert c["zapatas"].origen == "proporcion"
    c = _por_clave(calcular([_casa(columnas=9)], Formulario()))
    assert c["zapatas"].cantidad == pytest.approx(9 * 0.35)
    assert c["zapatas"].origen == "plano"


def test_cimiento_corrido_reemplaza_zapatas():
    c = _por_clave(calcular([_casa()], Formulario(fundacion="cimiento_corrido")))
    assert "zapatas" not in c
    assert c["cimientos"].cantidad == pytest.approx(40 * 0.5 * 0.6)


def test_pisos_que_se_repiten_multiplican():
    c = _por_clave(calcular([_casa(), _casa(nombre="Piso tipo", repeticiones=3)], Formulario()))
    assert c["muros:Piso tipo"].cantidad == pytest.approx(3 * c["muros:Planta baja"].cantidad)
    assert "contrapiso:Piso tipo" not in c


def test_las_claves_son_unicas_y_no_hay_ceros():
    cantidades = calcular([_casa(), PisoMedido(nombre="Techo", area_cubierta=85.0)], Formulario())
    claves = [c.clave for c in cantidades]
    assert len(claves) == len(set(claves))
    assert all(c.cantidad > 0 for c in cantidades)


def test_sin_pisos_no_hay_cantidades():
    assert calcular([], Formulario()) == []
