"""Casos calculados a mano para el módulo de valor ganado."""

from datetime import date
from decimal import Decimal as D

import pytest

from app.calculos.valor_ganado import (
    DatosPartida,
    RegistroAvance,
    RegistroGasto,
    avance_a_la_fecha,
    calcular_curva,
    calcular_indicadores,
    calcular_obra,
    calcular_partida,
    formatear_bs,
    fraccion_planificada,
    frases_resumen,
    semaforo,
)

INICIO = date(2026, 1, 1)
FIN = date(2026, 1, 10)  # 10 días incluidos


def muro(**extra):
    datos = dict(nombre="Muro 2do piso", presupuesto=D("10000"), fecha_inicio=INICIO, fecha_fin=FIN)
    datos.update(extra)
    return DatosPartida(**datos)


class TestFraccionPlanificada:
    def test_antes_del_inicio_es_cero(self):
        assert fraccion_planificada(INICIO, FIN, date(2025, 12, 31)) == 0

    def test_primer_dia_es_un_decimo(self):
        assert fraccion_planificada(INICIO, FIN, INICIO) == D("0.1")

    def test_mitad(self):
        assert fraccion_planificada(INICIO, FIN, date(2026, 1, 5)) == D("0.5")

    def test_en_y_despues_del_fin_es_uno(self):
        assert fraccion_planificada(INICIO, FIN, FIN) == 1
        assert fraccion_planificada(INICIO, FIN, date(2026, 3, 1)) == 1

    def test_partida_de_un_dia(self):
        assert fraccion_planificada(INICIO, INICIO, INICIO) == 1

    def test_sin_fechas_es_none(self):
        assert fraccion_planificada(None, FIN, INICIO) is None
        assert fraccion_planificada(INICIO, None, INICIO) is None

    def test_fin_antes_de_inicio_es_error(self):
        with pytest.raises(ValueError):
            fraccion_planificada(FIN, INICIO, INICIO)


class TestAvanceALaFecha:
    def test_sin_registros_es_cero(self):
        assert avance_a_la_fecha([], INICIO) == 0

    def test_toma_el_ultimo_hasta_el_corte(self):
        avances = [
            RegistroAvance(date(2026, 1, 2), D("20")),
            RegistroAvance(date(2026, 1, 4), D("50")),
            RegistroAvance(date(2026, 1, 8), D("90")),
        ]
        assert avance_a_la_fecha(avances, date(2026, 1, 5)) == D("50")

    def test_mismo_dia_manda_el_ultimo_registrado(self):
        avances = [RegistroAvance(INICIO, D("40")), RegistroAvance(INICIO, D("30"))]
        assert avance_a_la_fecha(avances, INICIO) == D("30")

    def test_registro_tardio_de_fecha_anterior(self):
        avances = [RegistroAvance(date(2026, 1, 5), D("60")), RegistroAvance(date(2026, 1, 3), D("30"))]
        assert avance_a_la_fecha(avances, date(2026, 1, 6)) == D("60")


class TestIndicadores:
    def test_caso_tipico(self):
        # BAC 10 000, a mitad de plazo, 30 % de avance, 4 500 gastados.
        r = calcular_partida(
            muro(
                avances=[RegistroAvance(date(2026, 1, 5), D("30"))],
                gastos=[RegistroGasto(date(2026, 1, 2), D("3000")), RegistroGasto(date(2026, 1, 5), D("1500"))],
            ),
            date(2026, 1, 5),
        )
        i = r.indicadores
        assert (i.bac, i.pv, i.ev, i.ac) == (D("10000"), D("5000"), D("3000"), D("4500"))
        assert i.sv == D("-2000")
        assert i.cv == D("-1500")
        assert i.spi == D("0.6")
        assert i.cpi.quantize(D("0.0001")) == D("0.6667")
        assert i.eac == D("15000")
        assert i.avance_esperado_por_gasto == D("0.45")
        assert i.avance_real == D("0.3")
        assert i.avance_planificado == D("0.5")

    def test_sin_gastos_cpi_y_eac_sin_dato(self):
        i = calcular_partida(muro(avances=[RegistroAvance(INICIO, D("10"))]), INICIO).indicadores
        assert i.ac == 0
        assert i.cpi is None
        assert i.eac is None

    def test_gasto_sin_avance_eac_sin_dato(self):
        i = calcular_partida(muro(gastos=[RegistroGasto(INICIO, D("500"))]), INICIO).indicadores
        assert i.cpi == 0
        assert i.eac is None

    def test_antes_de_empezar_spi_sin_dato(self):
        i = calcular_partida(muro(), date(2025, 12, 1)).indicadores
        assert i.pv == 0
        assert i.spi is None

    def test_sin_presupuesto(self):
        i = calcular_indicadores(D("0"), D("0"), D("0"), D("100"))
        assert i.avance_real is None
        assert i.avance_esperado_por_gasto is None

    def test_gastos_futuros_no_cuentan(self):
        r = calcular_partida(muro(gastos=[RegistroGasto(date(2026, 1, 9), D("800"))]), date(2026, 1, 5))
        assert r.indicadores.ac == 0

    def test_terminada_y_en_presupuesto(self):
        r = calcular_partida(
            muro(avances=[RegistroAvance(FIN, D("100"))], gastos=[RegistroGasto(FIN, D("9000"))]),
            FIN,
        )
        i = r.indicadores
        assert i.ev == i.pv == D("10000")
        assert i.spi == 1
        assert i.cpi.quantize(D("0.0001")) == D("1.1111")
        assert i.eac == D("9000")


