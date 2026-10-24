import pytest

from app.calculos.plano_dxf import PlanoInvalido
from app.calculos.plano_ifc import leer_ifc
from tests.planos_prueba import casa_ifc


def test_lee_pisos_y_cantidades_del_modelo():
    modelo = leer_ifc(casa_ifc())
    assert [p.nombre for p in modelo.pisos] == ["Planta baja", "Planta alta"]
    assert [p.elevacion for p in modelo.pisos] == [0.0, 2.8]
    pb = modelo.pisos[0].medido
    # 36 m del muro con Qto + 7,64 m del que solo trae geometría (en mm en el archivo).
    assert pb.largo_muros == pytest.approx(43.64)
    assert pb.area_muros_exterior == pytest.approx(85)
    assert pb.area_planta == pytest.approx(80)
    assert pb.altura == pytest.approx(2.6)
    assert pb.area_ambientes == pytest.approx(18.5)
    assert (pb.banos, pb.cocinas, pb.columnas) == (1, 1, 1)
    assert [(p.ancho, p.alto) for p in pb.puertas] == [(0.9, 2.1)]
    assert [(v.ancho, v.alto) for v in pb.ventanas] == [(1.2, 1.0)]
    assert modelo.pisos[1].medido.area_cubierta == pytest.approx(85)


def test_el_modelo_responde_el_formulario():
    modelo = leer_ifc(casa_ifc())
    assert modelo.formulario.altura_piso == pytest.approx(2.6)
    assert modelo.formulario.tipo_muro == "ladrillo_6h"
    assert modelo.formulario.cubierta == "losa"
    assert set(modelo.datos_del_modelo) >= {"altura_piso", "tipo_muro", "cubierta"}


def test_avisa_los_muros_sin_cantidades():
    modelo = leer_ifc(casa_ifc())
    assert any("Qto" in a for a in modelo.avisos)


def test_rechaza_un_archivo_que_no_es_ifc():
    with pytest.raises(PlanoInvalido):
        leer_ifc(b"esto no es un modelo")
