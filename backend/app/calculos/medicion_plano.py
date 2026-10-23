"""Medición de un plano CAD ya leído: capas, unidades, plantas y medidas por planta. Sin base de datos.

Supuestos (se avisan al constructor y se confirman en el asistente):
- Los muros vienen dibujados con dos líneas paralelas (o como polígonos/sombreados) y cortados en los vanos.
- Cada planta es una zona separada del dibujo; las vistas que no son planta (cortes, fachadas) se ignoran
  en el paso de plantas.
"""

from __future__ import annotations

import bisect
import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

from app.calculos.computos import Abertura, PisoMedido
from app.calculos.plano_dxf import Dibujo, Entidad

ROLES = ("muros", "puertas", "ventanas", "ambientes", "columnas", "ignorar")
UNIDADES = {1: ("pulgadas", 0.0254), 2: ("pies", 0.3048), 4: ("mm", 0.001), 5: ("cm", 0.01), 6: ("m", 1.0)}

_PALABRAS_ROL = {
    "muros": ("MURO", "PARED", "WALL", "MAMPOST", "TABIQUE", "LADRILLO", "MURETE"),
    "puertas": ("PUERTA", "DOOR", "PTA", "PORTON"),
    "ventanas": ("VENTANA", "WINDOW", "GLAZ", "VENT", "VIDRIO"),
    "ambientes": ("AMBIENTE", "ROOM", "AREA", "LOCAL", "ESPACIO", "RECINTO"),
    "columnas": ("COLUMNA", "COLUMN", "PILAR", "COL"),
}
_IGNORAR = (
    "COTA",
    "DIM",
    "TEXTO",
    "TEXT",
    "EJE",
    "AXIS",
    "MOBIL",
    "FURN",
    "MARCO",
    "ROTULO",
    "CAJETIN",
    "DEFPOINTS",
    "VIEWPORT",
    "HATCH",
    "SOMBR",
    "LAMINA",
    "SANITAR",
    "ARTEF",
)
_NOMBRES_AMBIENTE = (
    "DORMITORIO",
    "BANO",
    "COCINA",
    "LIVING",
    "COMEDOR",
    "SALA",
    "ESTAR",
    "LAVANDERIA",
    "GARAJE",
    "GARAGE",
    "ESTUDIO",
    "DEPOSITO",
    "HALL",
    "PASILLO",
    "CIRCULACION",
    "DORM",
    "OFICINA",
    "LOCAL",
    "TIENDA",
    "SUITE",
    "VESTIDOR",
    "TERRAZA",
    "BALCON",
    "PATIO",
)

ESPESOR_MIN, ESPESOR_MAX = 0.05, 0.45  # m entre las dos caras de un muro
SEPARACION_PLANTAS = 1.5  # m de dibujo vacío que separa una planta de otra
MAX_SEGMENTOS_VISTA = 15_000


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.upper()


# --- Capas ---


def resumen_capas(dibujo: Dibujo) -> list[dict]:
    conteo: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    nombres_bloques: dict[str, list[str]] = defaultdict(list)
    for e in dibujo.entidades:
        conteo[e.capa][e.tipo] += 1
        if e.tipo == "bloque" and len(nombres_bloques[e.capa]) < 30:
            nombres_bloques[e.capa].append(e.nombre)
    resumen = []
    for capa in dibujo.capas:
        c = conteo.get(capa, {})
        if not c:
            continue
        resumen.append(
            {
                "nombre": capa,
                "lineas": c.get("linea", 0) + c.get("polilinea", 0),
                "bloques": c.get("bloque", 0),
                "arcos": c.get("arco", 0),
                "textos": c.get("texto", 0),
                "rol_sugerido": sugerir_rol(capa, nombres_bloques.get(capa, [])),
            }
        )
    return resumen


