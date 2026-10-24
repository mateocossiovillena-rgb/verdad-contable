import pytest

from app.calculos import medicion_plano as mp
from app.calculos.plano_dxf import PlanoInvalido, leer_dxf
from tests.planos_prueba import casa_dxf, documento, linea


def _roles(dibujo):
    return {c["nombre"]: c["rol_sugerido"] for c in mp.resumen_capas(dibujo)}


def test_lee_capas_y_sugiere_roles():
    dibujo = leer_dxf(casa_dxf())
    assert dibujo.unidades == 5
    roles = _roles(dibujo)
    assert roles["A-MURO"] == "muros"
    assert roles["PUERTAS"] == "puertas"
    assert roles["VENTANAS"] == "ventanas"
    assert roles["AMBIENTES"] == "ambientes"
    assert roles["COTAS"] == "ignorar"
    # La capa "0" no tiene nada dibujado afuera de los bloques: no se muestra.
    assert "0" not in roles


def test_deduce_unidades_si_el_archivo_no_las_trae():
    assert mp.detectar_unidades(leer_dxf(casa_dxf(unidades=None))) == (5, True)
    assert mp.detectar_unidades(leer_dxf(casa_dxf(unidades=4))) == (4, False)


def test_separa_las_plantas_dibujadas_lado_a_lado():
    dibujo = leer_dxf(casa_dxf())
    regiones = mp.detectar_regiones(dibujo, _roles(dibujo), 0.01)
    assert [tuple(round(v, 2) for v in r.caja) for r in regiones] == [(0, 0, 10, 8), (15, 0, 25, 8)]


def test_mide_una_planta():
    dibujo = leer_dxf(casa_dxf())
    roles = _roles(dibujo)
    region = mp.detectar_regiones(dibujo, roles, 0.01)[0]
    medida = mp.medir_planta(dibujo, region, roles, 0.01, "Planta baja")
    piso = medida.piso
    assert piso.area_planta == pytest.approx(80, abs=0.5)
    assert piso.perimetro_exterior == pytest.approx(36, abs=0.5)
    # Eje ideal: 2 × (9,82 + 7,82) de exteriores + 7,64 del interior = 42,92 m.
    assert piso.largo_muros == pytest.approx(42.92, abs=1.0)
    assert piso.espesor_muros == pytest.approx(0.18, abs=0.01)
    assert piso.ambientes == ["DORMITORIO 1", "BAÑO"]
    assert (piso.banos, piso.cocinas) == (1, 0)
    assert [p.ancho for p in piso.puertas] == [0.9]
    assert [(v.ancho, v.alto) for v in piso.ventanas] == [(1.2, 1.0), (1.2, 1.0)]
    assert medida.geometria["ancho"] == 10 and medida.geometria["muros"]
    assert medida.avisos == []


def test_muros_de_una_sola_linea_avisan():
    entidades = [linea("MUROS", *s) for s in ((0, 0, 10, 0), (10, 0, 10, 8), (10, 8, 0, 8), (0, 8, 0, 0))]
    dibujo = leer_dxf(documento(entidades, ["MUROS"], {}, unidades=6).encode())
    roles = {"MUROS": "muros"}
    region = mp.detectar_regiones(dibujo, roles, 1.0)[0]
    medida = mp.medir_planta(dibujo, region, roles, 1.0, "PB")
    assert medida.piso.largo_muros == pytest.approx(36)
    assert any("una sola línea" in a for a in medida.avisos)


def test_medidas_desde_el_nombre_del_bloque():
    assert mp.medidas_de_nombre("P-090") == (0.9, None)
    assert mp.medidas_de_nombre("V120x100") == (1.2, 1.0)


@pytest.mark.parametrize(
    "datos, mensaje",
    [
        (b"AutoCAD Binary DXF\r\n\x1a\x00resto", "binario"),
        (b"AC1032\x00\x00\x00", "DWG"),
    ],
)
def test_rechaza_formatos_que_no_lee(datos, mensaje):
    with pytest.raises(PlanoInvalido, match=mensaje):
        leer_dxf(datos)
