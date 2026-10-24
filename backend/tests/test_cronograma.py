"""Obra, fases, actividades, fechas por predecesoras y dependencias circulares."""

from datetime import date

import pytest

from app.calculos.cronograma import (
    DatosActividad,
    DependenciaCircular,
    Enlace,
    calcular_fechas,
    calcular_holguras,
    fin_de,
    orden_topologico,
)
from tests.conftest import cabecera

INICIO = date(2026, 3, 2)  # lunes


def act(id_, dias, *predecesoras, manual=None):
    return DatosActividad(id_, dias, manual, tuple(Enlace(p) for p in predecesoras))


# --- Cálculo puro ---


class TestCalculoFechas:
    def test_duracion_incluye_el_primer_dia(self):
        assert fin_de(INICIO, 1) == INICIO
        assert fin_de(INICIO, 3) == date(2026, 3, 4)

    def test_sin_predecesoras_usa_fecha_manual_o_la_de_la_obra(self):
        fechas = calcular_fechas([act(1, 5), act(2, 2, manual=date(2026, 3, 10))], INICIO)
        assert (fechas[1].inicio, fechas[1].fin) == (INICIO, date(2026, 3, 6))
        assert (fechas[2].inicio, fechas[2].fin) == (date(2026, 3, 10), date(2026, 3, 11))

    def test_cadena_empieza_el_dia_siguiente(self):
        fechas = calcular_fechas([act(1, 5), act(2, 3, 1), act(3, 2, 2)], INICIO)
        assert fechas[2].inicio == date(2026, 3, 7)
        assert fechas[3].inicio == date(2026, 3, 10)
        assert fechas[3].fin == date(2026, 3, 11)

    def test_varias_predecesoras_espera_a_la_ultima(self):
        # Revoque (4) espera a muros (10 días) y a eléctrica (3 días): manda la que termina más tarde.
        fechas = calcular_fechas([act(1, 10), act(2, 3), act(4, 2, 1, 2)], INICIO)
        assert fechas[4].inicio == date(2026, 3, 12)

    def test_con_predecesoras_se_ignora_la_fecha_manual(self):
        fechas = calcular_fechas([act(1, 2), act(2, 1, 1, manual=date(2026, 12, 1))], INICIO)
        assert fechas[2].inicio == date(2026, 3, 4)

    def test_desfase_listo_para_esperas(self):
        datos = [act(1, 2), DatosActividad(2, 1, None, (Enlace(1, desfase_dias=3),))]
        assert calcular_fechas(datos, INICIO)[2].inicio == date(2026, 3, 7)

    def test_orden_independiente_de_la_entrada(self):
        fechas = calcular_fechas([act(3, 1, 2), act(2, 1, 1), act(1, 1)], INICIO)
        assert [fechas[i].inicio.day for i in (1, 2, 3)] == [2, 3, 4]


class TestRutaCritica:
    def test_dos_caminos_uno_critico_y_otro_con_holgura(self):
        # 1 → 2 (10 días) → 4 y 1 → 3 (3 días) → 4: el camino por 3 puede atrasarse 7 días.
        datos = [act(1, 2), act(2, 10, 1), act(3, 3, 1), act(4, 1, 2, 3)]
        h = calcular_holguras(datos, calcular_fechas(datos, INICIO))
        assert {i: h[i].dias for i in h} == {1: 0, 2: 0, 3: 7, 4: 0}
        assert sorted(i for i in h if h[i].critica) == [1, 2, 4]
        assert h[3].inicio_tardio == date(2026, 3, 11)

    def test_actividad_suelta_que_termina_antes(self):
        datos = [act(1, 10), act(2, 4)]
        h = calcular_holguras(datos, calcular_fechas(datos, INICIO))
        assert (h[1].dias, h[2].dias) == (0, 6)

    def test_el_desfase_cuenta_en_el_paso_hacia_atras(self):
        datos = [act(1, 2), DatosActividad(2, 3, None, (Enlace(1, desfase_dias=7),)), act(3, 5)]
        h = calcular_holguras(datos, calcular_fechas(datos, INICIO))
        # 1 y 2 suman 2 + 7 + 3 = 12 días: la 3 (5 días) tiene 7 de holgura.
        assert (h[1].dias, h[2].dias, h[3].dias) == (0, 0, 7)

    def test_sin_actividades(self):
        assert calcular_holguras([], {}) == {}


