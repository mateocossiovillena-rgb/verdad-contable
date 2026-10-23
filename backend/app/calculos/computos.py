"""Cómputos: cantidades por rubro a partir de lo medido en el plano y del formulario. Sin base de datos.

Sirve igual para CAD y BIM: los lectores entregan un `PisoMedido` por piso y este módulo calcula.
Cada cantidad dice su origen:
- plano: medida del archivo;
- formulario: dato del constructor;
- proporcion: valor típico por m² o por metro (constantes de abajo, a calibrar con los pilotos);
- editada: corregida a mano (la marca quien aplica las ediciones, no este módulo).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

# --- Valores típicos (ilustrativos: calibrar con constructores antes del piloto) ---
ALTO_PUERTA = 2.10  # m
ALTO_VENTANA = 1.20  # m, si el plano no lo dice
ESPESOR_LOSA = {"alivianada": 0.12, "maciza": 0.15, "viguetas": 0.10}  # m³ de hormigón por m² de losa
HORMIGON_COLUMNAS_VIGAS = 0.035  # m³ por m² de planta y por piso
FIERRO_ELEVADO = 90  # kg por m³ de hormigón armado en columnas, vigas y losas
FIERRO_ZAPATAS = 45  # kg por m³ de zapata
AREA_POR_ZAPATA = 12.0  # m² de planta por columna/zapata si el plano no las marca
ZAPATA = (1.0, 1.0, 0.35)  # m: largo, ancho y alto de una zapata típica
EXCAVACION_ZAPATA = (1.2, 1.2, 1.3)
CIMIENTO_CORRIDO = (0.50, 0.60)  # m: ancho y alto (H°C°)
EXCAVACION_CIMIENTO = (0.60, 0.80)
ALTO_SOBRECIMIENTO = 0.40
FACTOR_CUBIERTA = {"losa": 1.0, "calamina": 1.15, "teja": 1.20}  # por la pendiente y los aleros
PUNTOS_ELECTRICOS_POR_AMBIENTE = 4
PUNTOS_ELECTRICOS_POR_M2 = 0.25
PUNTOS_SANITARIOS = {"bano": 6, "cocina": 3}

NOMBRES_MURO = {
    "ladrillo_6h": "Muro de ladrillo de 6 huecos",
    "bloque_cemento": "Muro de bloque de cemento",
    "adobe": "Muro de adobe",
}
NOMBRES_CUBIERTA = {
    "losa": "Impermeabilización de losa de cubierta",
    "calamina": "Cubierta de calamina sobre estructura de madera",
    "teja": "Cubierta de teja sobre estructura de madera",
}
NOMBRES_PISO = {
    "ceramica": "Piso de cerámica",
    "porcelanato": "Piso de porcelanato",
    "cemento": "Piso de cemento pulido",
}


@dataclass
class Formulario:
    """Lo que el plano CAD no dice. En BIM no se pregunta: se llena con el modelo y estos valores típicos."""

    tipo_obra: str = "vivienda"  # vivienda, departamentos, comercial
    altura_piso: float = 2.60  # m, de piso a techo
    tipo_muro: str = "ladrillo_6h"
    espesor_exterior: float = 0.18  # m
    espesor_interior: float = 0.12  # m
    losa: str = "alivianada"  # alivianada, maciza, viguetas
    cubierta: str = "losa"  # losa, calamina, teja
    fundacion: str = "zapatas"  # zapatas, cimiento_corrido
    acabado: str = "medio"  # economico, medio, alto
    piso: str = "ceramica"  # ceramica, porcelanato, cemento
    banos: int | None = None  # None = los que marca el plano
    cocinas: int | None = None

    @classmethod
    def desde_dict(cls, datos: dict | None) -> Formulario:
        nombres = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (datos or {}).items() if k in nombres})

    def como_dict(self) -> dict:
        return asdict(self)


@dataclass
class Abertura:
    ancho: float  # m
    alto: float | None = None  # m; None = valor típico


@dataclass
class PisoMedido:
    """Lo medido en un piso. Lo que vale None no salió del plano y se completa con formulario o proporción."""

    nombre: str
    repeticiones: int = 1  # planta tipo que se repite (departamentos)
    largo_muros: float = 0.0  # m de eje
    perimetro_exterior: float = 0.0  # m
    espesor_muros: float | None = None  # m, el más común
    area_muros: float | None = None  # m² de una cara, ya sin vanos (BIM)
    area_muros_exterior: float | None = None  # m² de cara exterior (BIM)
    altura: float | None = None  # m (BIM)
    area_planta: float = 0.0  # m² que ocupa la planta (contorno o losa)
    area_ambientes: float | None = None  # m² útiles sumando ambientes
    ambientes: list[str] = field(default_factory=list)
    banos: int = 0
    cocinas: int = 0
    puertas: list[Abertura] = field(default_factory=list)
    ventanas: list[Abertura] = field(default_factory=list)
    columnas: int = 0
    volumen_hormigon: float | None = None  # m³ de columnas, vigas y losas (BIM)
    area_cubierta: float | None = None  # m² (BIM)

    @classmethod
    def desde_dict(cls, datos: dict) -> PisoMedido:
        datos = dict(datos)
        datos["puertas"] = [Abertura(**a) for a in datos.get("puertas", [])]
        datos["ventanas"] = [Abertura(**a) for a in datos.get("ventanas", [])]
        nombres = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in datos.items() if k in nombres})

    def como_dict(self) -> dict:
        return asdict(self)


@dataclass
class Cantidad:
    clave: str  # estable entre recálculos, para conservar lo editado a mano
    rubro: str
    nombre: str
    piso: str | None
    unidad: str
    cantidad: float
    origen: str  # plano, formulario, proporcion
    detalle: str  # cómo se calculó, en palabras simples


def _r(valor: float) -> float:
    return round(max(valor, 0.0), 2)


def _m(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",")


def calcular(pisos: list[PisoMedido], formulario: Formulario, origen_formulario: str = "formulario") -> list[Cantidad]:
    """Cantidades por rubro. `origen_formulario` es "proporcion" en BIM, donde el formulario no se pregunta."""
    cantidades: list[Cantidad] = []
    if not pisos:
        return cantidades

    def agregar(rubro: str, nombre: str, piso: str | None, unidad: str, valor: float, origen: str, detalle: str):
        if valor <= 0:  # un piso que solo tiene la cubierta no genera muros ni pisos en cero
            return
        clave = rubro if piso is None else f"{rubro}:{piso}"
        cantidades.append(Cantidad(clave, rubro, nombre, piso, unidad, _r(valor), origen, detalle))

    planta_baja = pisos[0]
    espesor = planta_baja.espesor_muros or formulario.espesor_exterior
    largo_pb = planta_baja.largo_muros

    # Fundaciones (solo planta baja)
    if formulario.fundacion == "cimiento_corrido":
        ex_ancho, ex_alto = EXCAVACION_CIMIENTO
        agregar(
            "excavacion",
            "Excavación de fundaciones",
            None,
            "m³",
            largo_pb * ex_ancho * ex_alto,
            "proporcion",
            f"{_m(largo_pb)} m de muro en planta baja × {_m(ex_ancho)} × {_m(ex_alto)} m",
        )
        ancho, alto = CIMIENTO_CORRIDO
        agregar(
            "cimientos",
            "Cimiento corrido de H°C°",
            None,
            "m³",
            largo_pb * ancho * alto,
            "plano",
            f"{_m(largo_pb)} m de muro × sección de {_m(ancho)} × {_m(alto)} m",
        )
    else:
        n = planta_baja.columnas or max(4, round(planta_baja.area_planta / AREA_POR_ZAPATA))
        origen_n = "plano" if planta_baja.columnas else "proporcion"
        detalle_n = f"{n} columnas" if planta_baja.columnas else f"{n} zapatas (1 cada {_m(AREA_POR_ZAPATA)} m²)"
        ex = EXCAVACION_ZAPATA[0] * EXCAVACION_ZAPATA[1] * EXCAVACION_ZAPATA[2]
        agregar("excavacion", "Excavación de fundaciones", None, "m³", n * ex, origen_n, f"{detalle_n} × {_m(ex)} m³")
        vol = ZAPATA[0] * ZAPATA[1] * ZAPATA[2]
        agregar("zapatas", "Zapatas de H°A°", None, "m³", n * vol, origen_n, f"{detalle_n} × {_m(vol)} m³")
        agregar(
            "fierro_zapatas",
            "Fierro en zapatas",
            None,
            "kg",
            n * vol * FIERRO_ZAPATAS,
            "proporcion",
            f"{_m(n * vol)} m³ × {FIERRO_ZAPATAS} kg/m³",
        )
    agregar(
        "sobrecimiento",
        "Sobrecimiento",
        None,
        "m³",
        largo_pb * espesor * ALTO_SOBRECIMIENTO,
        "plano",
        f"{_m(largo_pb)} m × {_m(espesor)} m de espesor × {_m(ALTO_SOBRECIMIENTO)} m de alto",
    )

    hormigon_total = 0.0
    banos_plano = cocinas_plano = 0
    for indice, piso in enumerate(pisos):
        veces = max(piso.repeticiones, 1)
        sufijo = f" (×{veces} pisos)" if veces > 1 else ""
        altura = piso.altura or formulario.altura_piso
        es_ultimo = indice == len(pisos) - 1

        # Estructura: columnas, vigas y losa de techo de este piso
        if piso.volumen_hormigon is not None:
            hormigon = piso.volumen_hormigon
            agregar(
                "hormigon",
                "Hormigón armado: columnas, vigas y losa",
                piso.nombre,
                "m³",
                hormigon * veces,
                "plano",
                f"Volumen del modelo{sufijo}",
            )
        else:
            lleva_losa = not es_ultimo or formulario.cubierta == "losa"
            espesor_losa = ESPESOR_LOSA.get(formulario.losa, 0.12) if lleva_losa else 0.0
            por_m2 = espesor_losa + HORMIGON_COLUMNAS_VIGAS
            hormigon = piso.area_planta * por_m2
            agregar(
                "hormigon",
                "Hormigón armado: columnas, vigas y losa",
                piso.nombre,
                "m³",
                hormigon * veces,
                "proporcion",
                f"{_m(piso.area_planta)} m² de planta × {_m(por_m2)} m³/m²{sufijo}",
            )
        hormigon_total += hormigon * veces

        # Muros: largo de eje × altura, más el muro sobre puertas y debajo y encima de ventanas
        # (en el plano los muros vienen cortados en los vanos).
        if piso.area_muros is not None:
            area_muros = piso.area_muros
            detalle_muros = f"Superficie neta del modelo{sufijo}"
            origen_muros = "plano"
        else:
            sobre_puertas = sum(p.ancho * max(altura - (p.alto or ALTO_PUERTA), 0) for p in piso.puertas)
            fuera_ventanas = sum(v.ancho * max(altura - (v.alto or ALTO_VENTANA), 0) for v in piso.ventanas)
            area_muros = piso.largo_muros * altura + sobre_puertas + fuera_ventanas
            detalle_muros = f"{_m(piso.largo_muros)} m de muro × {_m(altura)} m de alto, más dinteles y antepechos"
            detalle_muros += sufijo
            origen_muros = "plano"
        agregar(
            "muros",
            NOMBRES_MURO.get(formulario.tipo_muro, "Muros"),
            piso.nombre,
            "m²",
            area_muros * veces,
            origen_muros,
            detalle_muros,
        )

        if piso.area_muros_exterior is not None:
            exterior = piso.area_muros_exterior
        else:
            exterior = piso.perimetro_exterior * altura
        interior = max(2 * area_muros - exterior, area_muros)
        agregar(
            "revoque_exterior",
            "Revoque exterior",
            piso.nombre,
            "m²",
            exterior * veces,
            "plano",
            f"{_m(piso.perimetro_exterior)} m de fachada × {_m(altura)} m{sufijo}"
            if piso.area_muros_exterior is None
            else f"Cara exterior de los muros del modelo{sufijo}",
        )
        agregar(
            "revoque_interior",
            "Revoque interior",
            piso.nombre,
            "m²",
            interior * veces,
            "plano",
            f"Dos caras de muro menos la fachada{sufijo}",
        )

        # Pisos y cielos
        if piso.area_ambientes is not None:
            area_util = piso.area_ambientes
            detalle_util = f"Suma de {len(piso.ambientes) or 'los'} ambientes{sufijo}"
        else:
            area_util = max(piso.area_planta - piso.largo_muros * espesor, 0)
            detalle_util = f"Planta de {_m(piso.area_planta)} m² menos lo que ocupan los muros{sufijo}"
        if indice == 0:
            agregar("contrapiso", "Contrapiso de cemento", piso.nombre, "m²", area_util, "plano", detalle_util)
        agregar(
            "piso",
            NOMBRES_PISO.get(formulario.piso, "Piso"),
            piso.nombre,
            "m²",
            area_util * veces,
            "plano",
            detalle_util,
        )
        agregar("cielo_raso", "Cielo raso", piso.nombre, "m²", area_util * veces, "plano", detalle_util)
        agregar(
            "pintura",
            "Pintura interior y exterior",
            piso.nombre,
            "m²",
            (interior + exterior + area_util) * veces,
            "plano",
            f"Revoques + cielo raso{sufijo}",
        )

        # Carpintería
        if piso.puertas:
            agregar(
                "puertas",
                "Puertas",
                piso.nombre,
                "pza",
                len(piso.puertas) * veces,
                "plano",
                f"{len(piso.puertas)} puertas en el plano{sufijo}",
            )
        if piso.ventanas:
            area_ventanas = sum(v.ancho * (v.alto or ALTO_VENTANA) for v in piso.ventanas)
            agregar(
                "ventanas",
                "Ventanas",
                piso.nombre,
                "m²",
                area_ventanas * veces,
                "plano",
                f"{len(piso.ventanas)} ventanas{sufijo}",
            )

        # Instalación eléctrica
        if piso.ambientes:
            puntos = len(piso.ambientes) * PUNTOS_ELECTRICOS_POR_AMBIENTE
            detalle = f"{len(piso.ambientes)} ambientes × {PUNTOS_ELECTRICOS_POR_AMBIENTE} puntos"
        else:
            puntos = area_util * PUNTOS_ELECTRICOS_POR_M2
            detalle = f"{_m(area_util)} m² × {_m(PUNTOS_ELECTRICOS_POR_M2)} puntos/m²"
        agregar(
            "electrica",
            "Instalación eléctrica",
            piso.nombre,
            "punto",
            round(puntos) * veces,
            "proporcion",
            detalle + sufijo,
        )

        banos_plano += piso.banos * veces
        cocinas_plano += piso.cocinas * veces

    agregar(
        "fierro",
        "Fierro en columnas, vigas y losas",
        None,
        "kg",
        hormigon_total * FIERRO_ELEVADO,
        "proporcion",
        f"{_m(hormigon_total)} m³ × {FIERRO_ELEVADO} kg/m³",
    )

    ultimo = pisos[-1]
    if ultimo.area_cubierta is not None:
        area_cubierta, origen_cubierta, detalle_cubierta = ultimo.area_cubierta, "plano", "Cubierta del modelo"
    else:
        factor = FACTOR_CUBIERTA.get(formulario.cubierta, 1.0)
        area_cubierta = ultimo.area_planta * factor
        origen_cubierta = "plano"
        detalle_cubierta = f"{_m(ultimo.area_planta)} m² del último piso × {_m(factor)} por pendiente y aleros"
    agregar(
        "cubierta",
        NOMBRES_CUBIERTA.get(formulario.cubierta, "Cubierta"),
        None,
        "m²",
        area_cubierta,
        origen_cubierta,
        detalle_cubierta,
    )

    banos = formulario.banos if formulario.banos is not None else banos_plano
    cocinas = formulario.cocinas if formulario.cocinas is not None else cocinas_plano
    origen_san = origen_formulario if formulario.banos is not None or formulario.cocinas is not None else "plano"
    if banos or cocinas:
        puntos = banos * PUNTOS_SANITARIOS["bano"] + cocinas * PUNTOS_SANITARIOS["cocina"]
        agregar(
            "sanitaria",
            "Instalación sanitaria",
            None,
            "punto",
            puntos,
            origen_san,
            f"{banos} baños × {PUNTOS_SANITARIOS['bano']} + {cocinas} cocinas × {PUNTOS_SANITARIOS['cocina']}",
        )
    return cantidades
