"""Cada actividad del cronograma tiene su partida: gastos, avance y EVM salen del mismo cronograma."""

from tests.test_costos import ALBANILES, AYUDANTE
from tests.test_cronograma import crear_actividad, crear_fase, crear_obra


def partidas(cliente, dueno, obra_id):
    r = cliente.get(f"/api/obras/{obra_id}/partidas", headers=dueno)
    assert r.status_code == 200, r.text
    return {p["nombre"]: p for p in r.json() if not p["es_generales"]}


def test_actividad_crea_su_partida_con_fechas_y_costo(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    gruesa = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    _, cimientos = crear_actividad(cliente, dueno, gruesa["id"], "Cimientos", 4, recursos=[ALBANILES, AYUDANTE])
    crear_actividad(cliente, dueno, gruesa["id"], "Muros", 5, predecesoras=[cimientos["id"]])

    p = partidas(cliente, dueno, obra["id"])
    assert set(p) == {"Cimientos", "Muros"}
    c = p["Cimientos"]
    assert (c["codigo"], c["fase"], c["desde_cronograma"]) == ("1.1", "Obra gruesa", True)
    assert (c["fecha_inicio"], c["fecha_fin"]) == (cimientos["fecha_inicio"], cimientos["fecha_fin"])
    # 2 albañiles × 150 × 4 días + ayudante 800 por la actividad.
    assert c["presupuesto"] == 2000
    assert p["Muros"]["codigo"] == "1.2"
    assert p["Muros"]["presupuesto"] == 0


def test_cambios_en_la_actividad_llegan_a_la_partida(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    _, losa = crear_actividad(cliente, dueno, fase["id"], "Losa", 4, recursos=[ALBANILES])
    datos = {"nombre": "Losa 2do piso", "duracion_dias": 6, "predecesoras": [], "recursos": [ALBANILES]}
    r = cliente.put(f"/api/actividades/{losa['id']}", json=datos, headers=dueno)
    assert r.status_code == 200, r.text

    p = partidas(cliente, dueno, obra["id"])
    assert list(p) == ["Losa 2do piso"]
    assert p["Losa 2do piso"]["presupuesto"] == 1800  # jornal: ahora son 6 días
    assert p["Losa 2do piso"]["fecha_fin"] == "2026-03-07"


def test_gasto_y_avance_en_la_actividad_alimentan_los_indicadores(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    crear_actividad(cliente, dueno, fase["id"], "Cimientos", 4, recursos=[ALBANILES, AYUDANTE])
    partida = partidas(cliente, dueno, obra["id"])["Cimientos"]

    gasto = {"monto": 500, "tipo": "material", "partida_id": partida["id"]}
    assert cliente.post(f"/api/obras/{obra['id']}/gastos", json=gasto, headers=dueno).status_code == 201
    avance = {"porcentaje": 50}
    assert cliente.post(f"/api/partidas/{partida['id']}/avances", json=avance, headers=dueno).status_code == 201

    i = cliente.get(f"/api/obras/{obra['id']}/indicadores", headers=dueno).json()["indicadores"]
    assert (i["bac"], i["ac"], i["ev"]) == (2000, 500, 1000)


def test_borrar_actividad_borra_su_partida_salvo_que_tenga_gastos(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    _, cimientos = crear_actividad(cliente, dueno, fase["id"], "Cimientos", 4)
    _, muros = crear_actividad(cliente, dueno, fase["id"], "Muros", 5)
    partida_muros = partidas(cliente, dueno, obra["id"])["Muros"]
    gasto = {"monto": 200, "tipo": "material", "partida_id": partida_muros["id"]}
    cliente.post(f"/api/obras/{obra['id']}/gastos", json=gasto, headers=dueno)

    cliente.delete(f"/api/actividades/{cimientos['id']}", headers=dueno)
    cliente.delete(f"/api/actividades/{muros['id']}", headers=dueno)

    p = partidas(cliente, dueno, obra["id"])
    # Muros tenía un gasto: queda como partida suelta para no perder el historial.
    assert list(p) == ["Muros"]
    assert (p["Muros"]["desde_cronograma"], p["Muros"]["actividad_id"]) == (False, None)


def test_borrar_fase_limpia_sus_partidas(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    fase = crear_fase(cliente, dueno, obra["id"], "Acabados")
    crear_actividad(cliente, dueno, fase["id"], "Revoques", 4)
    crear_actividad(cliente, dueno, fase["id"], "Pisos", 3)
    assert cliente.delete(f"/api/fases/{fase['id']}", headers=dueno).status_code == 200
    assert partidas(cliente, dueno, obra["id"]) == {}


def test_partida_del_cronograma_no_se_edita_ni_borra_suelta(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    crear_actividad(cliente, dueno, fase["id"], "Cimientos", 4)
    partida = partidas(cliente, dueno, obra["id"])["Cimientos"]

    datos = {"nombre": "Otro nombre", "presupuesto": "100"}
    r = cliente.put(f"/api/partidas/{partida['id']}", json=datos, headers=dueno)
    assert r.status_code == 409
    assert "cronograma" in r.json()["detail"]
    assert cliente.delete(f"/api/partidas/{partida['id']}", headers=dueno).status_code == 409


def test_partidas_manuales_siguen_funcionando(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    datos = {"nombre": "Muro perimetral", "presupuesto": "5000"}
    assert cliente.post(f"/api/obras/{obra['id']}/partidas", json=datos, headers=dueno).status_code == 201
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    crear_actividad(cliente, dueno, fase["id"], "Cimientos", 4)

    p = partidas(cliente, dueno, obra["id"])
    assert set(p) == {"Muro perimetral", "Cimientos"}
    assert p["Muro perimetral"]["desde_cronograma"] is False
    assert p["Muro perimetral"]["presupuesto"] == 5000