class TestDependenciaCircular:
    def test_ciclo_de_dos(self):
        with pytest.raises(DependenciaCircular) as e:
            orden_topologico([act(1, 1, 2), act(2, 1, 1)])
        assert sorted(e.value.ciclo) == [1, 2]

    def test_ciclo_largo_con_actividades_sueltas(self):
        with pytest.raises(DependenciaCircular) as e:
            orden_topologico([act(9, 1), act(1, 1, 3), act(2, 1, 1), act(3, 1, 2), act(4, 1, 3)])
        assert sorted(e.value.ciclo) == [1, 2, 3]

    def test_a_si_misma(self):
        with pytest.raises(DependenciaCircular):
            orden_topologico([act(1, 1, 1)])


# --- API ---


def crear_obra(http, dueno, **extra):
    # `http` y no `cliente`: "cliente" también es un campo de la obra.
    datos = {"nombre": "Casa Choque", "fecha_inicio": INICIO.isoformat()}
    datos.update(extra)
    r = http.post("/api/obras", json=datos, headers=dueno)
    assert r.status_code == 201, r.text
    return r.json()


def crear_fase(cliente, dueno, obra_id, nombre):
    r = cliente.post(f"/api/obras/{obra_id}/fases", json={"nombre": nombre}, headers=dueno)
    assert r.status_code == 201, r.text
    return next(f for f in r.json()["fases"] if f["nombre"] == nombre)


def crear_actividad(cliente, dueno, fase_id, nombre, dias, predecesoras=(), **extra):
    datos = {"nombre": nombre, "duracion_dias": dias, "predecesoras": list(predecesoras), **extra}
    r = cliente.post(f"/api/fases/{fase_id}/actividades", json=datos, headers=dueno)
    assert r.status_code == 201, r.text
    return r.json(), actividad(r.json(), nombre)


def actividad(cronograma, nombre):
    return next(a for f in cronograma["fases"] for a in f["actividades"] if a["nombre"] == nombre)


def test_obra_con_cliente_moneda_y_presupuesto(cliente, dueno):
    obra = crear_obra(cliente, dueno, cliente="Familia Choque", moneda="USD", presupuesto_total="85000.50")
    assert (obra["cliente"], obra["moneda"], obra["presupuesto_total"]) == ("Familia Choque", "USD", 85000.5)
    # Sin fecha de fin: arranca igual a la de inicio.
    assert obra["fecha_fin"] == INICIO.isoformat()
    sin_presupuesto = crear_obra(cliente, dueno, nombre="Muro perimetral")
    assert sin_presupuesto["presupuesto_total"] is None and sin_presupuesto["moneda"] == "Bs"

    r = cliente.put(
        f"/api/obras/{obra['id']}",
        json={"nombre": "Casa Choque II", "fecha_inicio": INICIO.isoformat(), "moneda": "Bs", "cliente": "J. Choque"},
        headers=dueno,
    )
    assert r.status_code == 200, r.text
    assert (r.json()["nombre"], r.json()["moneda"], r.json()["presupuesto_total"]) == ("Casa Choque II", "Bs", None)
    assert [o["nombre"] for o in cliente.get("/api/obras", headers=dueno).json()] == [
        "Casa Choque II",
        "Muro perimetral",
    ]

    for malo in ({"moneda": "EUR"}, {"presupuesto_total": -1}, {"fecha_fin": "2026-01-01"}):
        assert (
            cliente.post(
                "/api/obras", json={"nombre": "X obra", "fecha_inicio": "2026-03-02", **malo}, headers=dueno
            ).status_code
            == 422
        )


