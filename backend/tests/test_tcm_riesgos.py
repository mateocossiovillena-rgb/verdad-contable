"""Kit TCM fase 3: registro de riesgos (AACE 44R-08) y contingencia sugerida."""

from decimal import Decimal as D

import pytest

from app.tcm import ejemplo
from app.tcm import plantilla as pl
from app.tcm import riesgos as rg

OCTETO = {"Content-Type": "application/octet-stream"}


def test_valor_esperado_es_probabilidad_por_impacto():
    r = rg.DatosRiesgo(probabilidad=D("40"), impacto_costo=D("6500"), impacto_dias=12)
    assert rg.valor_esperado(r) == D("2600.00")
    assert rg.dias_esperados(r) == D("4.8")


@pytest.mark.parametrize(
    ("probabilidad", "impacto", "esperado"),
    [
        ("10", "500", "bajo"),  # P baja × I bajo (0,5 % del estimado) = 1
        ("50", "500", "bajo"),  # P media × I bajo = 2
        ("50", "3000", "medio"),  # P media × I medio (3 %) = 4
        ("80", "3000", "alto"),  # P alta × I medio = 6
        ("20", "20000", "medio"),  # P baja × I alto (20 %) = 3
        ("70", "20000", "alto"),  # 9
    ],
)
def test_nivel_por_matriz_de_probabilidad_e_impacto(probabilidad, impacto, esperado):
    r = rg.DatosRiesgo(D(probabilidad), D(impacto), 0)
    assert rg.nivel(r, D("100000")) == esperado


def test_la_contingencia_sugerida_suma_solo_los_abiertos():
    riesgos = [
        rg.DatosRiesgo(D("40"), D("6500"), 0),
        rg.DatosRiesgo(D("60"), D("8000"), 12),
        rg.DatosRiesgo(D("90"), D("50000"), 30, estado="cerrado"),
        rg.DatosRiesgo(D("100"), D("1000"), 0, estado="ocurrido"),
    ]
    r = rg.resumir(riesgos, D("100000"))
    assert (r.abiertos, r.valor_esperado, r.dias_esperados) == (2, D("7400.00"), D("7.2"))
    assert r.porcentaje_del_estimado == D("7.40")
    assert rg.resumir(riesgos, None).porcentaje_del_estimado is None


# --- API ---


@pytest.fixture
def obra_id(cliente, dueno):
    contenido = pl.escribir_plantilla(ejemplo.datos())
    return cliente.post("/api/kit/importar", content=contenido, headers={**dueno, **OCTETO}).json()["obra"]["id"]


RIESGO = {
    "descripcion": "Suba del precio del fierro",
    "causa": "Escasez de dólares",
    "probabilidad": 40,
    "impacto_costo": 6500,
    "impacto_dias": 0,
    "responsable": "Dueño",
    "estrategia": "mitigar",
    "respuesta": "Comprar al iniciar",
}


def test_crear_editar_y_cerrar_riesgos(cliente, dueno, obra_id):
    r = cliente.post(f"/api/obras/{obra_id}/riesgos", json=RIESGO, headers=dueno)
    assert r.status_code == 201, r.text
    reg = r.json()
    assert reg["riesgos"][0]["codigo"] == "R-01"
    assert reg["riesgos"][0]["valor_esperado"] == 2600
    reg = cliente.post(
        f"/api/obras/{obra_id}/riesgos",
        json={**RIESGO, "descripcion": "Lluvias", "probabilidad": 60, "impacto_costo": 8000, "impacto_dias": 12},
        headers=dueno,
    ).json()
    assert [x["codigo"] for x in reg["riesgos"]] == ["R-01", "R-02"]
    assert (reg["abiertos"], reg["valor_esperado"], reg["dias_esperados"]) == (2, 7400, 7.2)
    assert reg["porcentaje_del_estimado"] == pytest.approx(7400 / reg["total_estimado"] * 100, abs=0.01)

    primero = reg["riesgos"][0]["id"]
    reg = cliente.put(f"/api/riesgos/{primero}", json={**RIESGO, "estado": "cerrado"}, headers=dueno).json()
    assert (reg["abiertos"], reg["valor_esperado"]) == (1, 4800)
    reg = cliente.delete(f"/api/riesgos/{primero}", headers=dueno).json()
    assert [x["codigo"] for x in reg["riesgos"]] == ["R-02"]


def test_validaciones_del_riesgo(cliente, dueno, obra_id):
    for malo in ({"probabilidad": 120}, {"estrategia": "rezar"}, {"estado": "dormido"}, {"descripcion": ""}):
        r = cliente.post(f"/api/obras/{obra_id}/riesgos", json={**RIESGO, **malo}, headers=dueno)
        assert r.status_code == 422, malo


def test_usar_la_suma_de_riesgos_como_contingencia(cliente, dueno, obra_id):
    cliente.post(f"/api/obras/{obra_id}/riesgos", json=RIESGO, headers=dueno)
    est = cliente.get(f"/api/obras/{obra_id}/estimado", headers=dueno).json()
    assert (est["riesgos_abiertos"], est["riesgos_valor_esperado"]) == (1, 2600)
    assert est["base"]["contingencia_porcentaje"] == 5.0  # la del Excel de ejemplo

    est = cliente.post(f"/api/obras/{obra_id}/riesgos/contingencia", headers=dueno).json()
    assert est["base"]["contingencia_porcentaje"] == est["riesgos_porcentaje"]
    assert est["base"]["contingencia_monto"] == pytest.approx(2600, abs=1)
    assert "44R-08" in est["base"]["contingencia_nota"]
    assert est["base"]["contingencia_nota"].endswith(".")


def test_sin_estimado_no_se_propone_contingencia(cliente, dueno):
    obra = cliente.post("/api/obras", json={"nombre": "Vacía", "fecha_inicio": "2026-12-01"}, headers=dueno).json()
    cliente.post(f"/api/obras/{obra['id']}/riesgos", json=RIESGO, headers=dueno)
    assert cliente.post(f"/api/obras/{obra['id']}/riesgos/contingencia", headers=dueno).status_code == 422


def test_otro_dueno_no_toca_los_riesgos(cliente, dueno, obra_id):
    reg = cliente.post(f"/api/obras/{obra_id}/riesgos", json=RIESGO, headers=dueno).json()
    r = cliente.post("/api/sesion/registro", json={"nombre": "Otro", "correo": "otro@obra.bo", "clave": "clave-segura"})
    otro = {"Authorization": f"Bearer {r.json()['token']}"}
    assert cliente.get(f"/api/obras/{obra_id}/riesgos", headers=otro).status_code == 404
    assert cliente.delete(f"/api/riesgos/{reg['riesgos'][0]['id']}", headers=otro).status_code == 404
