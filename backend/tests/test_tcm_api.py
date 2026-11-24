"""Kit TCM por la API: plantilla, importar con validación, estimado, línea base inmutable y exportación."""

from datetime import date, timedelta
from decimal import Decimal as D
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy.orm import sessionmaker

from app.modelos import LineaBase, LineaBaseInmutable
from app.tcm import ejemplo
from app.tcm import plantilla as pl

OCTETO = {"Content-Type": "application/octet-stream"}


@pytest.fixture(scope="module")
def excel_ejemplo() -> bytes:
    return pl.escribir_plantilla(ejemplo.datos())


def _importar(cliente, dueno, contenido: bytes) -> int:
    r = cliente.post("/api/kit/importar", content=contenido, headers={**dueno, **OCTETO})
    assert r.status_code == 201, r.text
    return r.json()["obra"]["id"]


def test_plantilla_vacia_se_descarga_y_no_pasa_la_validacion(cliente, dueno):
    r = cliente.get("/api/kit/plantilla.xlsx", headers=dueno)
    assert r.status_code == 200
    libro = load_workbook(BytesIO(r.content))
    assert libro.sheetnames == [
        "Instrucciones", "Datos de obra", "Clasificación", "Actividades", "APU-Insumos", "Base del estimado"
    ]  # fmt: skip
    assert libro["Actividades"].data_validations.dataValidation  # listas desplegables y validaciones
    previa = cliente.post("/api/kit/importar/previa", content=r.content, headers={**dueno, **OCTETO}).json()
    assert previa["valida"] is False
    mensajes = {(e["hoja"], e["columna"]) for e in previa["errores"]}
    assert ("Datos de obra", "Nombre de la obra") in mensajes
    assert ("Actividades", "") in mensajes  # no hay actividades


def test_vista_previa_del_ejemplo_no_graba_nada(cliente, dueno, excel_ejemplo):
    r = cliente.post("/api/kit/importar/previa", content=excel_ejemplo, headers={**dueno, **OCTETO})
    assert r.status_code == 200, r.text
    previa = r.json()
    assert previa["valida"] is True, previa["errores"]
    resumen = previa["resumen"]
    assert (resumen["fases"], resumen["actividades"], resumen["clase"]) == (7, 34, 2)
    assert cliente.get("/api/obras", headers=dueno).json() == []


def test_importar_crea_la_obra_con_estimado_clase_y_base(cliente, dueno, excel_ejemplo):
    obra_id = _importar(cliente, dueno, excel_ejemplo)
    est = cliente.get(f"/api/obras/{obra_id}/estimado", headers=dueno).json()
    assert len(est["fases"]) == 7
    assert sum(len(f["actividades"]) for f in est["fases"]) == 34
    assert est["clasificacion"]["clase"]["clase"] == 2
    assert est["clasificacion"]["porcentaje_definicion"] == 55.0
    assert est["parametros"]["cargas_sociales"] == 55.0
    assert est["base"]["contingencia_porcentaje"] == 5.0
    assert est["base"]["fecha_precios"] == "2026-11-15"
    assert est["vigente"] is None
    # El total del estimado coincide con lo que mostró la vista previa y con el presupuesto de las partidas.
    previa = cliente.post("/api/kit/importar/previa", content=excel_ejemplo, headers={**dueno, **OCTETO}).json()
    assert est["totales"]["total"] == previa["resumen"]["total_estimado"]
    partidas = cliente.get(f"/api/obras/{obra_id}/partidas", headers=dueno).json()
    assert round(sum(p["presupuesto"] for p in partidas), 2) == est["totales"]["total"]
    # Cronograma con predecesoras por código: la limpieza final es lo último.
    actividades = {a["codigo"]: a for f in est["fases"] for a in f["actividades"]}
    assert actividades["1.1"]["fecha_inicio"] == "2026-12-07"
    assert actividades["7.10"]["fecha_fin"] == max(a["fecha_fin"] for a in actividades.values())
    # APU por unidad: precio unitario = total / cómputo.
    muro = actividades["4.2"]
    assert muro["precio_unitario"] == pytest.approx(muro["apu"]["total"] / 260, abs=0.01)


