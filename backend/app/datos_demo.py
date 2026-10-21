"""Carga una obra de ejemplo para probar la app.

Uso:  python -m app.datos_demo
Crea (si no existen) estos usuarios:
  dueño     demo@verdadcontable.bo / demo1234
  encargado 70000000 / PIN 123456
"""

import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app import servicios
from app.db import FabricaSesion
from app.modelos import ROL_DUENO, ROL_ENCARGADO, Asignacion, Avance, CierreDia, Gasto, Hito, Obra, Partida, Usuario
from app.seguridad import cifrar_clave

CORREO_DEMO = "demo@verdadcontable.bo"

# (código, nombre, fase, día de inicio, duración en días, presupuesto Bs, ritmo de avance, ritmo de gasto)
# Ritmo 1.0 = va según lo previsto; menor = atrasado; mayor gasto = gasta de más.
PARTIDAS = [
    ("1", "Excavación y cimientos", "Obra gruesa", 0, 14, 28000, 1.00, 0.95),
    ("2", "Columnas y vigas 1er piso", "Obra gruesa", 10, 20, 46000, 0.95, 1.10),
    ("3", "Muros de ladrillo 1er piso", "Obra gruesa", 20, 25, 38000, 0.80, 1.05),
    ("4", "Losa 2do piso", "Obra gruesa", 40, 15, 52000, 0.60, 1.25),
    ("5", "Muros 2do piso", "Obra gruesa", 55, 20, 34000, 1.00, 1.00),
    ("6", "Instalación eléctrica", "Instalaciones", 60, 25, 18000, 1.00, 1.00),
    ("7", "Instalación sanitaria", "Instalaciones", 60, 25, 16000, 1.00, 1.00),
    ("8", "Revoques y pisos", "Acabados", 80, 25, 30000, 1.00, 1.00),
]
DIAS_TRANSCURRIDOS = 48
TIPOS = ["material", "material", "material", "mano_obra", "mano_obra", "transporte", "subcontrato"]
DESCRIPCIONES = {
    "material": ["Cemento 20 bolsas", "Fierro de 3/8", "Ladrillo 6 huecos", "Arena y grava", "Clavos y alambre"],
    "mano_obra": ["Jornales albañiles", "Pago ayudantes semana", "Jornal maestro"],
    "transporte": ["Flete volqueta", "Taxi carga materiales"],
    "subcontrato": ["Encofrado (subcontrato)", "Fierrero a destajo"],
}


def cargar() -> None:
    aleatorio = random.Random(7)
    hoy = servicios.hoy()
    inicio = hoy - timedelta(days=DIAS_TRANSCURRIDOS)
    with FabricaSesion() as sesion:
        if sesion.scalar(select(Usuario).where(Usuario.correo == CORREO_DEMO)):
            print("Los datos de demostración ya existen.")
            return
        dueno = Usuario(
            nombre="Constructora Demo", correo=CORREO_DEMO, rol=ROL_DUENO, clave_hash=cifrar_clave("demo1234")
        )
        sesion.add(dueno)
        sesion.flush()
        encargado = Usuario(
            nombre="Don Pedro (encargado)",
            telefono="70000000",
            rol=ROL_ENCARGADO,
            clave_hash=cifrar_clave("123456"),
            dueno_id=dueno.id,
        )
        sesion.add(encargado)
        obra = Obra(
            dueno_id=dueno.id,
            nombre="Casa familia Quispe",
            ubicacion="Zona Sur, La Paz",
            fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(days=105),
        )
        sesion.add(obra)
        sesion.flush()
        sesion.add(Asignacion(usuario_id=encargado.id, obra_id=obra.id))
        generales = servicios.partida_generales(sesion, obra)

        for orden, (codigo, nombre, fase, desde, dias, presupuesto, ritmo_avance, ritmo_gasto) in enumerate(
            PARTIDAS, 1
        ):
            p_inicio = inicio + timedelta(days=desde)
            p_fin = p_inicio + timedelta(days=dias - 1)
            partida = Partida(
                obra_id=obra.id,
                codigo=codigo,
                nombre=nombre,
                fase=fase,
                fecha_inicio=p_inicio,
                fecha_fin=p_fin,
                presupuesto=Decimal(presupuesto),
                orden=orden,
            )
            sesion.add(partida)
            sesion.flush()
            dia = p_inicio
            while dia <= min(p_fin, hoy - timedelta(days=1)):
                fraccion_plan = ((dia - p_inicio).days + 1) / dias
                # Avance cada 3 días.
                if (dia - p_inicio).days % 3 == 2 or dia == p_fin:
                    pct = min(100, round(fraccion_plan * 100 * ritmo_avance / 5) * 5)
                    sesion.add(
                        Avance(partida_id=partida.id, fecha=dia, porcentaje=Decimal(pct), usuario_id=encargado.id)
                    )
                # Uno o dos gastos por día.
                gasto_dia = presupuesto / dias * ritmo_gasto
                for _ in range(aleatorio.choice([1, 1, 2])):
                    tipo = aleatorio.choice(TIPOS)
                    monto = Decimal(str(round(gasto_dia * aleatorio.uniform(0.4, 0.9), 1)))
                    sesion.add(
                        Gasto(
                            obra_id=obra.id,
                            partida_id=partida.id,
                            fecha=dia,
                            monto=monto,
                            tipo=tipo,
                            descripcion=aleatorio.choice(DESCRIPCIONES[tipo]),
                            con_factura=aleatorio.random() < 0.45,
                            usuario_id=encargado.id,
                        )
                    )
                dia += timedelta(days=1)

        for d in range(DIAS_TRANSCURRIDOS):
            fecha = inicio + timedelta(days=d)
            if d % 5 == 0:
                sesion.add(
                    Gasto(
                        obra_id=obra.id,
                        partida_id=generales.id,
                        fecha=fecha,
                        monto=Decimal(aleatorio.choice([35, 50, 80, 120])),
                        tipo="caja_chica",
                        descripcion="Refrigerio y agua",
                        con_factura=False,
                        usuario_id=encargado.id,
                    )
                )
        sesion.flush()
        # Días cerrados hasta anteayer (ayer queda sin cerrar para ver la alerta).
        for d in range(DIAS_TRANSCURRIDOS - 1):
            fecha = inicio + timedelta(days=d)
            sesion.add(
                CierreDia(
                    obra_id=obra.id,
                    fecha=fecha,
                    total_dia=servicios.gastado_en(sesion, obra.id, fecha),
                    acumulado=servicios.gastado_hasta(sesion, obra.id, fecha),
                    usuario_id=encargado.id,
                )
            )
        sesion.add_all(
            [
                Hito(
                    obra_id=obra.id,
                    nombre="Cimientos terminados",
                    fecha_prevista=inicio + timedelta(days=13),
                    fecha_real=inicio + timedelta(days=14),
                ),
                Hito(obra_id=obra.id, nombre="Obra gruesa terminada", fecha_prevista=inicio + timedelta(days=74)),
                Hito(obra_id=obra.id, nombre="Entrega de la casa", fecha_prevista=obra.fecha_fin),
            ]
        )
        sesion.commit()
        print("Listo. Dueño: demo@verdadcontable.bo / demo1234 · Encargado: 70000000 / PIN 123456")


if __name__ == "__main__":
    cargar()
