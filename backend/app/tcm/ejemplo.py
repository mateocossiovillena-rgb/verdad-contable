"""Obra de ejemplo del Kit TCM: vivienda unifamiliar de ~120 m² en Santa Cruz de la Sierra.

Uso:  python -m app.tcm.ejemplo
  1. Escribe la plantilla llena en `kit/ejemplo/vivienda-120m2.xlsx`.
  2. La importa con el mismo importador que usa la app (así el ejemplo prueba el importador) en la cuenta
     demo (demo@verdadcontable.bo / demo1234, la crea si falta) y aprueba la línea base v1.

Los precios son ILUSTRATIVOS (referencia de mercado de Santa Cruz, noviembre de 2026): sirven para mostrar el
método, no para cotizar una obra real.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.modelos import Obra, Usuario
from app.tcm import plantilla as pl
from app.tcm import servicio as ts

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
ARCHIVO = RAIZ_PROYECTO / "kit" / "ejemplo" / "vivienda-120m2.xlsx"
NOMBRE_OBRA = "Vivienda unifamiliar 120 m² — Urb. Las Palmas (ejemplo Kit TCM)"
INICIO = date(2026, 12, 7)
FECHA_PRECIOS = date(2026, 11, 15)

# Precios unitarios (Bs) de insumos, para no repetirlos en cada actividad.
P = {
    "cemento": ("Cemento IP-30", "bolsa", 62),
    "arena": ("Arena fina", "m³", 120),
    "grava": ("Grava", "m³", 170),
    "piedra": ("Piedra desplazadora", "m³", 130),
    "fierro": ("Fierro corrugado", "kg", 9.5),
    "alambre": ("Alambre de amarre", "kg", 15),
    "madera_enc": ("Madera de encofrado", "p²", 7),
    "ladrillo": ("Ladrillo de 6 huecos", "pza", 1.35),
    "cal": ("Cal", "kg", 3),
    "yeso": ("Yeso", "kg", 1.2),
    "albanil": ("Albañil", "hr", 25),
    "ayudante": ("Ayudante", "hr", 16),
    "armador": ("Armador", "hr", 25),
    "carpintero": ("Carpintero", "hr", 25),
    "plomero": ("Plomero", "hr", 28),
    "electricista": ("Electricista", "hr", 28),
    "pintor": ("Pintor", "hr", 22),
    "mezcladora": ("Mezcladora", "hr", 35),
    "vibradora": ("Vibradora", "hr", 25),
    "compactadora": ("Compactadora tipo canguro", "hr", 45),
}
TIPO = {
    "albanil": "mano_obra",
    "ayudante": "mano_obra",
    "armador": "mano_obra",
    "carpintero": "mano_obra",
    "plomero": "mano_obra",
    "electricista": "mano_obra",
    "pintor": "mano_obra",
    "mezcladora": "equipo",
    "vibradora": "equipo",
    "compactadora": "equipo",
}


# Insumo propio de una actividad: (tipo, descripción, unidad, precio).
def _m(descripcion: str, unidad: str, precio: float) -> tuple[str, str, str, float]:
    return ("material", descripcion, unidad, precio)


def _e(descripcion: str, unidad: str, precio: float) -> tuple[str, str, str, float]:
    return ("equipo", descripcion, unidad, precio)


HORMIGON_ARMADO = {"cemento": 7.5, "arena": 0.45, "grava": 0.8, "alambre": 1.5, "mezcladora": 1, "vibradora": 1}

# (código, fase, actividad, unidad, cómputo, duración, unidad de duración, predecesoras,
#  insumos: {clave de P: rendimiento} o [(insumo propio, rendimiento)])
ACTIVIDADES = [
    ("1.1", "Obras preliminares", "Instalación de faenas", "glb", 1, 1, "semanas", "",
     {"albanil": 16, "ayudante": 24}, [(_m("Madera y calamina para depósito y baño de obra", "glb", 2500), 1)]),
    ("1.2", "Obras preliminares", "Limpieza y nivelación del terreno", "m²", 200, 3, "dias", "1.1",
     {"ayudante": 0.25}, []),
    ("1.3", "Obras preliminares", "Replanteo y trazado", "m²", 120, 2, "dias", "1.2",
     {"cal": 0.05, "albanil": 0.1, "ayudante": 0.1}, [(_m("Listón de madera 2\"x2\"", "ml", 4), 0.3)]),
    ("2.1", "Movimiento de tierras", "Excavación manual de cimientos", "m³", 28, 1, "semanas", "1.3",
     {"ayudante": 2.5}, []),
    ("2.2", "Movimiento de tierras", "Relleno y compactado con material del lugar", "m³", 12, 4, "dias", "3.3",
     {"ayudante": 1.5, "compactadora": 0.4}, []),
    ("2.3", "Movimiento de tierras", "Retiro de escombros", "m³", 18, 3, "dias", "2.1",
     {"ayudante": 1}, [(_e("Volqueta", "viaje", 350), 0.15)]),
    ("3.1", "Fundaciones", "Hormigón pobre (solado) e = 5 cm", "m²", 30, 2, "dias", "2.1",
     {"cemento": 0.2, "arena": 0.03, "grava": 0.05, "albanil": 0.5, "ayudante": 0.8, "mezcladora": 0.1}, []),
    ("3.2", "Fundaciones", "Zapatas de H°A°", "m³", 6, 1, "semanas", "3.1",
     {**HORMIGON_ARMADO, "fierro": 80, "madera_enc": 6, "albanil": 8, "ayudante": 12, "armador": 6}, []),
    ("3.3", "Fundaciones", "Cimiento de H°C° 50 % piedra", "m³", 14, 1, "semanas", "3.2",
     {"cemento": 3.2, "arena": 0.3, "grava": 0.45, "piedra": 0.5, "albanil": 4, "ayudante": 8, "mezcladora": 0.6},
     []),
    ("3.4", "Fundaciones", "Sobrecimiento de H°A°", "m³", 5, 1, "semanas", "3.3",
     {**HORMIGON_ARMADO, "fierro": 70, "madera_enc": 14, "albanil": 10, "ayudante": 12, "armador": 6}, []),
    ("3.5", "Fundaciones", "Impermeabilización de sobrecimiento", "ml", 70, 2, "dias", "3.4",
     {"albanil": 0.15, "ayudante": 0.15},
     [(_m("Asfalto diluido", "kg", 18), 0.4), (_m("Polietileno de 200 micrones", "m²", 6), 0.3)]),
    ("4.1", "Obra gruesa", "Columnas de H°A°", "m³", 4.5, 2, "semanas", "3.4",
     {**HORMIGON_ARMADO, "fierro": 110, "madera_enc": 28, "albanil": 14, "ayudante": 16, "armador": 10}, []),
    ("4.2", "Obra gruesa", "Muro de ladrillo de 6 huecos e = 18 cm", "m²", 260, 4, "semanas", "3.5",
     {"ladrillo": 36, "cemento": 0.15, "arena": 0.03, "albanil": 1.1, "ayudante": 1.1}, []),
    ("4.3", "Obra gruesa", "Vigas de encadenado y dinteles de H°A°", "m³", 4, 2, "semanas", "4.1, 4.2",
     {**HORMIGON_ARMADO, "fierro": 115, "madera_enc": 30, "albanil": 14, "ayudante": 16, "armador": 10}, []),
    ("4.4", "Obra gruesa", "Contrapiso de cemento sobre empedrado", "m²", 115, 1, "semanas", "4.2, 2.2",
     {"cemento": 0.35, "arena": 0.04, "grava": 0.06, "albanil": 0.8, "ayudante": 1},
     [(_m("Piedra manzana", "m³", 130), 0.15)]),
    ("5.1", "Cubierta", "Estructura de madera para cubierta", "m²", 140, 1, "semanas", "4.3",
     {"carpintero": 1, "ayudante": 1},
     [(_m("Madera semidura (cuchi o tajibo)", "p²", 9), 9), (_m("Clavos", "kg", 15), 0.15),
      (_m("Pernos y platinas", "kg", 20), 0.3)]),
    ("5.2", "Cubierta", "Cubierta de calamina galvanizada N° 28", "m²", 140, 1, "semanas", "5.1",
     {"carpintero": 0.4, "ayudante": 0.4},
     [(_m("Calamina galvanizada N° 28", "m²", 58), 1.15), (_m("Clavos para calamina", "kg", 22), 0.08)]),
    ("5.3", "Cubierta", "Cielo falso de placa de yeso", "m²", 115, 1, "semanas", "5.2",
     {"albanil": 0.7, "ayudante": 0.5},
     [(_m("Placa de yeso 1/2\"", "m²", 45), 1.05), (_m("Perfil metálico", "ml", 9), 2.5),
      (_m("Tornillos", "pza", 0.15), 12)]),
    ("5.4", "Cubierta", "Canaletas y bajantes de calamina plana", "ml", 30, 2, "dias", "5.2",
     {"plomero": 0.6, "ayudante": 0.3},
     [(_m("Calamina plana N° 28", "ml", 35), 1), (_m("Estaño para soldar", "kg", 90), 0.05)]),
    ("6.1", "Instalaciones", "Instalación sanitaria: desagüe de PVC", "pto", 12, 1, "semanas", "4.2",
     {"plomero": 3, "ayudante": 2},
     [(_m("Tubería PVC 4\"", "ml", 38), 3), (_m("Accesorios PVC", "pza", 18), 2),
      (_m("Pegamento PVC", "lt", 90), 0.05)]),
    ("6.2", "Instalaciones", "Instalación de agua potable", "pto", 10, 1, "semanas", "4.2",
     {"plomero": 2.5, "ayudante": 1},
     [(_m("Tubería PP 1/2\"", "ml", 12), 4), (_m("Accesorios PP", "pza", 8), 3), (_m("Cinta teflón", "pza", 5), 0.3)]),
    ("6.3", "Instalaciones", "Instalación eléctrica: iluminación y tomacorrientes", "pto", 45, 2, "semanas", "4.2",
     {"electricista": 1.5, "ayudante": 1},
     [(_m("Cable 2,5 mm²", "ml", 4.5), 10), (_m("Tubo corrugado 3/4\"", "ml", 2.5), 6),
      (_m("Caja de paso", "pza", 4), 1), (_m("Interruptor o tomacorriente", "pza", 25), 1)]),
    ("6.4", "Instalaciones", "Cámara séptica y pozo absorbente", "glb", 1, 2, "semanas", "2.1",
     {"cemento": 25, "arena": 3, "grava": 2, "fierro": 60, "ladrillo": 1200, "albanil": 60, "ayudante": 80}, []),
    ("6.5", "Instalaciones", "Provisión e instalación de artefactos sanitarios", "pza", 9, 3, "dias", "6.1, 7.4",
     {"plomero": 3, "ayudante": 1}, [(_m("Artefacto sanitario con grifería (promedio)", "pza", 650), 1)]),
    ("7.1", "Acabados", "Revoque interior de yeso", "m²", 420, 2, "semanas", "6.2, 6.3, 5.3",
     {"yeso": 12, "albanil": 0.45, "ayudante": 0.4}, []),
    ("7.2", "Acabados", "Revoque exterior de cemento", "m²", 180, 2, "semanas", "4.3, 5.2",
     {"cemento": 0.2, "arena": 0.03, "cal": 1.5, "albanil": 0.7, "ayudante": 0.6}, []),
    ("7.3", "Acabados", "Piso de cerámica", "m²", 115, 2, "semanas", "4.4, 7.1",
     {"albanil": 0.9, "ayudante": 0.5},
     [(_m("Cerámica de piso", "m²", 85), 1.05), (_m("Cemento cola", "kg", 2.5), 5), (_m("Pastina", "kg", 12), 0.3)]),
    ("7.4", "Acabados", "Revestimiento de cerámica en baños y cocina", "m²", 45, 1, "semanas", "7.1",
     {"albanil": 1, "ayudante": 0.5}, [(_m("Azulejo", "m²", 80), 1.05), (_m("Cemento cola", "kg", 2.5), 5)]),
    ("7.5", "Acabados", "Zócalo de cerámica", "ml", 110, 3, "dias", "7.3",
     {"albanil": 0.2, "ayudante": 0.1}, [(_m("Cerámica de piso (recortes para zócalo)", "m²", 85), 0.1)]),
    ("7.6", "Acabados", "Puertas de madera con marco y chapa", "pza", 8, 1, "semanas", "7.1",
     {"carpintero": 4, "ayudante": 2},
     [(_m("Puerta tablero con marco", "pza", 1300), 1), (_m("Chapa", "pza", 180), 1), (_m("Bisagra", "pza", 15), 3)]),
    ("7.7", "Acabados", "Ventanas de aluminio con vidrio (provisión e instalación)", "m²", 18, 1, "semanas", "7.2",
     {"ayudante": 0.5}, [(_m("Ventana de aluminio y vidrio 4 mm, instalada", "m²", 650), 1)]),
    ("7.8", "Acabados", "Pintura interior látex", "m²", 420, 2, "semanas", "7.3, 7.6",
     {"pintor": 0.3, "ayudante": 0.15},
     [(_m("Pintura látex", "lt", 38), 0.3), (_m("Masilla", "kg", 12), 0.2), (_m("Lija", "pza", 5), 0.1)]),
    ("7.9", "Acabados", "Pintura exterior", "m²", 180, 1, "semanas", "7.2",
     {"pintor": 0.35, "ayudante": 0.2}, [(_m("Pintura para exteriores", "lt", 45), 0.35)]),
    ("7.10", "Acabados", "Limpieza final y entrega", "glb", 1, 3, "dias", "7.8, 7.9, 6.5, 7.7, 7.5, 5.4, 2.3, 6.4",
     {"ayudante": 48}, [(_m("Materiales de limpieza", "glb", 300), 1)]),
]  # fmt: skip

# Regla de medición del avance (82R-13) distinta del % físico.
REGLAS = {"1.1": "50_50", "6.5": "0_100", "7.6": "50_50", "7.7": "0_100"}

CLASIFICACION = {
    "anteproyecto": "completo",
    "planos_arquitectonicos": "completo",
    "planos_estructurales": "parcial",
    "especificaciones": "no",
    "computos": "parcial",
    "cotizaciones": "parcial",
    "cronograma": "parcial",
}

PARAMETROS = {
    "cargas_sociales": Decimal("55"),
    "iva_mano_obra": Decimal("14.94"),
    "herramientas": Decimal("5"),
    "gastos_generales": Decimal("10"),
    "utilidad": Decimal("8"),
    "impuestos": Decimal("3.09"),
}

BASE = {
    "proposito": (
        "Estimado para fijar el precio de contrato con el cliente y aprobar la línea base de costo y plazo con la que "
        "se controlará la obra con valor ganado."
    ),
    "alcance": (
        "Vivienda unifamiliar de una planta, 120 m² construidos, en Urb. Las Palmas, Santa Cruz de la Sierra: "
        "fundaciones de H°A° y H°C°, estructura de columnas y vigas de H°A°, muros de ladrillo de 6 huecos, cubierta "
        "de calamina sobre estructura de madera con cielo falso de yeso, instalaciones sanitarias, de agua y "
        "eléctricas, cámara séptica, pisos y revestimientos de cerámica, carpintería y pintura."
    ),
    "metodologia": (
        "Precios unitarios detallados (APU) por actividad: rendimientos de materiales, mano de obra y equipo por "
        "unidad × cómputo métrico. Sobre la mano de obra se aplican cargas sociales (55 %), IVA (14,94 %) y "
        "herramientas menores (5 %); sobre el costo directo, gastos generales (10 %), utilidad (8 %) e IT (3,09 %)."
    ),
    "base_diseno": (
        "Planos arquitectónicos completos (plantas, cortes, fachadas). Planos estructurales preliminares: las "
        "cuantías de fierro de zapatas, columnas y vigas son estimadas y se deben ajustar con el cálculo estructural. "
        "Sin especificaciones técnicas escritas: se asumen materiales de calidad estándar del mercado local."
    ),
    "base_planificacion": (
        "Inicio el 07/12/2026 con una cuadrilla base (1 albañil y 2 ayudantes) más especialistas por actividad; "
        "6 días por semana; duraciones en días calendario; secuencia fin-comienzo según el cronograma."
    ),
    "fuentes_precios": (
        "Cotizaciones verbales a 2 ferreterías de Santa Cruz (cemento, fierro, ladrillo, calamina), jornales "
        "de mercado de la zona y precios de obras anteriores de la empresa. Precios ILUSTRATIVOS para el ejemplo."
    ),
    "supuestos": (
        "Terreno plano con suelo apto para fundación superficial; acceso para volqueta; agua y energía de obra "
        "disponibles; precios estables durante la obra; sin lluvias extraordinarias que paren más de 1 semana."
    ),
    "exclusiones": (
        "Trámites y aprobación de planos, conexiones a redes públicas, muro perimetral, jardinería, muebles "
        "de cocina y closets, calentador de agua, IVA de materiales con factura (se cobra aparte si el cliente "
        "la requiere)."
    ),
    "riesgos_oportunidades": (
        "Riesgos: suba del fierro y del cemento; cuantías de fierro mayores al cálculo final; lluvias en enero–marzo. "
        "Oportunidad: comprar el fierro y la calamina juntos con descuento por volumen. "
        "Nota: el BAC usado para valor ganado es el precio total del APU (incluye utilidad e impuestos), por eso el "
        "CPI se ve más favorable que si se midiera contra el costo."
    ),
    "contingencia_nota": (
        "5 % del estimado por la clase del estimado (planos estructurales y especificaciones incompletos). "
        "Se revisará con el registro de riesgos (fase 3)."
    ),
}


# Registro de riesgos (44R-08): (descripción, causa, probabilidad %, impacto Bs, impacto días, responsable,
# estrategia, respuesta).
RIESGOS = [
    ("Suba del precio del fierro y del cemento", "Escasez de dólares e importación irregular", 40, 6500, 0,
     "Dueño", "mitigar", "Comprar todo el fierro de fundaciones y estructura al iniciar la obra."),
    ("Lluvias intensas en enero–marzo", "Temporada de lluvias en Santa Cruz", 60, 8000, 12,
     "Residente de obra", "mitigar", "Cubrir excavaciones, terminar la cubierta antes de marzo y prever bombeo."),
    ("Cuantías de fierro mayores a las estimadas", "Planos estructurales todavía preliminares", 50, 9000, 0,
     "Ingeniero calculista", "evitar", "Cerrar el cálculo estructural antes de empezar las fundaciones."),
    ("Suelo con baja capacidad portante", "No hay estudio de suelos", 15, 25000, 15,
     "Ingeniero calculista", "evitar", "Hacer un estudio de suelos (SPT) antes de diseñar las fundaciones."),
    ("Falta de albañiles en temporada alta", "Varias obras grandes en la zona", 30, 4000, 10,
     "Dueño", "aceptar", "Acordar con la cuadrilla de confianza desde la firma del contrato."),
    ("Robo de materiales en obra", "Obra sin cerco y sin cuidador nocturno", 20, 3000, 2,
     "Encargado de obra", "mitigar", "Cerco provisional y cuidador; comprar materiales por etapas."),
]  # fmt: skip


def cargar_riesgos(sesion: Session, obra: Obra) -> None:
    from app.modelos import Riesgo

    for numero, (desc, causa, prob, costo, dias, resp, estrategia, respuesta) in enumerate(RIESGOS, 1):
        sesion.add(
            Riesgo(
                obra_id=obra.id,
                numero=numero,
                descripcion=desc,
                causa=causa,
                probabilidad=Decimal(prob),
                impacto_costo=Decimal(costo),
                impacto_dias=dias,
                responsable=resp,
                estrategia=estrategia,
                respuesta=respuesta,
                estado="abierto",
            )
        )
    sesion.flush()


def datos() -> pl.ObraLeida:
    obra = pl.ObraLeida(
        nombre=NOMBRE_OBRA,
        cliente="Familia Rojas Méndez",
        ubicacion="Urb. Las Palmas, Santa Cruz de la Sierra",
        fecha_inicio=INICIO,
        moneda="Bs",
        parametros=dict(PARAMETROS),
        clasificacion=dict(CLASIFICACION),
        base=dict(BASE),
        fecha_precios=FECHA_PRECIOS,
        contingencia_porcentaje=Decimal("5"),
    )
    for fila, (codigo, fase, nombre, unidad, computo, dur, udur, preds, comunes, propios) in enumerate(ACTIVIDADES, 2):
        predecesoras = [p.strip() for p in preds.split(",") if p.strip()]
        computo, dur = Decimal(str(computo)), Decimal(str(dur))
        regla = REGLAS.get(codigo, "porcentaje")
        obra.actividades.append(
            pl.ActividadLeida(fila, codigo, fase, nombre, unidad, computo, dur, udur, predecesoras, None, regla)
        )
        for clave, rendimiento in comunes.items():
            descripcion, u, precio = P[clave]
            tipo = TIPO.get(clave, "material")
            obra.insumos.append(
                pl.InsumoLeido(0, codigo, tipo, descripcion, u, Decimal(str(rendimiento)), Decimal(str(precio)))
            )
        for (tipo, descripcion, u, precio), rendimiento in propios:
            obra.insumos.append(
                pl.InsumoLeido(0, codigo, tipo, descripcion, u, Decimal(str(rendimiento)), Decimal(str(precio)))
            )
    return obra


def escribir(destino: Path = ARCHIVO) -> bytes:
    contenido = pl.escribir_plantilla(datos())
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return contenido


def cargar_en(sesion: Session, dueno: Usuario, contenido: bytes) -> Obra:
    """Importa el ejemplo (debe pasar la validación sin errores) y aprueba la línea base v1."""
    lectura = pl.leer_plantilla(contenido)
    if not lectura.valida:
        detalle = "; ".join(f"{e.hoja} fila {e.fila}: {e.mensaje}" for e in lectura.errores[:5])
        raise ValueError(f"El ejemplo no pasa la validación: {detalle}")
    obra = ts.crear_obra_desde_plantilla(sesion, dueno, lectura.obra)
    ts.aprobar_linea_base(sesion, obra, dueno, "Línea base inicial: estimado aprobado por el cliente.")
    cargar_riesgos(sesion, obra)
    return obra


NOMBRE_EN_EJECUCION = "Vivienda 120 m² — Urb. Los Mangales (ejemplo en ejecución)"
SEMANAS_TRANSCURRIDAS = 9
# Por fase: (ritmo de avance frente al plan, gasto frente a lo ganado). Ritmo < 1 = atrasado; gasto > 1 = sobrecosto.
ESCENARIO = {
    "Obras preliminares": (1.0, 0.95),
    "Movimiento de tierras": (1.0, 1.05),
    "Fundaciones": (0.95, 1.15),
    "Obra gruesa": (0.75, 1.06),
    "Cubierta": (0.6, 1.0),
    "Instalaciones": (0.7, 1.0),
    "Acabados": (0.5, 1.0),
}


def cargar_en_ejecucion(sesion: Session, dueno: Usuario, contenido: bytes, hoy: date) -> Obra:
    """La misma vivienda empezada hace 9 semanas, con avances y gastos: sirve para ver el valor ganado (82R-13) y los
    pronósticos (80R-13) con números. Fundaciones gastó de más y la obra gruesa va atrasada."""
    from datetime import timedelta

    from app.calculos import valor_ganado as vg
    from app.modelos import Avance, Gasto

    lectura = pl.leer_plantilla(contenido)
    d = lectura.obra
    d.nombre = NOMBRE_EN_EJECUCION
    d.cliente = "Sr. Julio Áñez"
    d.ubicacion = "Urb. Los Mangales, Santa Cruz de la Sierra"
    d.fecha_inicio = hoy - timedelta(weeks=SEMANAS_TRANSCURRIDAS)
    obra = ts.crear_obra_desde_plantilla(sesion, dueno, d)
    base = ts.aprobar_linea_base(sesion, obra, dueno, "Contrato firmado con el cliente.")
    cargar_riesgos(sesion, obra)
    ayer = hoy - timedelta(days=1)
    for lp in base.partidas:
        if lp.partida_id is None or not lp.fecha_inicio or lp.fecha_inicio > ayer or lp.presupuesto <= 0:
            continue
        ritmo, gasto = ESCENARIO.get(lp.fase, (1.0, 1.0))
        plan = vg.fraccion_planificada(lp.fecha_inicio, lp.fecha_fin, ayer)
        avance = min(Decimal("100"), (plan * Decimal(str(ritmo)) * 100).quantize(Decimal("1")))
        if avance <= 0:
            continue
        sesion.add(Avance(partida_id=lp.partida_id, fecha=ayer, porcentaje=avance, usuario_id=dueno.id))
        # Gasto repartido en pagos semanales desde el inicio de la partida (lo real, no lo que dice la regla).
        total = vg.redondear_dinero(lp.presupuesto * avance / 100 * Decimal(str(gasto)))
        fin = min(ayer, lp.fecha_fin)
        fechas = [lp.fecha_inicio + timedelta(days=7 * i) for i in range((fin - lp.fecha_inicio).days // 7 + 1)]
        cuota = vg.redondear_dinero(total / len(fechas))
        for i, f in enumerate(fechas):
            monto = total - cuota * (len(fechas) - 1) if i == len(fechas) - 1 else cuota
            sesion.add(
                Gasto(
                    obra_id=obra.id,
                    partida_id=lp.partida_id,
                    fecha=f,
                    monto=monto,
                    tipo="material" if i % 2 == 0 else "mano_obra",
                    descripcion=f"{lp.nombre} (pago {i + 1})",
                    con_factura=i % 2 == 0,
                    usuario_id=dueno.id,
                )
            )
    sesion.flush()
    cargar_cambios(sesion, obra, dueno, hoy)
    return obra


def cargar_cambios(sesion: Session, obra: Obra, dueno: Usuario, hoy: date) -> None:
    """Bitácora de ejemplo: un cambio aprobado (genera la línea base v2), uno pendiente y uno rechazado."""
    from datetime import timedelta

    from app.modelos import Cambio

    cambios = [
        (hoy - timedelta(days=20), "Cliente", "Agregar baño de visitas (2,5 m²) junto a la sala", Decimal("14500"), 10),
        (hoy - timedelta(days=12), "Cliente", "Cambiar la cubierta de calamina por teja colonial", Decimal("18000"), 7),
        (
            hoy - timedelta(days=3),
            "Cliente",
            "Piso de porcelanato en sala y comedor en vez de cerámica",
            Decimal("9800"),
            0,
        ),
    ]
    filas = []
    for numero, (fecha, solicitante, descripcion, costo, dias) in enumerate(cambios, 1):
        c = Cambio(
            obra_id=obra.id,
            numero=numero,
            fecha=fecha,
            solicitante=solicitante,
            descripcion=descripcion,
            impacto_costo=costo,
            impacto_dias=dias,
            estado="pendiente",
        )
        sesion.add(c)
        filas.append(c)
    sesion.flush()
    ts.aprobar_cambio(
        sesion, obra, filas[0], dueno, "Ing. Residente", agregar_partida=True, comentario="Firmado por el cliente"
    )
    ts.rechazar_cambio(filas[1], "Ing. Residente", "La estructura de madera no soporta el peso de la teja.")
    sesion.flush()


def main() -> None:
    from app import datos_demo
    from app.db import FabricaSesion

    contenido = escribir()
    print(f"Plantilla de ejemplo: {ARCHIVO}")
    with FabricaSesion() as sesion:
        dueno = sesion.scalar(select(Usuario).where(Usuario.correo == datos_demo.CORREO_DEMO))
    if dueno is None:
        datos_demo.cargar()
    with FabricaSesion() as sesion:
        dueno = sesion.scalar(select(Usuario).where(Usuario.correo == datos_demo.CORREO_DEMO))
        if sesion.scalar(select(Obra).where(Obra.dueno_id == dueno.id, Obra.nombre == NOMBRE_OBRA)):
            print("La obra de ejemplo ya está cargada en la cuenta demo.")
        else:
            obra = cargar_en(sesion, dueno, contenido)
            sesion.commit()
            print(f"Obra de ejemplo cargada (id {obra.id}) en {datos_demo.CORREO_DEMO} con la línea base v1 aprobada.")
        if sesion.scalar(select(Obra).where(Obra.dueno_id == dueno.id, Obra.nombre == NOMBRE_EN_EJECUCION)):
            print("La obra de ejemplo en ejecución ya está cargada.")
        else:
            from app import servicios

            obra = cargar_en_ejecucion(sesion, dueno, contenido, servicios.hoy())
            sesion.commit()
            print(f"Obra en ejecución cargada (id {obra.id}) con avances y gastos de {SEMANAS_TRANSCURRIDAS} semanas.")


if __name__ == "__main__":
    if config.ENTORNO == "produccion":
        raise SystemExit("El ejemplo usa la cuenta demo (clave pública): no se carga con ENTORNO=produccion.")
    main()
