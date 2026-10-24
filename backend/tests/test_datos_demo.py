from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import datos_demo
from app.db import Base, crear_motor
from app.modelos import Actividad, Gasto, Usuario


def test_datos_demo_cargan_y_no_se_duplican(tmp_path, monkeypatch):
    motor = crear_motor(f"sqlite:///{tmp_path / 'demo.db'}")
    Base.metadata.create_all(motor)
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    monkeypatch.setattr(datos_demo, "FabricaSesion", fabrica)

    datos_demo.cargar()
    datos_demo.cargar()

    with fabrica() as sesion:
        assert sesion.scalar(select(func.count()).select_from(Usuario)) == 2
        assert sesion.scalar(select(func.count()).select_from(Actividad)) == len(datos_demo.PARTIDAS)
        assert sesion.scalar(select(func.count()).select_from(Gasto)) > 0
    motor.dispose()
