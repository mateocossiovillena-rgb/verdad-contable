from datetime import date

import pytest

from app import config
from tests.planos_prueba import casa_dxf, casa_ifc
from tests.test_api import crear_obra

BINARIO = {"Content-Type": "application/octet-stream"}


def subir(cliente, dueno, obra_id, nombre, datos):
    return cliente.post(
        f"/api/obras/{obra_id}/estimaciones", params={"nombre": nombre}, content=datos, headers=dueno | BINARIO
    )


def test_flujo_cad_pide_formulario(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    r = subir(cliente, dueno, obra["id"], "casa.dxf", casa_dxf())
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["paso"] == "capas"
    assert e["pasos"] == ["capas", "plantas", "formulario", "cantidades", "confirmada", "generada"]
    assert e["unidades"] == 5 and not e["unidades_deducidas"]
    roles = {c["nombre"]: c["rol"] for c in e["capas"]}
    assert roles["A-MURO"] == "muros"
    # El archivo queda guardado con nombre aleatorio, nunca con el del cliente.
    assert [p.suffix for p in config.CARPETA_PLANOS.iterdir()] == [".dxf"]

    # Aún no se puede saltar al formulario.
    r = cliente.put(f"/api/estimaciones/{e['id']}/formulario", json={}, headers=dueno)
    assert r.status_code == 409

    r = cliente.put(f"/api/estimaciones/{e['id']}/capas", json={"capas": roles, "unidades": 5}, headers=dueno)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["paso"] == "plantas"
    assert [(p["nombre"], p["incluir"]) for p in e["plantas"]] == [("Planta baja", True), ("Piso 1", True)]
    geo = cliente.get(f"/api/estimaciones/{e['id']}/geometria", headers=dueno).json()
    assert len(geo["zonas"]) == 2 and geo["zonas"][0]["muros"]

    plantas = [{**p, "nombre": n} for p, n in zip(e["plantas"], ["Planta baja", "Planta alta"], strict=True)]
    r = cliente.put(f"/api/estimaciones/{e['id']}/plantas", json=plantas, headers=dueno)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["paso"] == "formulario"
    assert e["pisos_medidos"][0]["area_planta"] == 80
    assert e["formulario"]["altura_piso"] == 2.6

    r = cliente.put(f"/api/estimaciones/{e['id']}/formulario", json={"altura_piso": 2.5}, headers=dueno)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["paso"] == "cantidades"
    cantidades = {c["clave"]: c for c in e["cantidades"]}
    assert cantidades["muros:Planta alta"]["origen"] == "plano"

    r = cliente.put(
        f"/api/estimaciones/{e['id']}/cantidades",
        json={"ediciones": {"muros:Planta alta": 120, "no-existe": 5}, "confirmar": True},
        headers=dueno,
    )
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["paso"] == "confirmada"
    editada = next(c for c in e["cantidades"] if c["clave"] == "muros:Planta alta")
    assert editada["cantidad"] == 120 and editada["origen"] == "editada"
    assert editada["cantidad_original"] == cantidades["muros:Planta alta"]["cantidad"]

    # Volver a un paso anterior conserva lo editado a mano.
    r = cliente.put(f"/api/estimaciones/{e['id']}/formulario", json={"altura_piso": 2.7}, headers=dueno)
    editada = next(c for c in r.json()["cantidades"] if c["clave"] == "muros:Planta alta")
    assert editada["cantidad"] == 120


def test_flujo_bim_sin_formulario(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    r = subir(cliente, dueno, obra["id"], "Casa.IFC", casa_ifc())
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["paso"] == "plantas"
    assert e["pasos"] == ["plantas", "cantidades", "confirmada", "generada"]
    assert e["capas"] == []
    assert "altura_piso" in e["datos_del_modelo"]
    assert [p["nombre"] for p in e["plantas"]] == ["Planta baja", "Planta alta"]

    r = cliente.put(f"/api/estimaciones/{e['id']}/capas", json={"capas": {}, "unidades": 6}, headers=dueno)
    assert r.status_code == 409

    r = cliente.put(f"/api/estimaciones/{e['id']}/plantas", json=e["plantas"], headers=dueno)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["paso"] == "cantidades"
    cantidades = {c["clave"]: c for c in e["cantidades"]}
    assert cantidades["muros:Planta baja"]["cantidad"] == 104.86
    assert all(c["origen"] != "formulario" for c in e["cantidades"])

    r = cliente.put(f"/api/estimaciones/{e['id']}/formulario", json={}, headers=dueno)
    assert r.status_code == 409


def test_capas_exigen_muros(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = subir(cliente, dueno, obra["id"], "casa.dxf", casa_dxf()).json()
    capas = {c["nombre"]: "ignorar" for c in e["capas"]}
    r = cliente.put(f"/api/estimaciones/{e['id']}/capas", json={"capas": capas, "unidades": 5}, headers=dueno)
    assert r.status_code == 422


def test_recuerda_las_capas_para_el_proximo_plano(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = subir(cliente, dueno, obra["id"], "casa.dxf", casa_dxf()).json()
    capas = {c["nombre"]: c["rol"] for c in e["capas"]} | {"COTAS": "columnas"}
    cliente.put(f"/api/estimaciones/{e['id']}/capas", json={"capas": capas, "unidades": 5}, headers=dueno)
    otra = subir(cliente, dueno, obra["id"], "casa-2.dxf", casa_dxf()).json()
    cotas = next(c for c in otra["capas"] if c["nombre"] == "COTAS")
    assert cotas["rol"] == "columnas" and cotas["recordada"]


def test_plantas_con_nombres_repetidos(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = subir(cliente, dueno, obra["id"], "casa.ifc", casa_ifc()).json()
    plantas = [{**p, "nombre": "Piso"} for p in e["plantas"]]
    r = cliente.put(f"/api/estimaciones/{e['id']}/plantas", json=plantas, headers=dueno)
    assert r.status_code == 422
    plantas = [{**p, "incluir": False} for p in e["plantas"]]
    r = cliente.put(f"/api/estimaciones/{e['id']}/plantas", json=plantas, headers=dueno)
    assert r.status_code == 422


def test_formatos_no_soportados(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    r = subir(cliente, dueno, obra["id"], "casa.dwg", b"AC1032")
    assert r.status_code == 422 and "DXF" in r.json()["detail"]
    r = subir(cliente, dueno, obra["id"], "casa.rvt", b"x")
    assert r.status_code == 422 and "IFC" in r.json()["detail"]
    r = subir(cliente, dueno, obra["id"], "casa.dxf", b"no es un plano")
    assert r.status_code == 422
    assert not config.CARPETA_PLANOS.exists() or not any(config.CARPETA_PLANOS.iterdir())


def test_plano_demasiado_grande(cliente, dueno, monkeypatch):
    monkeypatch.setattr(config, "TAMANO_MAX_PLANO", 100)
    obra = crear_obra(cliente, dueno)
    r = subir(cliente, dueno, obra["id"], "casa.dxf", casa_dxf())
    assert r.status_code == 413


def test_listar_y_borrar(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = subir(cliente, dueno, obra["id"], "casa.dxf", casa_dxf()).json()
    lista = cliente.get(f"/api/obras/{obra['id']}/estimaciones", headers=dueno).json()
    assert [x["id"] for x in lista] == [e["id"]]
    assert cliente.delete(f"/api/estimaciones/{e['id']}", headers=dueno).status_code == 204
    assert cliente.get(f"/api/estimaciones/{e['id']}", headers=dueno).status_code == 404
    assert not any(config.CARPETA_PLANOS.iterdir())


def test_otro_dueno_no_ve_la_estimacion(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = subir(cliente, dueno, obra["id"], "casa.dxf", casa_dxf()).json()
    r = cliente.post("/api/sesion/registro", json={"nombre": "Otro", "correo": "otro@obra.bo", "clave": "clave-segura"})
    otro = {"Authorization": f"Bearer {r.json()['token']}"}
    assert cliente.get(f"/api/estimaciones/{e['id']}", headers=otro).status_code == 404
    assert subir(cliente, otro, obra["id"], "casa.dxf", casa_dxf()).status_code == 404


def _confirmada_ifc(cliente, dueno, obra_id):
    e = subir(cliente, dueno, obra_id, "casa.ifc", casa_ifc()).json()
    e = cliente.put(f"/api/estimaciones/{e['id']}/plantas", json=e["plantas"], headers=dueno).json()
    r = cliente.put(f"/api/estimaciones/{e['id']}/cantidades", json={"confirmar": True}, headers=dueno)
    assert r.status_code == 200, r.text
    return r.json()


def _confirmada_dxf(cliente, dueno, obra_id):
    e = subir(cliente, dueno, obra_id, "casa.dxf", casa_dxf()).json()
    capas = {c["nombre"]: c["rol"] for c in e["capas"]}
    e = cliente.put(f"/api/estimaciones/{e['id']}/capas", json={"capas": capas, "unidades": 5}, headers=dueno).json()
    plantas = [{**p, "nombre": n} for p, n in zip(e["plantas"], ["Planta baja", "Planta alta"], strict=True)]
    e = cliente.put(f"/api/estimaciones/{e['id']}/plantas", json=plantas, headers=dueno).json()
    e = cliente.put(f"/api/estimaciones/{e['id']}/formulario", json={}, headers=dueno).json()
    return cliente.put(f"/api/estimaciones/{e['id']}/cantidades", json={"confirmar": True}, headers=dueno).json()


def _generar(cliente, dueno, e, modo):
    propuesta = cliente.get(f"/api/estimaciones/{e['id']}/propuesta", headers=dueno).json()
    r = cliente.post(
        f"/api/estimaciones/{e['id']}/generar", json={**propuesta["ejecucion"], "modo": modo}, headers=dueno
    )
    assert r.status_code == 200, r.text
    return propuesta, r.json()


def test_propuesta_de_cronograma_sin_guardar(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = subir(cliente, dueno, obra["id"], "casa.dxf", casa_dxf()).json()
    assert cliente.get(f"/api/estimaciones/{e['id']}/propuesta", headers=dueno).status_code == 409

    e = _confirmada_ifc(cliente, dueno, obra["id"])
    r = cliente.get(f"/api/estimaciones/{e['id']}/propuesta", headers=dueno)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["ejecucion"]["fecha_inicio"] == obra["fecha_inicio"]
    assert p["ejecucion"]["dias_semana"] == 6
    assert p["pasos"][0]["clave"] == "preliminares" and p["pasos"][-1]["clave"] == "entrega"
    assert p["pasos"][-1]["critica"]
    assert p["costo_total"] == pytest.approx(p["costo_mano_obra"] + p["costo_materiales"])
    assert p["actividades_actuales"] == 0

    # Con otra fecha y más cuadrillas, sin guardar.
    cuerpo = {
        "fecha_inicio": "2027-01-04",
        "dias_semana": 5,
        "entrega_deseada": "2027-02-01",
        "cuadrillas": {"albanileria": 2},
    }
    r = cliente.post(f"/api/estimaciones/{e['id']}/propuesta", json=cuerpo, headers=dueno)
    assert r.status_code == 200, r.text
    otra = r.json()
    assert otra["inicio"] == "2027-01-04"
    assert otra["dias_de_retraso"] == (date.fromisoformat(otra["fin"]) - date(2027, 2, 1)).days
    assert next(o for o in otra["oficios"] if o["clave"] == "albanileria")["cuadrillas"] == 2
    assert cliente.get(f"/api/estimaciones/{e['id']}", headers=dueno).json()["ejecucion"] is None

    malo = {**cuerpo, "entrega_deseada": "2026-01-01"}
    assert cliente.post(f"/api/estimaciones/{e['id']}/propuesta", json=malo, headers=dueno).status_code == 422
    malo = {**cuerpo, "cuadrillas": {"astronautas": 1}}
    assert cliente.post(f"/api/estimaciones/{e['id']}/propuesta", json=malo, headers=dueno).status_code == 422


def test_generar_crea_el_cronograma_con_ruta_critica(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = _confirmada_ifc(cliente, dueno, obra["id"])
    propuesta, e = _generar(cliente, dueno, e, "reemplazar")
    assert e["paso"] == "generada"
    assert e["ejecucion"]["dias_semana"] == 6

    crono = cliente.get(f"/api/obras/{obra['id']}/cronograma", headers=dueno).json()
    assert [f["nombre"] for f in crono["fases"]] == propuesta["fases"]
    actividades = {a["nombre"]: a for f in crono["fases"] for a in f["actividades"]}
    assert len(actividades) == len(propuesta["pasos"])
    # Mismas fechas y ruta crítica que la vista previa, y el fin de la obra es la entrega.
    for paso in propuesta["pasos"]:
        a = actividades[paso["nombre"]]
        assert (a["fecha_inicio"], a["fecha_fin"], a["critica"]) == (paso["inicio"], paso["fin"], paso["critica"])
    assert crono["fecha_fin"] == propuesta["fin"]
    muros = next(a for n, a in actividades.items() if n.startswith("Muros"))
    assert any(r["descripcion"] == "Albañil" and r["por_dia"] for r in muros["recursos"])
    assert crono["costo_total"] == pytest.approx(propuesta["costo_total"])

    # Agregar suma fases "(estimado)"; volver a reemplazar deja una sola copia.
    _generar(cliente, dueno, e, "agregar")
    crono = cliente.get(f"/api/obras/{obra['id']}/cronograma", headers=dueno).json()
    assert len(crono["fases"]) == 2 * len(propuesta["fases"])
    assert crono["fases"][-1]["nombre"].endswith(" (estimado)")
    _generar(cliente, dueno, e, "reemplazar")
    crono = cliente.get(f"/api/obras/{obra['id']}/cronograma", headers=dueno).json()
    assert len(crono["fases"]) == len(propuesta["fases"])


def test_editar_actividad_generada_conserva_el_fraguado(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = _confirmada_dxf(cliente, dueno, obra["id"])
    _generar(cliente, dueno, e, "reemplazar")
    crono = cliente.get(f"/api/obras/{obra['id']}/cronograma", headers=dueno).json()
    actividades = {a["nombre"]: a for f in crono["fases"] for a in f["actividades"]}
    columnas = actividades["Columnas de H°A° · Planta alta"]
    losa = actividades["Vigas y losa de H°A° · Planta baja"]
    r = cliente.put(
        f"/api/actividades/{columnas['id']}",
        json={
            "nombre": "Columnas P1",
            "duracion_dias": columnas["duracion_dias"] + 1,
            "predecesoras": columnas["predecesoras"],
        },
        headers=dueno,
    )
    assert r.status_code == 200, r.text
    editada = next(a for f in r.json()["fases"] for a in f["actividades"] if a["nombre"] == "Columnas P1")
    assert losa["id"] in editada["predecesoras"]
    assert editada["fecha_inicio"] == columnas["fecha_inicio"]  # sigue esperando el fraguado


def test_corregir_cantidades_despues_de_generar(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    e = _confirmada_ifc(cliente, dueno, obra["id"])
    _generar(cliente, dueno, e, "agregar")
    # Confirmar sin cambios la deja generada; con cambios vuelve a confirmada para generar de nuevo.
    r = cliente.put(f"/api/estimaciones/{e['id']}/cantidades", json={"confirmar": True}, headers=dueno)
    assert r.json()["paso"] == "generada"
    r = cliente.put(
        f"/api/estimaciones/{e['id']}/cantidades",
        json={"ediciones": {"muros:Planta baja": 90}, "confirmar": True},
        headers=dueno,
    )
    assert r.json()["paso"] == "confirmada"


def test_plano_a_partidas_con_presupuesto(cliente, dueno):
    """Del plano al control de gastos: cada paso generado es una partida con su costo como presupuesto."""
    obra = crear_obra(cliente, dueno)
    e = _confirmada_ifc(cliente, dueno, obra["id"])
    propuesta, e = _generar(cliente, dueno, e, "reemplazar")
    ind = cliente.get(f"/api/obras/{obra['id']}/indicadores", headers=dueno).json()
    del_cronograma = [p["partida"] for p in ind["partidas"] if p["partida"]["desde_cronograma"]]
    assert len(del_cronograma) == len(propuesta["pasos"])
    assert all(p["fecha_inicio"] and p["fecha_fin"] for p in del_cronograma)
    assert ind["indicadores"]["bac"] == pytest.approx(propuesta["costo_total"])

    # Reemplazar no duplica partidas.
    _generar(cliente, dueno, e, "reemplazar")
    ind = cliente.get(f"/api/obras/{obra['id']}/indicadores", headers=dueno).json()
    assert sum(p["partida"]["desde_cronograma"] for p in ind["partidas"]) == len(propuesta["pasos"])
