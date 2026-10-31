import os
import subprocess
import sys
from pathlib import Path

from app import config
from app.seguridad import ControlIntentos

RAIZ_BACKEND = Path(__file__).resolve().parent.parent


class Reloj:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self):
        return self.ahora


def test_control_intentos_bloquea_y_caduca():
    reloj = Reloj()
    control = ControlIntentos(reloj)
    for _ in range(3):
        assert control.segundos_bloqueado("x", 3, 60) == 0
        control.registrar_fallo("x")
        reloj.ahora += 10
    # Tercer fallo hace 10 s, primero hace 30 s: faltan 30 s para que caduque el primero.
    assert control.segundos_bloqueado("x", 3, 60) == 30
    assert control.segundos_bloqueado("otro", 3, 60) == 0
    reloj.ahora += 31
    assert control.segundos_bloqueado("x", 3, 60) == 0


def test_control_intentos_limpiar():
    control = ControlIntentos(Reloj())
    control.registrar_fallo("x")
    control.registrar_fallo("x")
    control.limpiar("x")
    assert control.segundos_bloqueado("x", 1, 60) == 0


def _ingresar(cliente, usuario, clave):
    return cliente.post("/api/sesion/ingreso", json={"usuario": usuario, "clave": clave})


def test_ingreso_se_bloquea_tras_fallos(cliente, dueno, monkeypatch):
    monkeypatch.setattr(config, "INTENTOS_POR_USUARIO", 3)
    for _ in range(3):
        assert _ingresar(cliente, "ana@obra.bo", "mala").status_code == 401
    r = _ingresar(cliente, "ANA@obra.bo", "clave-segura")
    assert r.status_code == 429
    assert "Demasiados intentos" in r.json()["detail"]
    assert int(r.headers["Retry-After"]) > 0


def test_ingreso_correcto_reinicia_el_conteo(cliente, dueno, monkeypatch):
    monkeypatch.setattr(config, "INTENTOS_POR_USUARIO", 3)
    for _ in range(2):
        _ingresar(cliente, "ana@obra.bo", "mala")
    assert _ingresar(cliente, "ana@obra.bo", "clave-segura").status_code == 200
    for _ in range(2):
        _ingresar(cliente, "ana@obra.bo", "mala")
    assert _ingresar(cliente, "ana@obra.bo", "clave-segura").status_code == 200


def test_bloqueo_por_ip_con_muchas_cuentas(cliente, monkeypatch):
    monkeypatch.setattr(config, "INTENTOS_POR_IP", 4)
    for i in range(4):
        assert _ingresar(cliente, f"7000000{i}", "123456").status_code == 401
    assert _ingresar(cliente, "70000009", "123456").status_code == 429


PG = "postgresql://usuario:clave@localhost:5432/verdad_contable"


def _importar_config(**variables):
    entorno = {k: v for k, v in os.environ.items() if k not in ("ENTORNO", "CLAVE_SECRETA", "DATABASE_URL")}
    entorno.update(variables)
    return subprocess.run(
        [sys.executable, "-c", "import app.config"], cwd=RAIZ_BACKEND, env=entorno, capture_output=True, text=True
    )


def test_produccion_exige_clave_secreta():
    r = _importar_config(ENTORNO="produccion")
    assert r.returncode != 0
    assert "CLAVE_SECRETA" in r.stderr
    assert _importar_config(ENTORNO="produccion", CLAVE_SECRETA="corta").returncode != 0
    assert _importar_config(ENTORNO="produccion", CLAVE_SECRETA="x" * 40, DATABASE_URL=PG).returncode == 0


def test_produccion_no_arranca_con_sqlite():
    r = _importar_config(ENTORNO="produccion", CLAVE_SECRETA="x" * 40)
    assert r.returncode != 0
    assert "DATABASE_URL" in r.stderr
