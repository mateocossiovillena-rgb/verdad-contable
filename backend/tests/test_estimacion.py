from datetime import date

import pytest

from app.calculos.catalogo import CATALOGO, FRAGUADO_DIAS
from app.calculos.computos import Abertura, Formulario, PisoMedido, calcular
from app.calculos.estimacion import CantidadRubro, Ejecucion, dias_calendario, proponer

INICIO = date(2026, 11, 2)  # lunes


def _piso(nombre: str) -> PisoMedido:
    return PisoMedido(
        nombre=nombre,
        largo_muros=42.2,
        perimetro_exterior=36,
        espesor_muros=0.18,
        area_planta=80,
        area_ambientes=72.6,
        ambientes=["Dormitorio", "Baño"],
        banos=1,
        puertas=[Abertura(0.9)],
        ventanas=[Abertura(1.2, 1.0)],
    )


def _cantidades(pisos: list[str], formulario: Formulario | None = None) -> list[CantidadRubro]:
    f = formulario or Formulario()
    return [CantidadRubro(c.rubro, c.piso, c.cantidad, c.unidad) for c in calcular([_piso(p) for p in pisos], f)]


def _propuesta(pisos=("PB", "P1"), formulario: Formulario | None = None, **ejecucion):
    f = formulario or Formulario()
    return proponer(_cantidades(list(pisos), f), list(pisos), 80, f, Ejecucion(INICIO, **ejecucion))


def _por_clave(propuesta):
    return {p.clave: p for p in propuesta.pasos}


def test_dias_calendario_segun_dias_de_trabajo_por_semana():
    assert dias_calendario(6, 6) == 6
    assert dias_calendario(7, 6) == 8
    assert dias_calendario(10, 5) == 12
    assert dias_calendario(3, 7) == 3


def test_secuencia_constructiva_por_piso():
    p = _por_clave(_propuesta())
    tecnicas = lambda clave: {e.predecesora for e in p[clave].predecesoras if e.origen == "tecnica"}  # noqa: E731
    assert tecnicas("excavacion") == {"preliminares"}
    assert tecnicas("muros:PB") == {"columnas:PB", "sobrecimiento"}
    assert "electrica:PB" in tecnicas("revoque_interior:PB")
    # El piso de arriba espera el fraguado de la losa de abajo.
    columnas_p1 = p["columnas:P1"].predecesoras
    assert [(e.predecesora, e.desfase_dias) for e in columnas_p1] == [("losa:PB", FRAGUADO_DIAS)]
    assert (p["columnas:P1"].inicio - p["losa:PB"].fin).days == FRAGUADO_DIAS + 1
    # Nada empieza antes de que terminen sus predecesoras.
    for paso in p.values():
        for e in paso.predecesoras:
            assert paso.inicio > p[e.predecesora].fin


def test_sin_cantidad_no_hay_paso_y_la_secuencia_sigue():
    p = _por_clave(_propuesta(formulario=Formulario(fundacion="cimiento_corrido")))
    assert "zapatas" not in p and "cimientos" in p
    assert {e.predecesora for e in p["columnas:PB"].predecesoras} == {"cimientos"}


def test_duracion_y_cuadrilla_salen_del_catalogo():
    p = _por_clave(_propuesta())
    muro = CATALOGO["muros:ladrillo_6h"]
    muros = p["muros:PB"]
    assert muros.dias_trabajo == -(-muros.cantidad // muro.rendimiento)
    assert muros.personas == muro.personas
    cargos = {r.descripcion: r.cantidad for r in muros.recursos if r.tipo == "mano_obra"}
    assert cargos == {"Albañil": 1, "Ayudante": 1}
    materiales = {r.descripcion for r in muros.recursos if r.tipo == "material"}
    assert "Ladrillo 6 huecos" in materiales
    # El fierro va como material del hormigón.
    assert any(r.descripcion == "Fierro corrugado" for r in p["losa:PB"].recursos)


def test_un_oficio_no_hace_dos_pasos_a_la_vez():
    propuesta = _propuesta()
    por_oficio = {}
    for paso in propuesta.pasos:
        por_oficio.setdefault(paso.oficio, []).append(paso)
    for pasos in por_oficio.values():
        pasos.sort(key=lambda x: x.inicio)
        for a, b in zip(pasos, pasos[1:], strict=False):
            assert b.inicio > a.fin, (a.clave, b.clave)
    assert any(e.origen == "cuadrilla" for paso in propuesta.pasos for e in paso.predecesoras)


def test_subcontrato_no_compite_por_cuadrilla():
    base = _propuesta()
    sub = _propuesta(subcontratos=frozenset({"albanileria"}))
    assert sub.fin < base.fin
    assert not any(e.origen == "cuadrilla" for p in sub.pasos if p.oficio == "albanileria" for e in p.predecesoras)


def test_mas_cuadrillas_acortan_la_obra():
    una = _propuesta()
    dos = _propuesta(cuadrillas={"albanileria": 2})
    assert dos.fin < una.fin
    assert _por_clave(dos)["muros:PB"].personas == 2 * _por_clave(una)["muros:PB"].personas


def test_ruta_critica_va_de_punta_a_punta():
    propuesta = _propuesta()
    p = _por_clave(propuesta)
    assert p["preliminares"].critica and p["entrega"].critica
    assert p["entrega"].fin == propuesta.fin
    assert any(not x.critica and x.holgura_dias > 0 for x in propuesta.pasos)


def test_sugerencia_de_cuadrilla_y_entrega_deseada():
    propuesta = _propuesta(entrega_deseada=date(2027, 1, 31))
    assert propuesta.dias_de_retraso == (propuesta.fin - date(2027, 1, 31)).days > 0
    mejor = propuesta.sugerencias[0]
    assert mejor.oficio == "albanileria" and mejor.dias_menos > 0
    con_ella = _propuesta(cuadrillas={"albanileria": 2})
    assert (propuesta.fin - con_ella.fin).days == mejor.dias_menos


def test_fases_en_orden_de_inicio_y_costos():
    propuesta = _propuesta()
    assert propuesta.fases[0] == "Preliminares" and propuesta.fases[-1] == "Entrega"
    assert propuesta.fases.index("Obra gruesa · PB") < propuesta.fases.index("Obra gruesa · P1")
    assert propuesta.costo_mano_obra > 0 and propuesta.costo_materiales > 0
    assert sum(p.costo_materiales for p in propuesta.pasos) == propuesta.costo_materiales


def test_un_solo_piso_sin_sufijo():
    propuesta = _propuesta(pisos=("Planta baja",), formulario=Formulario(cubierta="calamina"))
    p = _por_clave(propuesta)
    assert p["muros:Planta baja"].nombre == "Muros de ladrillo"
    assert p["losa:Planta baja"].nombre == "Vigas de amarre de H°A°"
    assert "Obra gruesa" in propuesta.fases
    assert p["cubierta"].oficio == "techo"


def test_sin_pisos_falla():
    with pytest.raises(ValueError):
        proponer([], [], 0, Formulario(), Ejecucion(INICIO))