def test_linea_base_aprobada_es_la_que_mide_el_valor_ganado(cliente, dueno, excel_ejemplo):
    obra_id = _importar(cliente, dueno, excel_ejemplo)
    r = cliente.post(f"/api/obras/{obra_id}/lineas-base", json={"motivo": "Contrato firmado"}, headers=dueno)
    assert r.status_code == 201, r.text
    est = r.json()
    v1 = est["vigente"]
    assert (v1["version"], v1["clase"], v1["motivo"]) == (1, 2, "Contrato firmado")
    assert v1["bac"] == est["totales"]["total"]
    assert v1["semanas"][-1]["pv_acumulado"] == v1["bac"]
    assert est["plan_distinto_de_base"] is False

    # Cambiar el plan (subir los % del APU) no cambia el BAC: el EVM sigue midiendo contra la v1.
    nuevos = {**est["parametros"], "utilidad": 15}
    est = cliente.put(f"/api/obras/{obra_id}/estimado/parametros", json=nuevos, headers=dueno).json()
    assert est["totales"]["total"] > v1["bac"]
    assert est["plan_distinto_de_base"] is True
    corte = (date(2026, 12, 7) + timedelta(days=30)).isoformat()
    ind = cliente.get(f"/api/obras/{obra_id}/indicadores?corte={corte}", headers=dueno).json()
    assert ind["indicadores"]["bac"] == v1["bac"]

    # Una versión nueva toma el plan actual; la v1 queda tal cual y deja de valer.
    est = cliente.post(f"/api/obras/{obra_id}/lineas-base", json={"motivo": "Cambio de utilidad"}, headers=dueno).json()
    assert est["vigente"]["version"] == 2
    assert est["vigente"]["bac"] == est["totales"]["total"]
    assert [(b["version"], b["vigente"]) for b in est["lineas_base"]] == [(2, True), (1, False)]
    vieja = cliente.get(f"/api/lineas-base/{v1['id']}", headers=dueno).json()
    assert (vieja["bac"], vieja["vigente"]) == (v1["bac"], False)
    ind = cliente.get(f"/api/obras/{obra_id}/indicadores?corte={corte}", headers=dueno).json()
    assert ind["indicadores"]["bac"] == est["vigente"]["bac"]


def test_linea_base_no_se_puede_editar(cliente, dueno, excel_ejemplo, tmp_path):
    obra_id = _importar(cliente, dueno, excel_ejemplo)
    cliente.post(f"/api/obras/{obra_id}/lineas-base", json={}, headers=dueno)
    from app.db import obtener_sesion
    from app.main import app

    sesion = next(app.dependency_overrides[obtener_sesion]())
    base = sesion.query(LineaBase).one()
    base.partidas[0].presupuesto = D("1")
    with pytest.raises(LineaBaseInmutable):
        sesion.flush()
    sesion.rollback()
    base = sesion.query(LineaBase).one()
    base.bac = D("1")
    with pytest.raises(LineaBaseInmutable):
        sesion.flush()
    sesion.close()


def test_sin_presupuesto_no_se_aprueba_linea_base(cliente, dueno):
    obra = cliente.post("/api/obras", json={"nombre": "Vacía", "fecha_inicio": "2026-12-01"}, headers=dueno).json()
    r = cliente.post(f"/api/obras/{obra['id']}/lineas-base", json={}, headers=dueno)
    assert r.status_code == 422


def test_clasificacion_y_base_del_estimado_se_editan(cliente, dueno, excel_ejemplo):
    obra_id = _importar(cliente, dueno, excel_ejemplo)
    r = cliente.put(
        f"/api/obras/{obra_id}/estimado/clasificacion",
        json={"entregables": {"especificaciones": "completo", "cotizaciones": "completo"}},
        headers=dueno,
    )
    assert r.json()["clasificacion"]["porcentaje_definicion"] == 75.0
    assert r.json()["clasificacion"]["clase"]["clase"] == 1
    r = cliente.put(
        f"/api/obras/{obra_id}/estimado/clasificacion", json={"entregables": {"inventado": "no"}}, headers=dueno
    )
    assert r.status_code == 422
    r = cliente.put(
        f"/api/obras/{obra_id}/estimado/base",
        json={"proposito": "  Licitación  ", "contingencia_porcentaje": 7.5},
        headers=dueno,
    )
    base = r.json()["base"]
    assert base["proposito"] == "Licitación"
    assert base["contingencia_monto"] == pytest.approx(r.json()["totales"]["total"] * 0.075, abs=0.01)


def test_exportar_estimado_con_linea_base_y_curva_s(cliente, dueno, excel_ejemplo):
    obra_id = _importar(cliente, dueno, excel_ejemplo)
    cliente.post(f"/api/obras/{obra_id}/lineas-base", json={}, headers=dueno)
    r = cliente.get(f"/api/obras/{obra_id}/estimado.xlsx", headers=dueno)
    assert r.status_code == 200
    libro = load_workbook(BytesIO(r.content))
    assert {"Resumen", "Estimado APU", "Insumos", "Base del estimado", "Línea base", "PV semanal"} <= set(
        libro.sheetnames
    )
    assert libro["PV semanal"]._charts  # curva S como gráfico de Excel
    assert libro["Estimado APU"].max_row >= 35


