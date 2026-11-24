"""Kit TCM fase 2: regla de medición del avance (82R-13) y pronósticos del costo final (80R-13)."""

from datetime import date, timedelta
from decimal import Decimal as D
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy.orm import sessionmaker

from app.calculos import valor_ganado as vg
from app.tcm import ejemplo
from app.tcm import plantilla as pl
from app.tcm.pronostico import pronosticos, tcpi

OCTETO = {"Content-Type": "application/octet-stream"}


@pytest.mark.parametrize(
    ("regla", "avance", "esperado"),
    [
        ("porcentaje", "60", "0.6"),
        ("0_100", "0", "0"),
        ("0_100", "99", "0"),
        ("0_100", "100", "1"),
        ("50_50", "0", "0"),
        ("50_50", "1", "0.5"),
        ("50_50", "99", "0.5"),
        ("50_50", "100", "1"),
    ],
)
def test_fraccion_ganada_segun_la_regla(regla, avance, esperado):
    assert vg.fraccion_ganada(D(avance), regla) == D(esperado)


def test_la_regla_cambia_el_ev_pero_no_el_avance_fisico():
    inicio = date(2026, 1, 1)
    partida = vg.DatosPartida(
        nombre="Muro",
        presupuesto=D("1000"),
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(days=9),
        avances=[vg.RegistroAvance(inicio + timedelta(days=4), D("60"))],
        regla_medicion="0_100",
    )
    r = vg.calcular_partida(partida, inicio + timedelta(days=5))
    assert r.porcentaje_avance == D("60")
    assert r.indicadores.ev == 0
    partida.regla_medicion = "50_50"
    assert vg.calcular_partida(partida, inicio + timedelta(days=5)).indicadores.ev == D("500")


def test_pronosticos_80r13_calculados_a_mano():
    ind = vg.calcular_indicadores(bac=D("1000"), pv=D("500"), ev=D("400"), ac=D("500"))
    assert (ind.cpi, ind.spi) == (D("0.8"), D("0.8"))
    p = {x.clave: x for x in pronosticos(ind)}
    assert p["atipico"].eac == D("1100.00")  # 500 + (1000 − 400)
    assert p["cpi"].eac == D("1250.00")  # 1000 / 0,8
    assert p["cpi_spi"].eac == D("1437.50")  # 500 + 600 / 0,64
    assert (p["cpi"].etc, p["cpi"].vac) == (D("750.00"), D("-250.00"))
    assert tcpi(ind) == D("1.2")  # 600 / 500: hay que rendir 20 % más para terminar en el BAC


def test_sin_gasto_ni_avance_no_hay_pronostico_por_indices():
    ind = vg.calcular_indicadores(bac=D("1000"), pv=D("100"), ev=D("0"), ac=D("0"))
    p = {x.clave: x for x in pronosticos(ind)}
    assert p["atipico"].eac == D("1000.00")
    assert p["cpi"].eac is None and p["cpi_spi"].eac is None and p["cpi"].vac is None


# --- API ---


def _obra_con_avance(cliente, dueno) -> tuple[int, dict]:
    obra = cliente.post("/api/obras", json={"nombre": "Prueba EVM", "fecha_inicio": "2026-01-05"}, headers=dueno).json()
    partida = cliente.post(
        f"/api/obras/{obra['id']}/partidas",
        json={"nombre": "Muro", "presupuesto": "1000", "fecha_inicio": "2026-01-05", "fecha_fin": "2026-01-14"},
        headers=dueno,
    ).json()
    r = cliente.post(
        f"/api/partidas/{partida['id']}/avances",
        json={"fecha": "2026-01-08", "porcentaje": "60"},
        headers=dueno,
    )
    assert r.status_code in (200, 201), r.text
    return obra["id"], partida


