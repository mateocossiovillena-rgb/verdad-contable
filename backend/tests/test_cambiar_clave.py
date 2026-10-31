import pytest
from sqlalchemy.orm import sessionmaker

from app import cambiar_clave
from app.db import Base, crear_motor
from app.modelos import ROL_DUENO, ROL_ENCARGADO, Usuario
from app.seguridad import cifrar_clave, verificar_clave


def test_pone_clave_temporal_solo_a_duenos(tmp_path, monkeypatch):
    motor = crear_motor(f"sqlite:///{tmp_path / 'clave.db'}")
    Base.metadata.create_all(motor)
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    monkeypatch.setattr(cambiar_clave, "FabricaSesion", fabrica)
    with fabrica() as sesion:
        sesion.add_all(
            [
                Usuario(nombre="Ana", correo="ana@obra.bo", rol=ROL_DUENO, clave_hash=cifrar_clave("vieja-clave")),
                Usuario(nombre="Pedro", telefono="70000001", rol=ROL_ENCARGADO, clave_hash=cifrar_clave("123456")),
            ]
        )
        sesion.commit()

    nueva = cambiar_clave.cambiar_clave(" Ana@Obra.bo ")

    assert len(nueva) == 10 and set(nueva) <= set(cambiar_clave.LETRAS)
    with fabrica() as sesion:
        ana = sesion.query(Usuario).filter_by(correo="ana@obra.bo").one()
        assert verificar_clave(nueva, ana.clave_hash)
        assert not verificar_clave("vieja-clave", ana.clave_hash)
    with pytest.raises(SystemExit):
        cambiar_clave.cambiar_clave("nadie@obra.bo")
    motor.dispose()