def test_otro_dueno_no_ve_el_estimado(cliente, dueno, excel_ejemplo):
    obra_id = _importar(cliente, dueno, excel_ejemplo)
    r = cliente.post("/api/sesion/registro", json={"nombre": "Otro", "correo": "otro@obra.bo", "clave": "clave-segura"})
    otro = {"Authorization": f"Bearer {r.json()['token']}"}
    assert cliente.get(f"/api/obras/{obra_id}/estimado", headers=otro).status_code == 404


# --- Importador: errores fila por fila ---


def _con_errores() -> bytes:
    d = ejemplo.datos()
    acts = d.actividades
    acts[1].codigo = acts[0].codigo  # código duplicado (fila 3)
    acts[2].predecesoras = ["9.9"]  # predecesora inexistente (fila 4)
    acts[3].predecesoras = ["2.3"]  # 2.1 → 2.3 → 2.1: ciclo
    acts[4].inicio = d.fecha_inicio - timedelta(days=10)  # 2.2: fecha anterior al inicio de la obra (fila 6)
    acts[4].predecesoras = []
    d.insumos = [i for i in d.insumos if i.codigo_actividad != "1.3"] + [
        pl.InsumoLeido(0, "8.8", "material", "Algo", "u", D("1"), D("1"))
    ]
    libro = load_workbook(BytesIO(pl.escribir_plantilla(d)))
    libro["APU-Insumos"].cell(row=2, column=2, value="Herramienta")  # tipo inválido
    libro["Actividades"].cell(row=10, column=3).value = None  # nombre vacío
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def test_importador_reporta_cada_error_con_su_fila(cliente, dueno):
    contenido = _con_errores()
    previa = cliente.post("/api/kit/importar/previa", content=contenido, headers={**dueno, **OCTETO}).json()
    assert previa["valida"] is False
    errores = {(e["hoja"], e["fila"], e["columna"]) for e in previa["errores"]}
    textos = " | ".join(e["mensaje"] for e in previa["errores"])
    assert ("Actividades", 3, "Código") in errores
    assert ("Actividades", 4, "Predecesoras") in errores
    assert "Dependencia circular" in textos
    assert ("Actividades", 6, "Inicio fijo") in errores
    assert ("APU-Insumos", 2, "Tipo") in errores
    assert ("Actividades", 10, "Actividad") in errores
    assert any(e["columna"] == "Costo" for e in previa["errores"])  # 1.3 quedó sin insumos
    assert any(e["hoja"] == "APU-Insumos" and "8.8" in e["mensaje"] for e in previa["errores"])
    # Confirmar con errores no graba nada.
    r = cliente.post("/api/kit/importar", content=contenido, headers={**dueno, **OCTETO})
    assert r.status_code == 422
    assert cliente.get("/api/obras", headers=dueno).json() == []


def test_archivo_que_no_es_excel(cliente, dueno):
    r = cliente.post("/api/kit/importar/previa", content=b"hola", headers={**dueno, **OCTETO})
    assert r.json()["valida"] is False


def test_numeros_con_coma_decimal_y_fechas_en_texto():
    assert pl._decimal("1.234,5") == D("1234.5")
    assert pl._decimal("0,25") == D("0.25")
    assert pl._fecha_de("07/12/2026") == date(2026, 12, 7)
    with pytest.raises(ValueError):
        pl._decimal("abc")


def test_el_ejemplo_se_carga_con_linea_base(tmp_path):
    """Lo que hace `python -m app.tcm.ejemplo`, contra una base temporal."""
    from app.db import Base, crear_motor
    from app.modelos import ROL_DUENO, Usuario

    motor = crear_motor(f"sqlite:///{tmp_path / 'ej.db'}")
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as sesion:
        dueno = Usuario(nombre="Demo", correo="d@d.bo", rol=ROL_DUENO, clave_hash="x")
        sesion.add(dueno)
        sesion.flush()
        contenido = ejemplo.escribir(tmp_path / "ejemplo.xlsx")
        obra = ejemplo.cargar_en(sesion, dueno, contenido)
        sesion.commit()
        base = sesion.query(LineaBase).filter_by(obra_id=obra.id).one()
        assert base.version == 1 and base.vigente
        assert len(base.partidas) == 35  # 34 actividades + gastos generales
    motor.dispose()
