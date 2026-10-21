"""Flujo completo de la API: dueño, encargado, gastos, avances y cierres."""

import base64
from datetime import timedelta

from app import servicios
from tests.conftest import cabecera

# JPG mínimo: solo importa la firma inicial.
FOTO = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 100).decode()


def crear_obra(cliente, dueno, **extra):
    hoy = servicios.hoy()
    datos = {
        "nombre": "Casa Mamani",
        "ubicacion": "El Alto",
        "fecha_inicio": (hoy - timedelta(days=9)).isoformat(),
        "fecha_fin": (hoy + timedelta(days=10)).isoformat(),
    }
    datos.update(extra)
    r = cliente.post("/api/obras", json=datos, headers=dueno)
    assert r.status_code == 201, r.text
    return r.json()


def crear_partida(cliente, dueno, obra_id, **extra):
    hoy = servicios.hoy()
    datos = {
        "nombre": "Muro 2do piso",
        "presupuesto": 10000,
        "fecha_inicio": (hoy - timedelta(days=9)).isoformat(),
        "fecha_fin": hoy.isoformat(),
    }
    datos.update(extra)
    r = cliente.post(f"/api/obras/{obra_id}/partidas", json=datos, headers=dueno)
    assert r.status_code == 201, r.text
    return r.json()


def crear_encargado(cliente, dueno, obra_ids):
    r = cliente.post(
        "/api/equipo",
        json={"nombre": "Don Pedro", "telefono": "+591 70000001", "pin": "123456", "obra_ids": obra_ids},
        headers=dueno,
    )
    assert r.status_code == 201, r.text
    r = cliente.post("/api/sesion/ingreso", json={"usuario": "+59170000001", "clave": "123456"})
    assert r.status_code == 200, r.text
    return cabecera(r.json()["token"])


def test_registro_e_ingreso(cliente, dueno):
    assert cliente.get("/api/sesion/yo", headers=dueno).json()["rol"] == "dueno"
    assert (
        cliente.post("/api/sesion/ingreso", json={"usuario": "ANA@obra.bo", "clave": "clave-segura"}).status_code == 200
    )
    assert cliente.post("/api/sesion/ingreso", json={"usuario": "ana@obra.bo", "clave": "otra"}).status_code == 401
    assert cliente.get("/api/sesion/yo").status_code == 401


