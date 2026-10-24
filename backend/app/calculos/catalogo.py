"""Catálogo base de rendimientos, cuadrillas y consumos por rubro. Sin base de datos.

**Todos los valores son ilustrativos**: sirven para que la estimación funcione de punta a punta y se deben
calibrar con 2 o 3 constructores antes del piloto (plan de estimación §7). Más adelante cada dueño podrá
personalizarlos; por ahora viven aquí.
"""

from __future__ import annotations

from dataclasses import dataclass

# Jornal por día en Bs (referencia, a calibrar).
JORNALES = {
    "Albañil": 150,
    "Ayudante": 100,
    "Peón": 100,
    "Fierrista": 160,
    "Electricista": 180,
    "Plomero": 180,
    "Carpintero": 170,
    "Ceramista": 170,
    "Pintor": 150,
}

OFICIOS = {
    "tierras": "Movimiento de tierras",
    "estructura": "Hormigón y fierro",
    "albanileria": "Albañilería",
    "pisos": "Pisos",
    "electricidad": "Electricidad",
    "plomeria": "Plomería",
    "carpinteria": "Carpintería",
    "techo": "Techo",
    "pintura": "Pintura",
    "limpieza": "Limpieza",
}

# Precio de los acabados según el nivel elegido (piso, puertas, ventanas y pintura).
FACTOR_ACABADO = {"economico": 0.8, "medio": 1.0, "alto": 1.4}


@dataclass(frozen=True)
class Consumo:
    material: str
    unidad: str
    por_unidad: float  # cantidad de material por unidad del rubro
    precio: float  # Bs por unidad de material
    acabado: bool = False  # su precio cambia con el nivel de acabado


@dataclass(frozen=True)
class Rubro:
    actividad: str
    fase: str
    oficio: str
    cuadrilla: tuple[tuple[str, int], ...]  # (cargo, personas) de una cuadrilla
    rendimiento: float  # unidades del rubro por día de trabajo de una cuadrilla
    consumos: tuple[Consumo, ...] = ()
    dias_fijos: int | None = None  # actividades sin cantidad (ej. entrega)

    @property
    def personas(self) -> int:
        return sum(n for _, n in self.cuadrilla)


_HORMIGON_ARMADO = (
    Consumo("Cemento", "bolsa", 7.0, 60),
    Consumo("Arena", "m³", 0.5, 150),
    Consumo("Grava", "m³", 0.8, 180),
)
_ESTRUCTURA = (("Albañil", 1), ("Fierrista", 1), ("Ayudante", 3))

