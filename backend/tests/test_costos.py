"""Mano de obra y materiales por actividad: cálculo y API."""

from decimal import Decimal as D

from app.calculos.costos import DatosRecurso, costo_actividad, costo_recurso
from tests.test_cronograma import actividad, crear_actividad, crear_fase, crear_obra

ALBANILES = {"tipo": "mano_obra", "descripcion": "Albañil", "cantidad": 2, "precio_unitario": "150", "por_dia": True}
AYUDANTE = {"tipo": "mano_obra", "descripcion": "Ayudante", "cantidad": 1, "precio_unitario": "800"}
CEMENTO = {
    "tipo": "material",
    "descripcion": "Cemento",
    "unidad": "bolsa",
    "cantidad": "20",
    "precio_unitario": "52.50",
}
LADRILLO = {
    "tipo": "material",
    "descripcion": "Ladrillo 6H",
    "unidad": "pieza",
    "cantidad": "1500",
    "precio_unitario": "1.20",
}


# --- Cálculo puro ---


def test_jornal_se_multiplica_por_personas_y_dias():
    # 2 albañiles × Bs 150/día × 5 días
    assert costo_recurso(DatosRecurso("mano_obra", D(2), D("150"), por_dia=True), 5) == D("1500.00")


def test_pago_por_toda_la_actividad_no_depende_de_la_duracion():
    assert costo_recurso(DatosRecurso("mano_obra", D(3), D("800")), 5) == D("2400.00")
    assert costo_recurso(DatosRecurso("mano_obra", D(3), D("800")), 50) == D("2400.00")


def test_material_es_cantidad_por_precio_y_redondea_al_centavo():
    assert costo_recurso(DatosRecurso("material", D("2.5"), D("52.50")), 9) == D("131.25")
    assert costo_recurso(DatosRecurso("material", D("0.333"), D("10.00")), 1) == D("3.33")
    # "por día" no aplica a materiales.
    assert costo_recurso(DatosRecurso("material", D(1), D("100"), por_dia=True), 9) == D("100.00")


def test_costo_actividad_separa_mano_de_obra_y_materiales():
    recursos = [
        DatosRecurso("mano_obra", D(2), D("150"), por_dia=True),
        DatosRecurso("mano_obra", D(1), D("800")),
        DatosRecurso("material", D(20), D("52.50")),
    ]
    c = costo_actividad(recursos, 5)
    assert (c.mano_obra, c.materiales, c.total) == (D("2300.00"), D("1050.00"), D("3350.00"))
    assert costo_actividad([], 5).total == 0


# --- API ---


def test_actividad_con_mano_de_obra_y_materiales(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    gruesa = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    acab = crear_fase(cliente, dueno, obra["id"], "Acabados")

    crono, muros = crear_actividad(
        cliente, dueno, gruesa["id"], "Muros", 5, recursos=[ALBANILES, AYUDANTE, CEMENTO, LADRILLO]
    )
    assert [(r["descripcion"], r["costo"]) for r in muros["recursos"]] == [
        ("Albañil", 1500.0),
        ("Ayudante", 800.0),
        ("Cemento", 1050.0),
        ("Ladrillo 6H", 1800.0),
    ]
    assert muros["recursos"][2]["unidad"] == "bolsa"
    assert (muros["costo_mano_obra"], muros["costo_materiales"], muros["costo_total"]) == (2300.0, 2850.0, 5150.0)

    crono, _ = crear_actividad(
        cliente, dueno, acab["id"], "Pintura", 3, [muros["id"]], recursos=[{**ALBANILES, "descripcion": "Pintor"}]
    )
    assert [f["costo_total"] for f in crono["fases"]] == [5150.0, 900.0]
    assert (crono["costo_mano_obra"], crono["costo_materiales"], crono["costo_total"]) == (3200.0, 2850.0, 6050.0)

    # Alargar la actividad encarece el jornal, no el pago por toda la actividad ni los materiales.
    r = cliente.put(f"/api/actividades/{muros['id']}", json={"nombre": "Muros", "duracion_dias": 10}, headers=dueno)
    muros = actividad(r.json(), "Muros")
    assert len(muros["recursos"]) == 4  # sin "recursos" en el pedido se conservan
    assert (muros["costo_mano_obra"], muros["costo_materiales"]) == (3800.0, 2850.0)

    # Enviar la lista los reemplaza; lista vacía los quita.
    r = cliente.put(
        f"/api/actividades/{muros['id']}",
        json={"nombre": "Muros", "duracion_dias": 10, "recursos": [CEMENTO]},
        headers=dueno,
    )
    assert [x["descripcion"] for x in actividad(r.json(), "Muros")["recursos"]] == ["Cemento"]
    r = cliente.put(
        f"/api/actividades/{muros['id']}", json={"nombre": "Muros", "duracion_dias": 10, "recursos": []}, headers=dueno
    )
    assert actividad(r.json(), "Muros")["costo_total"] == 0

    # Borrar la actividad borra sus recursos con ella.
    r = cliente.delete(f"/api/actividades/{actividad(r.json(), 'Pintura')['id']}", headers=dueno)
    assert r.json()["costo_total"] == 0


def test_validaciones_de_recursos(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    malos = [
        {**CEMENTO, "tipo": "equipo"},
        {**CEMENTO, "cantidad": 0},
        {**CEMENTO, "precio_unitario": "-1"},
        {**CEMENTO, "precio_unitario": "1.234"},
        {**CEMENTO, "descripcion": ""},
        {**ALBANILES, "cantidad": "1.5"},  # personas enteras
    ]
    for recurso in malos:
        r = cliente.post(
            f"/api/fases/{fase['id']}/actividades",
            json={"nombre": "X", "duracion_dias": 1, "recursos": [recurso]},
            headers=dueno,
        )
        assert r.status_code == 422, recurso
    # Un material marcado "por día" se guarda como pago único.
    _, a = crear_actividad(cliente, dueno, fase["id"], "Y", 4, recursos=[{**CEMENTO, "por_dia": True}])
    assert a["recursos"][0]["por_dia"] is False and a["costo_total"] == 1050.0
