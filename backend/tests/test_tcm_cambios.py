"""Kit TCM fase 4: bitácora de cambios (solo un cambio aprobado versiona la línea base) y riesgos/cambios en Excel."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from app.tcm import ejemplo
from app.tcm import plantilla as pl

OCTETO = {"Content-Type": "application/octet-stream"}
CAMBIO = {
    "fecha": "2026-12-20",
    "solicitante": "Cliente",
    "descripcion": "Agregar baño de visitas",
    "impacto_costo": 14500,
    "impacto_dias": 10,
}


@pytest.fixture
def obra_id(cliente, dueno):
    contenido = pl.escribir_plantilla(ejemplo.datos())
    obra_id = cliente.post("/api/kit/importar", content=contenido, headers={**dueno, **OCTETO}).json()["obra"]["id"]
    cliente.post(f"/api/obras/{obra_id}/lineas-base", json={"motivo": "Contrato"}, headers=dueno)
    return obra_id


def _crear(cliente, dueno, obra_id, **cambios) -> dict:
    r = cliente.post(f"/api/obras/{obra_id}/cambios", json={**CAMBIO, **cambios}, headers=dueno)
    assert r.status_code == 201, r.text
    return r.json()["cambios"][-1]


def _estimado(cliente, dueno, obra_id) -> dict:
    return cliente.get(f"/api/obras/{obra_id}/estimado", headers=dueno).json()


def test_aprobar_un_cambio_como_partida_crea_la_version_2(cliente, dueno, obra_id):
    v1 = _estimado(cliente, dueno, obra_id)["vigente"]
    c = _crear(cliente, dueno, obra_id)
    assert (c["codigo"], c["estado"]) == ("C-01", "pendiente")
    # Mientras está pendiente, la línea base no cambia.
    assert _estimado(cliente, dueno, obra_id)["vigente"]["version"] == 1

    r = cliente.post(f"/api/cambios/{c['id']}/aprobar", json={"aprobador": "Ing. Rojas"}, headers=dueno)
    assert r.status_code == 200, r.text
    bit = r.json()
    aprobado = bit["cambios"][0]
    assert (aprobado["estado"], aprobado["aprobador"], aprobado["linea_base_version"]) == ("aprobado", "Ing. Rojas", 2)
    assert (bit["aprobados"], bit["costo_aprobado"], bit["dias_aprobados"]) == (1, 14500, 10)

    v2 = _estimado(cliente, dueno, obra_id)["vigente"]
    assert (v2["version"], v2["cambio_codigo"]) == (2, "C-01")
    assert v2["bac"] == pytest.approx(v1["bac"] + 14500, abs=0.01)
    partida = next(p for p in v2["partidas"] if p["codigo"] == "C-01")
    assert partida["presupuesto"] == 14500 and partida["fase"] == "Cambios aprobados"
    assert "Cambio C-01" in v2["motivo"]


def test_un_cambio_resuelto_no_se_edita_ni_se_borra(cliente, dueno, obra_id):
    c = _crear(cliente, dueno, obra_id)
    cliente.post(
        f"/api/cambios/{c['id']}/rechazar", json={"aprobador": "Ing. Rojas", "comentario": "No"}, headers=dueno
    )
    assert cliente.put(f"/api/cambios/{c['id']}", json=CAMBIO, headers=dueno).status_code == 409
    assert cliente.delete(f"/api/cambios/{c['id']}", headers=dueno).status_code == 409
    r = cliente.post(f"/api/cambios/{c['id']}/aprobar", json={"aprobador": "Ing. Rojas"}, headers=dueno)
    assert r.status_code == 409
    # Rechazado: no genera línea base.
    assert _estimado(cliente, dueno, obra_id)["vigente"]["version"] == 1


def test_un_cambio_pendiente_se_edita_y_se_borra(cliente, dueno, obra_id):
    c = _crear(cliente, dueno, obra_id)
    bit = cliente.put(f"/api/cambios/{c['id']}", json={**CAMBIO, "impacto_costo": 9000}, headers=dueno).json()
    assert bit["costo_pendiente"] == 9000
    bit = cliente.delete(f"/api/cambios/{c['id']}", headers=dueno).json()
    assert bit["cambios"] == []


def test_aprobar_sin_reflejar_el_cambio_en_el_plan_se_rechaza(cliente, dueno, obra_id):
    c = _crear(cliente, dueno, obra_id)
    r = cliente.post(
        f"/api/cambios/{c['id']}/aprobar", json={"aprobador": "Ing. Rojas", "agregar_partida": False}, headers=dueno
    )
    assert r.status_code == 422
    assert "cuesta lo mismo" in r.json()["detail"]


def test_un_cambio_que_quita_alcance_no_se_agrega_como_partida(cliente, dueno, obra_id):
    c = _crear(cliente, dueno, obra_id, impacto_costo=-5000)
    r = cliente.post(f"/api/cambios/{c['id']}/aprobar", json={"aprobador": "Ing. Rojas"}, headers=dueno)
    assert r.status_code == 422


def test_sin_linea_base_inicial_no_se_aprueban_cambios(cliente, dueno):
    contenido = pl.escribir_plantilla(ejemplo.datos())
    obra_id = cliente.post("/api/kit/importar", content=contenido, headers={**dueno, **OCTETO}).json()["obra"]["id"]
    c = _crear(cliente, dueno, obra_id)
    r = cliente.post(f"/api/cambios/{c['id']}/aprobar", json={"aprobador": "Ing. Rojas"}, headers=dueno)
    assert r.status_code == 422


def test_otro_dueno_no_toca_los_cambios(cliente, dueno, obra_id):
    c = _crear(cliente, dueno, obra_id)
    r = cliente.post("/api/sesion/registro", json={"nombre": "Otro", "correo": "otro@obra.bo", "clave": "clave-segura"})
    otro = {"Authorization": f"Bearer {r.json()['token']}"}
    assert cliente.get(f"/api/obras/{obra_id}/cambios", headers=otro).status_code == 404
    assert cliente.post(f"/api/cambios/{c['id']}/aprobar", json={"aprobador": "X Y"}, headers=otro).status_code == 404


# --- Excel ---


RIESGO = {"descripcion": "Lluvias", "probabilidad": 60, "impacto_costo": 8000, "impacto_dias": 12}


def test_riesgos_y_cambios_ida_y_vuelta_por_excel(cliente, dueno, obra_id):
    cliente.post(f"/api/obras/{obra_id}/riesgos", json=RIESGO, headers=dueno)
    c = _crear(cliente, dueno, obra_id)
    cliente.post(f"/api/cambios/{c['id']}/aprobar", json={"aprobador": "Ing. Rojas"}, headers=dueno)
    r = cliente.get(f"/api/obras/{obra_id}/registros.xlsx", headers=dueno)
    libro = load_workbook(BytesIO(r.content))
    riesgos, cambios = libro["Riesgos"], libro["Cambios"]
    assert riesgos["A2"].value == "R-01" and cambios["A2"].value == "C-01"
    assert cambios["I2"].value == "v2"

    riesgos["D2"] = 30  # actualizar R-01
    for col, valor in enumerate(
        ["", "Robo de materiales", "Sin cerco", 20, 3000, 2, "Encargado", "Mitigar", "", "Abierto"], 1
    ):
        riesgos.cell(row=3, column=col).value = valor or None  # riesgo nuevo
    cambios["E2"] = 99999  # C-01 ya aprobado: se avisa y no se toca
    for col, valor in enumerate(["", "05/01/2027", "Cliente", "Porcelanato en sala", 9800, 0], 1):
        cambios.cell(row=3, column=col).value = valor or None  # cambio nuevo
    salida = BytesIO()
    libro.save(salida)
    contenido = salida.getvalue()

    previa = cliente.post(
        f"/api/obras/{obra_id}/registros/previa", content=contenido, headers={**dueno, **OCTETO}
    ).json()
    assert previa["valida"] is True, previa["errores"]
    assert (previa["riesgos_nuevos"], previa["riesgos_actualizados"]) == (1, 1)
    assert (previa["cambios_nuevos"], previa["cambios_actualizados"]) == (1, 0)
    assert any("C-01" in a["mensaje"] for a in previa["advertencias"])

    r = cliente.post(f"/api/obras/{obra_id}/registros/importar", content=contenido, headers={**dueno, **OCTETO})
    assert r.status_code == 200, r.text
    res = r.json()
    assert [(x["codigo"], x["probabilidad"]) for x in res["riesgos"]["riesgos"]] == [("R-01", 30.0), ("R-02", 20.0)]
    cambios_api = res["cambios"]["cambios"]
    assert [(x["codigo"], x["estado"]) for x in cambios_api] == [("C-01", "aprobado"), ("C-02", "pendiente")]
    assert cambios_api[0]["impacto_costo"] == 14500  # no se modificó


def test_importar_registros_con_errores_no_graba(cliente, dueno, obra_id):
    libro = load_workbook(BytesIO(cliente.get(f"/api/obras/{obra_id}/registros.xlsx", headers=dueno).content))
    libro["Riesgos"]["A2"], libro["Riesgos"]["B2"], libro["Riesgos"]["D2"] = "R-09", "Inventado", 10  # no existe
    libro["Riesgos"]["B3"], libro["Riesgos"]["D3"] = "Probabilidad mala", 150
    libro["Cambios"]["B2"], libro["Cambios"]["C2"], libro["Cambios"]["D2"] = "no es fecha", "Cliente", "Algo"
    salida = BytesIO()
    libro.save(salida)
    previa = cliente.post(
        f"/api/obras/{obra_id}/registros/previa", content=salida.getvalue(), headers={**dueno, **OCTETO}
    ).json()
    errores = {(e["hoja"], e["fila"], e["columna"]) for e in previa["errores"]}
    assert {("Riesgos", 2, "Código"), ("Riesgos", 3, "Probabilidad"), ("Cambios", 2, "Fecha")} <= errores
    r = cliente.post(f"/api/obras/{obra_id}/registros/importar", content=salida.getvalue(), headers={**dueno, **OCTETO})
    assert r.status_code == 422
    assert cliente.get(f"/api/obras/{obra_id}/riesgos", headers=dueno).json()["riesgos"] == []


def test_el_estimado_exportado_trae_riesgos_y_cambios(cliente, dueno, obra_id):
    cliente.post(f"/api/obras/{obra_id}/riesgos", json=RIESGO, headers=dueno)
    _crear(cliente, dueno, obra_id)
    libro = load_workbook(BytesIO(cliente.get(f"/api/obras/{obra_id}/estimado.xlsx", headers=dueno).content))
    assert {"Riesgos", "Cambios"} <= set(libro.sheetnames)


def test_ejemplo_en_ejecucion_trae_la_bitacora(tmp_path):
    from datetime import date

    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app.db import Base, crear_motor
    from app.modelos import ROL_DUENO, Cambio, LineaBase, Usuario

    motor = crear_motor(f"sqlite:///{tmp_path / 'ej.db'}")
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as sesion:
        dueno = Usuario(nombre="Demo", correo="d@d.bo", rol=ROL_DUENO, clave_hash="x")
        sesion.add(dueno)
        sesion.flush()
        obra = ejemplo.cargar_en_ejecucion(sesion, dueno, pl.escribir_plantilla(ejemplo.datos()), date(2026, 11, 24))
        sesion.commit()
        estados = [
            c.estado for c in sesion.scalars(select(Cambio).where(Cambio.obra_id == obra.id).order_by(Cambio.numero))
        ]
        assert estados == ["aprobado", "rechazado", "pendiente"]
        versiones = sesion.scalars(
            select(LineaBase).where(LineaBase.obra_id == obra.id).order_by(LineaBase.version)
        ).all()
        assert [(b.version, b.vigente, b.cambio_id is not None) for b in versiones] == [
            (1, False, False),
            (2, True, True),
        ]
    motor.dispose()


def test_volver_a_subir_el_mismo_excel_no_cambia_nada(cliente, dueno, obra_id):
    cliente.post(f"/api/obras/{obra_id}/riesgos", json=RIESGO, headers=dueno)
    _crear(cliente, dueno, obra_id)
    contenido = cliente.get(f"/api/obras/{obra_id}/registros.xlsx", headers=dueno).content
    previa = cliente.post(
        f"/api/obras/{obra_id}/registros/previa", content=contenido, headers={**dueno, **OCTETO}
    ).json()
    assert previa["valida"] is True, previa["errores"]
    conteos = [previa[k] for k in ("riesgos_nuevos", "riesgos_actualizados", "cambios_nuevos", "cambios_actualizados")]
    assert conteos == [0, 0, 0, 0]