CATALOGO: dict[str, Rubro] = {
    "preliminares": Rubro(
        "Limpieza, replanteo e instalación de faenas",
        "Preliminares",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 2)),
        80,
    ),
    "excavacion": Rubro("Excavación de fundaciones", "Movimiento de tierras", "tierras", (("Peón", 2),), 4),
    "zapatas": Rubro("Zapatas de H°A°", "Fundaciones", "estructura", _ESTRUCTURA, 1.5, _HORMIGON_ARMADO),
    "cimientos": Rubro(
        "Cimiento corrido de H°C°",
        "Fundaciones",
        "estructura",
        (("Albañil", 1), ("Ayudante", 3)),
        3,
        (Consumo("Cemento", "bolsa", 3.0, 60), Consumo("Arena", "m³", 0.5, 150), Consumo("Piedra", "m³", 0.6, 150)),
    ),
    "sobrecimiento": Rubro(
        "Sobrecimiento",
        "Fundaciones",
        "estructura",
        (("Albañil", 1), ("Ayudante", 2)),
        2,
        (Consumo("Cemento", "bolsa", 4.5, 60), Consumo("Arena", "m³", 0.5, 150), Consumo("Piedra", "m³", 0.3, 150)),
    ),
    "columnas": Rubro("Columnas de H°A°", "Obra gruesa", "estructura", _ESTRUCTURA, 1.0, _HORMIGON_ARMADO),
    "losa": Rubro("Vigas y losa de H°A°", "Obra gruesa", "estructura", _ESTRUCTURA, 3.0, _HORMIGON_ARMADO),
    "muros:ladrillo_6h": Rubro(
        "Muros de ladrillo",
        "Obra gruesa",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 1)),
        10,
        (
            Consumo("Ladrillo 6 huecos", "pza", 36, 1.6),
            Consumo("Cemento", "bolsa", 0.2, 60),
            Consumo("Arena", "m³", 0.03, 150),
        ),
    ),
    "muros:bloque_cemento": Rubro(
        "Muros de bloque de cemento",
        "Obra gruesa",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 1)),
        12,
        (
            Consumo("Bloque de cemento", "pza", 12.5, 5),
            Consumo("Cemento", "bolsa", 0.15, 60),
            Consumo("Arena", "m³", 0.02, 150),
        ),
    ),
    "muros:adobe": Rubro(
        "Muros de adobe",
        "Obra gruesa",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 1)),
        8,
        (Consumo("Adobe", "pza", 30, 1.5), Consumo("Barro", "m³", 0.05, 60)),
    ),
    "electrica": Rubro(
        "Instalación eléctrica empotrada",
        "Instalaciones",
        "electricidad",
        (("Electricista", 1), ("Ayudante", 1)),
        8,
        (
            Consumo("Cable", "m", 12, 4),
            Consumo("Tubo corrugado", "m", 4, 3),
            Consumo("Caja y accesorios", "pza", 1, 25),
        ),
    ),
    "sanitaria": Rubro(
        "Instalación sanitaria",
        "Instalaciones",
        "plomeria",
        (("Plomero", 1), ("Ayudante", 1)),
        3,
        (Consumo("Tubería PVC", "m", 4, 18), Consumo("Accesorios", "jgo", 1, 40)),
    ),
    "revoque_interior": Rubro(
        "Revoque interior",
        "Acabados",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 1)),
        14,
        (Consumo("Cemento", "bolsa", 0.12, 60), Consumo("Cal", "kg", 2, 2), Consumo("Arena", "m³", 0.02, 150)),
    ),
    "revoque_exterior": Rubro(
        "Revoque exterior",
        "Acabados",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 1)),
        10,
        (Consumo("Cemento", "bolsa", 0.18, 60), Consumo("Arena", "m³", 0.025, 150)),
    ),
    "contrapiso": Rubro(
        "Contrapiso",
        "Acabados",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 2)),
        25,
        (Consumo("Cemento", "bolsa", 0.25, 60), Consumo("Arena", "m³", 0.03, 150), Consumo("Grava", "m³", 0.06, 180)),
    ),
    "cielo_raso": Rubro(
        "Cielo raso de yeso",
        "Acabados",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 1)),
        12,
        (Consumo("Yeso", "kg", 8, 1.5),),
    ),
    "piso:ceramica": Rubro(
        "Piso de cerámica",
        "Acabados",
        "pisos",
        (("Ceramista", 1), ("Ayudante", 1)),
        12,
        (Consumo("Cerámica", "m²", 1.05, 75, True), Consumo("Cemento cola", "kg", 5, 3)),
    ),
    "piso:porcelanato": Rubro(
        "Piso de porcelanato",
        "Acabados",
        "pisos",
        (("Ceramista", 1), ("Ayudante", 1)),
        10,
        (Consumo("Porcelanato", "m²", 1.05, 160, True), Consumo("Cemento cola", "kg", 5, 3)),
    ),
    "piso:cemento": Rubro(
        "Piso de cemento pulido",
        "Acabados",
        "pisos",
        (("Albañil", 1), ("Ayudante", 1)),
        20,
        (Consumo("Cemento", "bolsa", 0.2, 60), Consumo("Arena", "m³", 0.02, 150)),
    ),
    "puertas": Rubro(
        "Puertas",
        "Acabados",
        "carpinteria",
        (("Carpintero", 1), ("Ayudante", 1)),
        3,
        (Consumo("Puerta con marco", "pza", 1, 750, True),),
    ),
    "ventanas": Rubro(
        "Ventanas",
        "Acabados",
        "carpinteria",
        (("Carpintero", 1), ("Ayudante", 1)),
        6,
        (Consumo("Ventana de aluminio y vidrio", "m²", 1, 550, True),),
    ),
    "pintura": Rubro(
        "Pintura interior y exterior",
        "Acabados",
        "pintura",
        (("Pintor", 1), ("Ayudante", 1)),
        40,
        (Consumo("Pintura látex", "l", 0.12, 35, True),),
    ),
    "cubierta:losa": Rubro(
        "Impermeabilización de losa de cubierta",
        "Cubierta",
        "albanileria",
        (("Albañil", 1), ("Ayudante", 1)),
        30,
        (Consumo("Membrana asfáltica", "m²", 1.1, 45),),
    ),
    "cubierta:calamina": Rubro(
        "Cubierta de calamina",
        "Cubierta",
        "techo",
        (("Carpintero", 1), ("Ayudante", 2)),
        25,
        (Consumo("Calamina", "m²", 1.1, 55), Consumo("Madera", "pie²", 4, 10)),
    ),
    "cubierta:teja": Rubro(
        "Cubierta de teja",
        "Cubierta",
        "techo",
        (("Carpintero", 1), ("Ayudante", 2)),
        15,
        (Consumo("Teja", "pza", 16, 4), Consumo("Madera", "pie²", 4, 10)),
    ),
    "entrega": Rubro(
        "Limpieza final y entrega",
        "Entrega",
        "limpieza",
        (("Ayudante", 2),),
        1,
        dias_fijos=2,
    ),
}

FIERRO = Consumo("Fierro corrugado", "kg", 1.0, 9)
FRACCION_COLUMNAS = 0.25  # parte del hormigón de un piso que va en columnas (el resto, vigas y losa)
FRAGUADO_DIAS = 7  # espera antes de cargar la losa con el piso de arriba