def test_fases_crear_editar_ordenar_borrar(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    gruesa = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    inst = crear_fase(cliente, dueno, obra["id"], "Instalaciones")
    acab = crear_fase(cliente, dueno, obra["id"], "Acabados")

    r = cliente.put(f"/api/fases/{inst['id']}", json={"nombre": "Instalaciones eléctricas"}, headers=dueno)
    assert r.status_code == 200

    ids = [acab["id"], gruesa["id"], inst["id"]]
    r = cliente.put(f"/api/obras/{obra['id']}/fases/orden", json={"ids": ids}, headers=dueno)
    assert [f["nombre"] for f in r.json()["fases"]] == ["Acabados", "Obra gruesa", "Instalaciones eléctricas"]
    # El orden debe nombrar todas las fases.
    r = cliente.put(f"/api/obras/{obra['id']}/fases/orden", json={"ids": ids[:2]}, headers=dueno)
    assert r.status_code == 422

    r = cliente.delete(f"/api/fases/{acab['id']}", headers=dueno)
    assert [f["nombre"] for f in r.json()["fases"]] == ["Obra gruesa", "Instalaciones eléctricas"]
    assert cliente.delete(f"/api/fases/{acab['id']}", headers=dueno).status_code == 404


def test_actividades_y_fechas_por_predecesoras(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    gruesa = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    inst = crear_fase(cliente, dueno, obra["id"], "Instalaciones")

    _, cimientos = crear_actividad(cliente, dueno, gruesa["id"], "Cimientos", 5)
    assert (cimientos["fecha_inicio"], cimientos["fecha_fin"]) == ("2026-03-02", "2026-03-06")
    _, muros = crear_actividad(cliente, dueno, gruesa["id"], "Muros", 10, [cimientos["id"]])
    assert muros["fecha_inicio"] == "2026-03-07"
    _, electrica = crear_actividad(cliente, dueno, inst["id"], "Eléctrica", 3, inicio_manual="2026-03-20")
    assert electrica["fecha_inicio"] == "2026-03-20"
    crono, revoque = crear_actividad(cliente, dueno, inst["id"], "Revoque", 4, [muros["id"], electrica["id"]])
    # Muros termina el 16/03 y eléctrica el 22/03: manda la última.
    assert (revoque["fecha_inicio"], revoque["fecha_fin"]) == ("2026-03-23", "2026-03-26")
    assert revoque["predecesoras"] == sorted([muros["id"], electrica["id"]])
    assert crono["fecha_fin"] == "2026-03-26"
    # Ruta crítica: eléctrica → revoque. Cimientos y muros terminan el 16/03 y podrían atrasarse 6 días.
    assert [(a["nombre"], a["holgura_dias"]) for f in crono["fases"] for a in f["actividades"]] == [
        ("Cimientos", 6),
        ("Muros", 6),
        ("Eléctrica", 0),
        ("Revoque", 0),
    ]
    assert actividad(crono, "Revoque")["critica"] and not actividad(crono, "Muros")["critica"]
    assert cliente.get(f"/api/obras/{obra['id']}", headers=dueno).json()["fecha_fin"] == "2026-03-26"

    # Al alargar cimientos se corre todo lo que depende de él.
    r = cliente.put(
        f"/api/actividades/{cimientos['id']}", json={"nombre": "Cimientos", "duracion_dias": 15}, headers=dueno
    )
    assert r.status_code == 200, r.text
    assert actividad(r.json(), "Muros")["fecha_inicio"] == "2026-03-17"
    assert actividad(r.json(), "Revoque")["fecha_inicio"] == "2026-03-27"

    # Si la obra empieza después, las actividades sin fecha propia la siguen.
    r = cliente.put(
        f"/api/obras/{obra['id']}", json={"nombre": "Casa Choque", "fecha_inicio": "2026-03-09"}, headers=dueno
    )
    assert r.status_code == 200
    crono = cliente.get(f"/api/obras/{obra['id']}/cronograma", headers=dueno).json()
    assert actividad(crono, "Cimientos")["fecha_inicio"] == "2026-03-09"
    assert actividad(crono, "Eléctrica")["fecha_inicio"] == "2026-03-20"

    # Mover de fase y quitar predecesoras.
    r = cliente.put(
        f"/api/actividades/{revoque['id']}",
        json={"nombre": "Revoque", "duracion_dias": 4, "fase_id": gruesa["id"], "inicio_manual": "2026-04-01"},
        headers=dueno,
    )
    revoque = actividad(r.json(), "Revoque")
    assert (revoque["fase_id"], revoque["predecesoras"], revoque["fecha_inicio"]) == (gruesa["id"], [], "2026-04-01")

    # Borrar una actividad suelta a sus sucesoras.
    r = cliente.delete(f"/api/actividades/{cimientos['id']}", headers=dueno)
    assert actividad(r.json(), "Muros")["predecesoras"] == []
    assert actividad(r.json(), "Muros")["fecha_inicio"] == "2026-03-09"

    # Borrar la fase borra sus actividades.
    r = cliente.delete(f"/api/fases/{gruesa['id']}", headers=dueno)
    assert [a["nombre"] for f in r.json()["fases"] for a in f["actividades"]] == ["Eléctrica"]


def test_dependencia_circular_bloqueada(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    _, a = crear_actividad(cliente, dueno, fase["id"], "Excavación", 2)
    _, b = crear_actividad(cliente, dueno, fase["id"], "Cimientos", 3, [a["id"]])
    _, c = crear_actividad(cliente, dueno, fase["id"], "Muros", 4, [b["id"]])

    r = cliente.put(
        f"/api/actividades/{a['id']}",
        json={"nombre": "Excavación", "duracion_dias": 2, "predecesoras": [c["id"]]},
        headers=dueno,
    )
    assert r.status_code == 422
    assert "circular" in r.json()["detail"] and "Muros" in r.json()["detail"]

    r = cliente.put(
        f"/api/actividades/{a['id']}",
        json={"nombre": "Excavación", "duracion_dias": 2, "predecesoras": [a["id"]]},
        headers=dueno,
    )
    assert r.status_code == 422

    # Nada cambió.
    crono = cliente.get(f"/api/obras/{obra['id']}/cronograma", headers=dueno).json()
    assert actividad(crono, "Excavación")["predecesoras"] == []
    assert actividad(crono, "Muros")["fecha_inicio"] == "2026-03-07"


def test_validaciones_y_permisos_del_cronograma(cliente, dueno):
    obra = crear_obra(cliente, dueno)
    otra = crear_obra(cliente, dueno, nombre="Otra obra")
    fase = crear_fase(cliente, dueno, obra["id"], "Obra gruesa")
    fase_otra = crear_fase(cliente, dueno, otra["id"], "Acabados")
    _, ajena = crear_actividad(cliente, dueno, fase_otra["id"], "Pintura", 2)
    _, a = crear_actividad(cliente, dueno, fase["id"], "Excavación", 2)

    malos = [
        {"nombre": "X", "duracion_dias": 0},
        {"nombre": "", "duracion_dias": 1},
        {"nombre": "X", "duracion_dias": 1, "predecesoras": [ajena["id"]]},
        {"nombre": "X", "duracion_dias": 1, "predecesoras": [a["id"], a["id"]]},
    ]
    for datos in malos:
        assert cliente.post(f"/api/fases/{fase['id']}/actividades", json=datos, headers=dueno).status_code == 422, datos
    r = cliente.put(
        f"/api/actividades/{a['id']}",
        json={"nombre": "X", "duracion_dias": 1, "fase_id": fase_otra["id"]},
        headers=dueno,
    )
    assert r.status_code == 422

    # Otro dueño no ve ni toca el cronograma.
    r = cliente.post("/api/sesion/registro", json={"nombre": "Luis", "correo": "luis@obra.bo", "clave": "clave-segura"})
    otro = cabecera(r.json()["token"])
    assert cliente.get(f"/api/obras/{obra['id']}/cronograma", headers=otro).status_code == 404
    assert cliente.post(f"/api/obras/{obra['id']}/fases", json={"nombre": "X"}, headers=otro).status_code == 404
    assert cliente.delete(f"/api/actividades/{a['id']}", headers=otro).status_code == 404