def sugerir_rol(capa: str, nombres_bloques: list[str] | None = None) -> str:
    nombre = normalizar(capa)
    partes = set(re.split(r"[^A-Z0-9]+", nombre))
    if any(p in nombre for p in _IGNORAR):
        return "ignorar"
    for rol, palabras in _PALABRAS_ROL.items():
        for palabra in palabras:
            # Las palabras cortas ("COL", "PTA", "VENT") solo valen como parte separada del nombre.
            if (len(palabra) <= 4 and palabra in partes) or (len(palabra) > 4 and palabra in nombre):
                return rol
    bloques = " ".join(normalizar(b) for b in nombres_bloques or [])
    if "PUERTA" in bloques or "DOOR" in bloques:
        return "puertas"
    if "VENTANA" in bloques or "WINDOW" in bloques:
        return "ventanas"
    return "ignorar"


# --- Unidades ---


def detectar_unidades(dibujo: Dibujo) -> tuple[int, bool]:
    """Código de unidades y si fue deducido (no venía en el archivo o no es una unidad de largo usual)."""
    if dibujo.unidades in UNIDADES:
        return dibujo.unidades, False
    puertas = sorted(
        e.tamano for e in dibujo.entidades if e.tipo == "bloque" and e.tamano > 0 and _parece_puerta(e.nombre)
    )
    if puertas:
        mediana = puertas[len(puertas) // 2]
        for codigo, (minimo, maximo) in ((6, (0.5, 1.5)), (5, (50, 150)), (4, (500, 1500))):
            if minimo <= mediana <= maximo:
                return codigo, True
    puntos = [p for e in dibujo.entidades if e.tipo in ("linea", "polilinea") for p in e.puntos]
    caja = _caja(puntos)
    if caja is None:
        return 6, True
    lado = max(caja[2] - caja[0], caja[3] - caja[1])
    if lado > 5000:
        return 4, True
    if lado > 300:
        return 5, True
    return 6, True


def _parece_puerta(nombre: str) -> bool:
    n = normalizar(nombre)
    return "PUERTA" in n or "DOOR" in n or bool(re.match(r"^P[-_ ]?\d", n))


def _parece_ventana(nombre: str) -> bool:
    n = normalizar(nombre)
    return "VENTANA" in n or "WINDOW" in n or bool(re.match(r"^V[-_ ]?\d", n))


# --- Geometría básica ---


def _caja(puntos) -> tuple[float, float, float, float] | None:
    if not puntos:
        return None
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return min(xs), min(ys), max(xs), max(ys)


def area_poligono(puntos: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x1, y1), (x2, y2) in zip(puntos, puntos[1:] + puntos[:1], strict=False):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def perimetro(puntos: list[tuple[float, float]], cerrada: bool) -> float:
    pares = list(zip(puntos, puntos[1:] + (puntos[:1] if cerrada else []), strict=False))
    return sum(math.dist(a, b) for a, b in pares)


def dentro(punto: tuple[float, float], poligono: list[tuple[float, float]]) -> bool:
    x, y = punto
    adentro = False
    for (x1, y1), (x2, y2) in zip(poligono, poligono[1:] + poligono[:1], strict=False):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            adentro = not adentro
    return adentro


def _segmentos(e: Entidad) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    puntos = e.puntos
    pares = list(zip(puntos, puntos[1:], strict=False))
    if e.cerrada and len(puntos) > 2:
        pares.append((puntos[-1], puntos[0]))
    return [(a, b) for a, b in pares if a != b]


# --- Plantas (zonas separadas del dibujo) ---


@dataclass
class Region:
    caja: tuple[float, float, float, float]  # en metros
    indices: list[int] = field(default_factory=list)  # entidades del dibujo que caen en la zona


def _agrupar(cajas: list[tuple[int, tuple[float, float, float, float]]], eje: int, margen: float):
    """Separa en grupos por huecos vacíos mayores que `margen` a lo largo de un eje (0 = x, 1 = y)."""
    orden = sorted(cajas, key=lambda c: c[1][eje])
    grupos: list[list[tuple[int, tuple[float, float, float, float]]]] = []
    fin = -math.inf
    for item in orden:
        caja = item[1]
        if not grupos or caja[eje] > fin + margen:
            grupos.append([])
            fin = -math.inf
        grupos[-1].append(item)
        fin = max(fin, caja[eje + 2])
    return grupos


def detectar_regiones(dibujo: Dibujo, roles: dict[str, str], factor: float) -> list[Region]:
    utiles = {"muros", "puertas", "ventanas", "ambientes", "columnas"}
    hay_muros = any(r == "muros" for r in roles.values())
    cajas = []
    for i, e in enumerate(dibujo.entidades):
        rol = roles.get(e.capa, "ignorar")
        if e.tipo == "texto" or (rol not in utiles if hay_muros else rol == "ignorar"):
            continue
        caja = _caja(e.puntos)
        if caja is None:
            continue
        cajas.append((i, tuple(v * factor for v in caja)))
    grupos = [cajas]
    for eje in (0, 1, 0, 1):
        grupos = [g for grupo in grupos for g in _agrupar(grupo, eje, SEPARACION_PLANTAS)]
    regiones = []
    for grupo in grupos:
        caja = (
            min(c[1][0] for c in grupo),
            min(c[1][1] for c in grupo),
            max(c[1][2] for c in grupo),
            max(c[1][3] for c in grupo),
        )
        # Menos de 2 m de lado: un detalle o un símbolo suelto, no una planta.
        if max(caja[2] - caja[0], caja[3] - caja[1]) < 2.0 or len(grupo) < 4:
            continue
        regiones.append(Region(caja, [c[0] for c in grupo]))
    # Se agregan los textos de cada zona (nombres de ambientes) aunque estén en capas ignoradas.
    for i, e in enumerate(dibujo.entidades):
        if e.tipo != "texto":
            continue
        x, y = e.puntos[0][0] * factor, e.puntos[0][1] * factor
        for r in regiones:
            if r.caja[0] <= x <= r.caja[2] and r.caja[1] <= y <= r.caja[3]:
                r.indices.append(i)
                break
    regiones.sort(key=lambda r: (r.caja[0], -r.caja[3]))
    return regiones


# --- Muros ---


def medir_muros(
    segmentos: list[tuple[tuple[float, float], tuple[float, float]]],
    poligonos: list[list[tuple[float, float]]],
) -> tuple[float, float | None, list[str]]:
    """Largo de eje (m) y espesor más común. Coordenadas ya en metros y cerca del origen."""
    avisos: list[str] = []
    largo_lineas, espesor_lineas = _muros_por_pares(segmentos)
    largo_pol = 0.0
    espesores_pol = []
    for pol in poligonos:
        area = area_poligono(pol)
        per = perimetro(pol, True)
        if per <= 0:
            continue
        espesor = 2 * area / per
        if ESPESOR_MIN * 0.8 <= espesor <= ESPESOR_MAX:
            largo_pol += per / 2
            espesores_pol.append((espesor, per / 2))
    espesor_pol = _mediana_ponderada(espesores_pol)
    if largo_lineas and largo_pol:
        # Muro dibujado con líneas y además relleno: es el mismo muro, no se suma dos veces.
        if min(largo_lineas, largo_pol) / max(largo_lineas, largo_pol) > 0.6:
            if largo_pol >= largo_lineas:
                return largo_pol, espesor_pol or espesor_lineas, avisos
            return largo_lineas, espesor_lineas or espesor_pol, avisos
        return largo_lineas + largo_pol, espesor_lineas or espesor_pol, avisos
    if largo_pol:
        return largo_pol, espesor_pol, avisos
    if largo_lineas:
        return largo_lineas, espesor_lineas, avisos
    total = sum(math.dist(a, b) for a, b in segmentos)
    if total:
        avisos.append("Los muros están dibujados con una sola línea: se tomó cada línea como el eje del muro.")
    return total, None, avisos


def _mediana_ponderada(valores: list[tuple[float, float]]) -> float | None:
    if not valores:
        return None
    valores = sorted(valores)
    mitad = sum(p for _, p in valores) / 2
    acumulado = 0.0
    for valor, peso in valores:
        acumulado += peso
        if acumulado >= mitad:
            return round(valor, 3)
    return round(valores[-1][0], 3)


def _muros_por_pares(segmentos) -> tuple[float, float | None]:
    """Muros de dos líneas paralelas: cada cara aporta la parte que tiene otra cara enfrente, a una
    distancia de espesor de muro. El eje es la mitad de la suma (cada muro se ve desde sus dos caras).
    Si casi nada tiene pareja, los muros están dibujados con una sola línea y se devuelve 0."""
    datos = []
    radio = 0.0
    for a, b in segmentos:
        largo = math.dist(a, b)
        if largo < 0.03:
            continue
        angulo = math.atan2(b[1] - a[1], b[0] - a[0]) % math.pi
        ux, uy = math.cos(angulo), math.sin(angulo)
        datos.append((a, b, largo, angulo, ux, uy, -uy * a[0] + ux * a[1]))
        radio = max(radio, math.hypot(*a), math.hypot(*b))
    if not datos:
        return 0.0, None
    paso = math.radians(0.5)
    cubetas: dict[int, list[int]] = defaultdict(list)
    for i, d in enumerate(datos):
        cubetas[round(d[3] / paso) % round(math.pi / paso)].append(i)
    ordenadas = {k: sorted(v, key=lambda i: datos[i][6]) for k, v in cubetas.items()}
    claves_d = {k: [datos[i][6] for i in v] for k, v in ordenadas.items()}
    total_cubetas = round(math.pi / paso)
    ventana = ESPESOR_MAX + radio * 2 * paso

    cubierto_total = 0.0
    largo_total = 0.0
    espesores: list[tuple[float, float]] = []
    for i, (a, b, largo, angulo, ux, uy, di) in enumerate(datos):
        largo_total += largo
        nx, ny = -uy, ux
        t0, t1 = sorted((ux * a[0] + uy * a[1], ux * b[0] + uy * b[1]))
        intervalos = []
        k = round(angulo / paso) % total_cubetas
        for kk in ((k - 1) % total_cubetas, k, (k + 1) % total_cubetas):
            if kk not in ordenadas:
                continue
            lista, claves = ordenadas[kk], claves_d[kk]
            desde = bisect.bisect_left(claves, di - ventana)
            hasta = bisect.bisect_right(claves, di + ventana)
            for j in lista[desde:hasta]:
                if j == i:
                    continue
                a2, b2, largo2, angulo2 = datos[j][:4]
                diferencia = abs(angulo - angulo2)
                if min(diferencia, math.pi - diferencia) > math.radians(2):
                    continue
                medio = ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)
                separacion = abs(nx * medio[0] + ny * medio[1] - di)
                if not ESPESOR_MIN <= separacion <= ESPESOR_MAX:
                    continue
                s0, s1 = sorted((ux * a2[0] + uy * a2[1], ux * b2[0] + uy * b2[1]))
                inicio, fin = max(t0, s0), min(t1, s1)
                if fin - inicio > 0.02:
                    intervalos.append((inicio, fin, separacion))
        if not intervalos:
            continue
        intervalos.sort()
        cubierto = 0.0
        actual_ini, actual_fin = intervalos[0][0], intervalos[0][1]
        for ini, fin, _s in intervalos[1:]:
            if ini > actual_fin:
                cubierto += actual_fin - actual_ini
                actual_ini, actual_fin = ini, fin
            else:
                actual_fin = max(actual_fin, fin)
        cubierto += actual_fin - actual_ini
        cubierto_total += cubierto
        cercana = min(intervalos, key=lambda x: x[2])
        espesores.append((cercana[2], cubierto))
    if largo_total == 0 or cubierto_total / largo_total < 0.3:
        return 0.0, None
    return cubierto_total / 2, _mediana_ponderada(espesores)


