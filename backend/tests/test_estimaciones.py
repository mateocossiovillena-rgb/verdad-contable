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
    assert e["pasos"] == ["capas", "plantas", "formulario", "cantidades", "confirmada"]
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
    assert e["pasos"] == ["plantas", "cantidades", "confirmada"]
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