def test_cambiar_la_regla_de_medicion_cambia_el_ev(cliente, dueno):
    obra_id, partida = _obra_con_avance(cliente, dueno)
    url = f"/api/obras/{obra_id}/indicadores?corte=2026-01-09"
    assert cliente.get(url, headers=dueno).json()["indicadores"]["ev"] == 600
    r = cliente.put(f"/api/partidas/{partida['id']}/medicion", json={"regla_medicion": "0_100"}, headers=dueno)
    assert r.json()["regla_medicion"] == "0_100"
    assert cliente.get(url, headers=dueno).json()["indicadores"]["ev"] == 0
    r = cliente.put(f"/api/partidas/{partida['id']}/medicion", json={"regla_medicion": "otra"}, headers=dueno)
    assert r.status_code == 422


def test_gastos_generales_no_tienen_regla(cliente, dueno):
    obra_id, _ = _obra_con_avance(cliente, dueno)
    generales = next(
        p for p in cliente.get(f"/api/obras/{obra_id}/partidas", headers=dueno).json() if p["es_generales"]
    )
    r = cliente.put(f"/api/partidas/{generales['id']}/medicion", json={"regla_medicion": "0_100"}, headers=dueno)
    assert r.status_code == 409


def test_indicadores_traen_los_tres_pronosticos(cliente, dueno):
    obra_id, _ = _obra_con_avance(cliente, dueno)
    d = cliente.get(f"/api/obras/{obra_id}/indicadores?corte=2026-01-09", headers=dueno).json()
    assert [p["clave"] for p in d["pronosticos"]] == ["atipico", "cpi", "cpi_spi"]
    assert d["linea_base_version"] is None


def test_el_importador_lee_la_regla_de_medicion(cliente, dueno):
    contenido = pl.escribir_plantilla(ejemplo.datos())
    obra_id = cliente.post("/api/kit/importar", content=contenido, headers={**dueno, **OCTETO}).json()["obra"]["id"]
    partidas = {p["codigo"]: p for p in cliente.get(f"/api/obras/{obra_id}/partidas", headers=dueno).json()}
    assert partidas["6.5"]["regla_medicion"] == "0_100"
    assert partidas["1.1"]["regla_medicion"] == "50_50"
    assert partidas["4.2"]["regla_medicion"] == "porcentaje"

    libro = load_workbook(BytesIO(contenido))
    libro["Actividades"].cell(row=2, column=10).value = "30/70"
    salida = BytesIO()
    libro.save(salida)
    previa = cliente.post("/api/kit/importar/previa", content=salida.getvalue(), headers={**dueno, **OCTETO}).json()
    assert ("Actividades", 2, "Regla de medición") in {(e["hoja"], e["fila"], e["columna"]) for e in previa["errores"]}


def test_ejemplo_en_ejecucion_tiene_sobrecosto_y_atraso(tmp_path):
    from app import servicios
    from app.db import Base, crear_motor
    from app.modelos import ROL_DUENO, Usuario
    from app.tcm import exportar

    motor = crear_motor(f"sqlite:///{tmp_path / 'ej.db'}")
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as sesion:
        dueno = Usuario(nombre="Demo", correo="d@d.bo", rol=ROL_DUENO, clave_hash="x")
        sesion.add(dueno)
        sesion.flush()
        hoy = date(2026, 11, 24)
        obra = ejemplo.cargar_en_ejecucion(sesion, dueno, pl.escribir_plantilla(ejemplo.datos()), hoy)
        sesion.commit()
        _, r = servicios.calcular(sesion, obra, hoy)
        i = r.indicadores
        assert i.ac > 0 and i.ev > 0
        assert i.cpi < 1 and i.spi < 1
        p = {x.clave: x for x in pronosticos(i)}
        assert p["atipico"].eac < p["cpi"].eac < p["cpi_spi"].eac
        libro = load_workbook(
            BytesIO(exportar.exportar_estimado(sesion, obra, servicios.linea_base_vigente(sesion, obra.id)))
        )
        assert libro["Valor ganado"]._charts
    motor.dispose()