class TestAdvertencias:
    def codigos(self, partida, corte):
        return {a.codigo for a in calcular_partida(partida, corte).advertencias}

    def test_sin_fechas(self):
        assert "sin_fechas" in self.codigos(muro(fecha_inicio=None, fecha_fin=None), INICIO)

    def test_gasto_supera_presupuesto(self):
        assert "gasto_supera_presupuesto" in self.codigos(muro(gastos=[RegistroGasto(INICIO, D("12000"))]), INICIO)

    def test_gasto_sin_avance_despues_de_7_dias(self):
        p = muro(gastos=[RegistroGasto(INICIO, D("100"))])
        assert "gasto_sin_avance" not in self.codigos(p, date(2026, 1, 8))
        assert "gasto_sin_avance" in self.codigos(p, date(2026, 1, 9))

    def test_terminada_sin_gastos(self):
        assert "terminada_sin_gastos" in self.codigos(muro(avances=[RegistroAvance(INICIO, D("100"))]), INICIO)

    def test_gastos_generales_sin_presupuesto(self):
        p = DatosPartida(nombre="Generales", presupuesto=D("0"), gastos=[RegistroGasto(INICIO, D("50"))])
        assert self.codigos(p, INICIO) == {"gasto_sin_presupuesto"}


class TestObra:
    def test_suma_partidas(self):
        a = muro(avances=[RegistroAvance(date(2026, 1, 5), D("50"))], gastos=[RegistroGasto(INICIO, D("6000"))])
        b = DatosPartida(
            nombre="Losa",
            presupuesto=D("20000"),
            fecha_inicio=date(2026, 1, 6),
            fecha_fin=date(2026, 1, 15),
        )
        generales = DatosPartida(nombre="Generales", presupuesto=D("0"), gastos=[RegistroGasto(INICIO, D("400"))])
        r = calcular_obra([a, b, generales], date(2026, 1, 5))
        i = r.indicadores
        assert i.bac == D("30000")
        assert i.pv == D("5000")
        assert i.ev == D("5000")
        assert i.ac == D("6400")
        assert i.spi == 1
        assert {x.codigo for x in r.advertencias} == {"proyeccion_supera_presupuesto"}

    def test_obra_vacia(self):
        i = calcular_obra([], INICIO).indicadores
        assert i.bac == 0 and i.spi is None and i.cpi is None

    def test_curva_no_muestra_futuro(self):
        p = muro(gastos=[RegistroGasto(INICIO, D("100"))])
        puntos = calcular_curva([p], [INICIO, date(2026, 1, 5), FIN], hoy=date(2026, 1, 5))
        assert [x.pv for x in puntos] == [D("1000"), D("5000"), D("10000")]
        assert puntos[1].ac == D("100")
        assert puntos[2].ac is None and puntos[2].ev is None


class TestGastosGenerales:
    def generales(self, **extra):
        datos = dict(nombre="Gastos generales", presupuesto=D("2000"), es_generales=True)
        datos.update(extra)
        return DatosPartida(**datos)

    def test_sin_fechas_ni_avance_no_da_avisos(self):
        g = self.generales(gastos=[RegistroGasto(date(2026, 1, 1), D("100"))])
        assert calcular_partida(g, date(2026, 2, 1)).advertencias == []

    def test_se_gana_con_el_tiempo(self):
        # Sin avance físico: EV = PV, así que su SPI es 1 y su CPI compara gasto contra tiempo.
        g = self.generales(fecha_inicio=INICIO, fecha_fin=FIN, gastos=[RegistroGasto(INICIO, D("1500"))])
        i = calcular_partida(g, date(2026, 1, 5)).indicadores
        assert i.pv == i.ev == D("1000")
        assert i.spi == 1
        assert i.cpi == D("1000") / D("1500")

    def test_no_atrasa_a_la_obra(self):
        corte = date(2026, 1, 5)
        a_tiempo = muro(avances=[RegistroAvance(corte, D("50"))])
        g = self.generales(fecha_inicio=INICIO, fecha_fin=FIN)
        assert calcular_obra([a_tiempo, g], corte).indicadores.spi == 1

    def test_sigue_avisando_si_supera_su_presupuesto(self):
        g = self.generales(gastos=[RegistroGasto(INICIO, D("2500"))])
        codigos = [a.codigo for a in calcular_partida(g, FIN).advertencias]
        assert codigos == ["gasto_supera_presupuesto"]


class TestSemaforoYFrases:
    def test_semaforo(self):
        amarillo, rojo = D("0.9"), D("0.8")
        assert semaforo(calcular_indicadores(D("100"), D("50"), D("50"), D("50")), amarillo, rojo) == "verde"
        assert semaforo(calcular_indicadores(D("100"), D("50"), D("44"), D("44")), amarillo, rojo) == "amarillo"
        assert semaforo(calcular_indicadores(D("100"), D("50"), D("50"), D("70")), amarillo, rojo) == "rojo"
        assert semaforo(calcular_indicadores(D("100"), D("0"), D("0"), D("0")), amarillo, rojo) == "sin_dato"
        assert semaforo(calcular_indicadores(D("100"), D("0"), D("0"), D("120")), amarillo, rojo) == "rojo"
        # Partida sin presupuesto (gastos generales): no tiene semáforo.
        assert semaforo(calcular_indicadores(D("0"), D("0"), D("0"), D("50")), amarillo, rojo) == "sin_dato"

    def test_formato_bs(self):
        assert formatear_bs(D("7054.654")) == "Bs 7.054,65"
        assert formatear_bs(D("-1234567.5")) == "Bs -1.234.567,50"

    def test_frases(self):
        i = calcular_indicadores(D("10000"), D("5000"), D("3000"), D("4500"))
        frases = frases_resumen(i)
        assert frases[0] == "Gastaste el 45 % del presupuesto y avanzaste el 30 %."
        assert "Estás gastando más de lo que avanzas." in frases
        assert "Según el cronograma deberías ir en 50 %: vas atrasado." in frases