def test_obra_nueva_tiene_partida_generales(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    partidas = cliente.get(f"/api/obras/{obra['id']}/partidas", headers=dueno).json()
    assert [p["es_generales"] for p in partidas] == [True]


def test_flujo_completo_e_indicadores(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    muro = crear_partida(cliente, dueno, obra["id"])
    encargado = crear_encargado(cliente, dueno, [obra["id"]])

    # El encargado registra gasto, avance y un gasto sin partida.
    r = cliente.post(
        f"/api/obras/{obra['id']}/gastos",
        json={
            "monto": "4500.50",
            "tipo": "material",
            "partida_id": muro["id"],
            "foto_base64": FOTO,
            "id_cliente": "a1",
        },
        headers=encargado,
    )
    assert r.status_code == 201, r.text
    assert r.json()["foto"].endswith(".jpg")
    # Reenvío desde la cola sin señal: no se duplica.
    r2 = cliente.post(
        f"/api/obras/{obra['id']}/gastos",
        json={"monto": "4500.50", "tipo": "material", "partida_id": muro["id"], "id_cliente": "a1"},
        headers=encargado,
    )
    assert r2.status_code == 200 and r2.json()["id"] == r.json()["id"]
    r = cliente.post(f"/api/obras/{obra['id']}/gastos", json={"monto": 100, "tipo": "transporte"}, headers=encargado)
    assert r.json()["partida_nombre"] == servicios.NOMBRE_GENERALES
    r = cliente.post(f"/api/partidas/{muro['id']}/avances", json={"porcentaje": 30}, headers=encargado)
    assert r.status_code == 201, r.text

    dia = cliente.get(f"/api/obras/{obra['id']}/dia", headers=encargado).json()
    assert cliente.get(f"/api/fotos/{dia['gastos'][0]['foto']}").status_code == 200
    assert dia["total_dia"] == 4600.5 and dia["acumulado"] == 4600.5 and not dia["cerrado"]

    # El encargado no ve indicadores ni presupuestos.
    assert cliente.get(f"/api/obras/{obra['id']}/indicadores", headers=encargado).status_code == 403
    resumen = cliente.get("/api/obras", headers=encargado).json()[0]
    assert resumen["presupuesto"] is None and resumen["gastado_hoy"] == 4600.5
    assert all(
        p["presupuesto"] == 0 for p in cliente.get(f"/api/obras/{obra['id']}/partidas", headers=encargado).json()
    )

    ind = cliente.get(f"/api/obras/{obra['id']}/indicadores", headers=dueno).json()
    i = ind["indicadores"]
    assert i["bac"] == 10000 and i["pv"] == 10000 and i["ev"] == 3000 and i["ac"] == 4600.5
    assert i["spi"] == 0.3 and i["cpi"] == 0.6521
    assert ind["semaforo"] == "rojo"
    assert ind["frases"][0] == "Gastaste el 46 % del presupuesto y avanzaste el 30 %."
    assert ind["curva"][-1]["ac"] is None  # el futuro no tiene costo real
    codigos = {a["codigo"] for p in ind["partidas"] for a in p["advertencias"]}
    assert "gasto_sin_presupuesto" in codigos

    alertas = cliente.get("/api/alertas", headers=dueno).json()
    assert alertas and alertas[0]["nivel"] == "rojo"


def test_cierre_del_dia(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    encargado = crear_encargado(cliente, dueno, [obra["id"]])
    cliente.post(f"/api/obras/{obra['id']}/gastos", json={"monto": 50, "tipo": "caja_chica"}, headers=encargado)
    r = cliente.post(f"/api/obras/{obra['id']}/cierres", json={}, headers=encargado)
    assert r.status_code == 201 and r.json()["cerrado"]
    r = cliente.post(f"/api/obras/{obra['id']}/gastos", json={"monto": 10, "tipo": "caja_chica"}, headers=encargado)
    assert r.status_code == 409
    hoy = servicios.hoy().isoformat()
    assert cliente.delete(f"/api/obras/{obra['id']}/cierres/{hoy}", headers=encargado).status_code == 403
    assert cliente.delete(f"/api/obras/{obra['id']}/cierres/{hoy}", headers=dueno).status_code == 204
    r = cliente.post(f"/api/obras/{obra['id']}/gastos", json={"monto": 10, "tipo": "caja_chica"}, headers=encargado)
    assert r.status_code == 201


def test_anular_gasto_y_exportar(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    gasto = cliente.post(
        f"/api/obras/{obra['id']}/gastos", json={"monto": 80, "tipo": "material"}, headers=dueno
    ).json()
    r = cliente.post(f"/api/gastos/{gasto['id']}/anular", json={"motivo": "Duplicado"}, headers=dueno)
    assert r.status_code == 200 and r.json()["anulado"]
    assert cliente.get(f"/api/obras/{obra['id']}/gastos", headers=dueno).json() == []
    todos = cliente.get(f"/api/obras/{obra['id']}/gastos?incluir_anulados=true", headers=dueno).json()
    assert len(todos) == 1
    r = cliente.get(f"/api/obras/{obra['id']}/gastos.xlsx", headers=dueno)
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_aislamiento_entre_duenos(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    otro = cliente.post(
        "/api/sesion/registro", json={"nombre": "Otro", "correo": "otro@obra.bo", "clave": "clave-segura"}
    ).json()["token"]
    otro = cabecera(otro)
    assert cliente.get(f"/api/obras/{obra['id']}", headers=otro).status_code == 404
    assert cliente.get("/api/obras", headers=otro).json() == []
    r = cliente.post(f"/api/obras/{obra['id']}/gastos", json={"monto": 1, "tipo": "material"}, headers=otro)
    assert r.status_code == 404
    # Un encargado sin asignación tampoco ve la obra.
    encargado = crear_encargado(cliente, dueno, [])
    assert cliente.get(f"/api/obras/{obra['id']}/dia", headers=encargado).status_code == 404


def test_validaciones(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    manana = (servicios.hoy() + timedelta(days=1)).isoformat()
    casos = [
        {"monto": 0, "tipo": "material"},
        {"monto": -5, "tipo": "material"},
        {"monto": 10, "tipo": "otro"},
        {"monto": "10.123", "tipo": "material"},
        {"monto": 10, "tipo": "material", "fecha": manana},
        {"monto": 10, "tipo": "material", "foto_base64": base64.b64encode(b"no es imagen").decode()},
    ]
    for datos in casos:
        assert cliente.post(f"/api/obras/{obra['id']}/gastos", json=datos, headers=dueno).status_code == 422, datos
    r = cliente.post(
        "/api/obras", json={"nombre": "X obra", "fecha_inicio": "2026-02-01", "fecha_fin": "2026-01-01"}, headers=dueno
    )
    assert r.status_code == 422
    generales = cliente.get(f"/api/obras/{obra['id']}/partidas", headers=dueno).json()[0]
    assert cliente.delete(f"/api/partidas/{generales['id']}", headers=dueno).status_code == 409
    assert (
        cliente.post(f"/api/partidas/{generales['id']}/avances", json={"porcentaje": 10}, headers=dueno).status_code
        == 422
    )