# --- Contorno de la planta (área y perímetro de fachada) ---


def contorno(
    segmentos: list[tuple[tuple[float, float], tuple[float, float]]],
    vanos: list[tuple[tuple[float, float], tuple[float, float]]],
    ancho: float,
    alto: float,
) -> tuple[float, float, bool]:
    """Área encerrada por los muros y perímetro de fachada, rellenando desde afuera en una grilla.
    Los vanos (puertas y ventanas, como segmentos) se cierran y además se cierran huecos de hasta ~1,5 m
    para que el relleno no entre por una abertura sin bloque. Devuelve (área, perímetro, confiable)."""
    celda = max(0.1, max(ancho, alto) / 400)
    radio = max(1, round(0.75 / celda))
    # El margen vacío alrededor tiene que ser mayor que el cierre, para que el relleno rodee la planta.
    borde = radio + 3
    columnas, filas = int(ancho / celda) + 2 * borde + 1, int(alto / celda) + 2 * borde + 1
    margen = borde * celda
    muro = [[False] * columnas for _ in range(filas)]

    def marcar(x: float, y: float):
        c, f = int((x + margen) / celda), int((y + margen) / celda)
        if 0 <= f < filas and 0 <= c < columnas:
            muro[f][c] = True

    for a, b in segmentos + vanos:
        pasos = max(1, int(math.dist(a, b) / (celda / 2)))
        for k in range(pasos + 1):
            t = k / pasos
            marcar(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    cerrado = _dilatar(muro, radio)
    afuera = _rellenar_afuera(cerrado)
    # Se devuelve el afuera a su tamaño real (deshace la dilatación del cierre).
    afuera = _dilatar(afuera, radio)
    adentro = [[not afuera[f][c] for c in range(columnas)] for f in range(filas)]
    celdas = sum(sum(fila) for fila in adentro)
    area = celdas * celda * celda
    bordes = 0
    for f in range(filas):
        for c in range(columnas):
            if adentro[f][c]:
                for df, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ff, cc = f + df, c + dc
                    if not (0 <= ff < filas and 0 <= cc < columnas) or not adentro[ff][cc]:
                        bordes += 1
    perim = bordes * celda
    # Un perímetro escalonado en diagonal se pasa de largo; los muros rectos (lo usual) no.
    confiable = area >= 0.3 * ancho * alto
    return area, perim, confiable


def _dilatar(grilla: list[list[bool]], radio: int) -> list[list[bool]]:
    filas, columnas = len(grilla), len(grilla[0])
    horizontal = []
    for fila in grilla:
        prefijo = [0]
        for v in fila:
            prefijo.append(prefijo[-1] + v)
        horizontal.append(
            [prefijo[min(columnas, c + radio + 1)] - prefijo[max(0, c - radio)] > 0 for c in range(columnas)]
        )
    resultado = [[False] * columnas for _ in range(filas)]
    for c in range(columnas):
        prefijo = [0]
        for f in range(filas):
            prefijo.append(prefijo[-1] + horizontal[f][c])
        for f in range(filas):
            resultado[f][c] = prefijo[min(filas, f + radio + 1)] - prefijo[max(0, f - radio)] > 0
    return resultado


def _rellenar_afuera(muro: list[list[bool]]) -> list[list[bool]]:
    filas, columnas = len(muro), len(muro[0])
    afuera = [[False] * columnas for _ in range(filas)]
    pila = [(0, 0)]
    afuera[0][0] = True
    while pila:
        f, c = pila.pop()
        for ff, cc in ((f + 1, c), (f - 1, c), (f, c + 1), (f, c - 1)):
            if 0 <= ff < filas and 0 <= cc < columnas and not afuera[ff][cc] and not muro[ff][cc]:
                afuera[ff][cc] = True
                pila.append((ff, cc))
    return afuera


# --- Aberturas y ambientes ---


def medidas_de_nombre(nombre: str) -> tuple[float | None, float | None]:
    """Ancho y alto en metros desde nombres como "P-090", "V120x100" o "PUERTA 80"."""
    n = normalizar(nombre)
    doble = re.search(r"(\d{2,4})\s*[X×]\s*(\d{2,4})", n)
    numeros = [doble.group(1), doble.group(2)] if doble else re.findall(r"\d{2,4}", n)[:1]
    medidas = []
    for texto in numeros:
        valor = int(texto)
        if 50 <= valor <= 400:
            medidas.append(valor / 100)
        elif 500 <= valor <= 4000:
            medidas.append(valor / 1000)
        else:
            medidas.append(None)
    while len(medidas) < 2:
        medidas.append(None)
    return medidas[0], medidas[1]


def _nombre_ambiente(textos: list[str]) -> str | None:
    for t in textos:
        if any(p in normalizar(t) for p in _NOMBRES_AMBIENTE):
            return t
    for t in textos:
        if re.search(r"[A-Za-z]{3,}", t) and not re.search(r"\d+[.,]?\d*\s*M", normalizar(t)):
            return t
    return None


def _contar_ambientes(nombres: list[str]) -> tuple[int, int]:
    banos = sum(1 for n in nombres if re.search(r"\bBANO|\bWC\b|SS\.?HH|SANITARIO", normalizar(n)))
    cocinas = sum(1 for n in nombres if re.search(r"COCINA|KITCHEN|KITCHENETTE", normalizar(n)))
    return banos, cocinas


# --- Medición de una planta ---


@dataclass
class PlantaMedida:
    piso: PisoMedido
    geometria: dict
    avisos: list[str]


def medir_planta(dibujo: Dibujo, region: Region, roles: dict[str, str], factor: float, nombre: str) -> PlantaMedida:
    ox, oy = region.caja[0], region.caja[1]
    ancho, alto = region.caja[2] - ox, region.caja[3] - oy

    def m(p: tuple[float, float]) -> tuple[float, float]:
        return (p[0] * factor - ox, p[1] * factor - oy)

    segmentos_muro = []  # todos: para el contorno y la vista
    segmentos_lineas = []  # solo los muros de líneas: los polígonos se miden aparte
    poligonos_muro = []
    ambientes_pol: list[list[tuple[float, float]]] = []
    bloques: list[tuple[Entidad, str]] = []
    arcos_puerta: list[Entidad] = []
    columnas: set[tuple[int, int]] = set()
    textos: list[tuple[tuple[float, float], str]] = []
    for i in region.indices:
        e = dibujo.entidades[i]
        rol = roles.get(e.capa, "ignorar")
        if e.tipo == "texto":
            textos.append((m(e.puntos[0]), e.nombre))
            continue
        if rol == "muros" and e.tipo in ("linea", "polilinea"):
            puntos = [m(p) for p in e.puntos]
            if e.cerrada and len(puntos) >= 3:
                area, per = area_poligono(puntos), perimetro(puntos, True)
                if per and 2 * area / per <= ESPESOR_MAX:
                    poligonos_muro.append(puntos)
                    segmentos_muro += _segmentos(Entidad("polilinea", "", puntos, True))
                    continue
            nuevos = _segmentos(Entidad(e.tipo, "", puntos, e.cerrada))
            segmentos_muro += nuevos
            segmentos_lineas += nuevos
        elif rol == "ambientes" and e.tipo == "polilinea" and e.cerrada and len(e.puntos) >= 3:
            puntos = [m(p) for p in e.puntos]
            if area_poligono(puntos) >= 1.0:
                ambientes_pol.append(puntos)
        elif e.tipo == "bloque" and rol != "ignorar":
            if rol in ("puertas", "ventanas"):
                bloques.append((e, rol))
            elif rol == "columnas":
                x, y = m(e.puntos[0])
                columnas.add((round(x * 5), round(y * 5)))
            elif _parece_puerta(e.nombre):
                bloques.append((e, "puertas"))
            elif _parece_ventana(e.nombre):
                bloques.append((e, "ventanas"))
        elif rol == "puertas" and e.tipo == "arco":
            arcos_puerta.append(e)
        elif rol == "columnas" and e.tipo == "polilinea" and e.cerrada:
            puntos = [m(p) for p in e.puntos]
            if area_poligono(puntos) <= 0.6:
                cx = sum(p[0] for p in puntos) / len(puntos)
                cy = sum(p[1] for p in puntos) / len(puntos)
                columnas.add((round(cx * 5), round(cy * 5)))

    avisos: list[str] = []
    largo, espesor, avisos_muro = medir_muros(segmentos_lineas, poligonos_muro)
    avisos += avisos_muro
    if not segmentos_muro:
        avisos.append(f"{nombre}: no encontramos muros. Revisa las capas de muros o corrige las cantidades.")

    puertas: list[Abertura] = []
    ventanas: list[Abertura] = []
    vista_aberturas = []
    vanos: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for e, rol in bloques:
        ancho_nombre, alto_nombre = medidas_de_nombre(e.nombre)
        ancho_ab = ancho_nombre or (e.tamano * factor if 0.4 <= e.tamano * factor <= 4.0 else None)
        if ancho_ab is None:
            ancho_ab = 0.9 if rol == "puertas" else 1.2
        x, y = m(e.puntos[0])
        lista = puertas if rol == "puertas" else ventanas
        lista.append(Abertura(round(ancho_ab, 2), alto_nombre if rol == "ventanas" else None))
        giro = math.radians(e.giro)
        fin = (x + ancho_ab * math.cos(giro), y + ancho_ab * math.sin(giro))
        vista_aberturas.append(
            {"tipo": rol[:-1], "x": round(x, 2), "y": round(y, 2), "x2": round(fin[0], 2), "y2": round(fin[1], 2)}
        )
        vanos.append(((x, y), fin))
    if not any(r == "puertas" for _, r in bloques):
        for e in arcos_puerta:
            radio = e.tamano * factor
            if 0.5 <= radio <= 1.5:
                x, y = m(e.puntos[0])
                puertas.append(Abertura(round(radio, 2)))
                # El arco de una puerta gira sobre la bisagra: el vano va de la bisagra al radio.
                vista_aberturas.append(
                    {"tipo": "puerta", "x": round(x, 2), "y": round(y, 2), "x2": round(x + radio, 2), "y2": round(y, 2)}
                )

    area_planta, perimetro_ext, confiable = contorno(segmentos_muro, vanos, ancho, alto)
    if not confiable or area_planta <= 0:
        area_planta, perimetro_ext = ancho * alto, 2 * (ancho + alto)
        if segmentos_muro:
            avisos.append(f"{nombre}: no pudimos cerrar el contorno; se usó el rectángulo que ocupa la planta.")

    ambientes: list[str] = []
    vista_ambientes = []
    area_ambientes = None
    if ambientes_pol:
        area_ambientes = 0.0
        for pol in ambientes_pol:
            area = area_poligono(pol)
            area_ambientes += area
            dentro_pol = [t for p, t in textos if dentro(p, pol)]
            nombre_amb = _nombre_ambiente(dentro_pol) or f"Ambiente {len(ambientes) + 1}"
            ambientes.append(nombre_amb)
            vista_ambientes.append(
                {"nombre": nombre_amb, "area": round(area, 2), "puntos": [[round(x, 2), round(y, 2)] for x, y in pol]}
            )
    else:
        ambientes = [t for _, t in textos if any(p in normalizar(t) for p in _NOMBRES_AMBIENTE)]
    banos, cocinas = _contar_ambientes(ambientes)

    piso = PisoMedido(
        nombre=nombre,
        largo_muros=round(largo, 2),
        perimetro_exterior=round(perimetro_ext, 2),
        espesor_muros=espesor,
        area_planta=round(area_planta, 2),
        area_ambientes=None if area_ambientes is None else round(area_ambientes, 2),
        ambientes=ambientes,
        banos=banos,
        cocinas=cocinas,
        puertas=puertas,
        ventanas=ventanas,
        columnas=len(columnas),
    )
    paso = max(1, len(segmentos_muro) // MAX_SEGMENTOS_VISTA + 1)
    geometria = {
        "ancho": round(ancho, 2),
        "alto": round(alto, 2),
        "muros": [[round(a[0], 2), round(a[1], 2), round(b[0], 2), round(b[1], 2)] for a, b in segmentos_muro[::paso]],
        "ambientes": vista_ambientes,
        "aberturas": vista_aberturas,
    }
    return PlantaMedida(piso, geometria, avisos)


def resumen_region(dibujo: Dibujo, region: Region, roles: dict[str, str], factor: float) -> dict:
    """Datos cortos para elegir plantas en el paso 3: tamaño y una vista mínima de sus muros."""
    ox, oy = region.caja[0], region.caja[1]
    muros = []
    for i in region.indices:
        e = dibujo.entidades[i]
        if roles.get(e.capa) == "muros" and e.tipo in ("linea", "polilinea"):
            for a, b in _segmentos(e):
                muros.append(
                    [
                        round(a[0] * factor - ox, 2),
                        round(a[1] * factor - oy, 2),
                        round(b[0] * factor - ox, 2),
                        round(b[1] * factor - oy, 2),
                    ]
                )
    paso = max(1, len(muros) // 3000 + 1)
    return {
        "ancho": round(region.caja[2] - ox, 2),
        "alto": round(region.caja[3] - oy, 2),
        "tiene_muros": bool(muros),
        "muros": muros[::paso],
    }
