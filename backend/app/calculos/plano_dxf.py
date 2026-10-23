"""Lector de planos DXF en texto (ASCII), escrito desde cero.

Solo saca lo que la estimación necesita: unidades, capas, líneas, polilíneas, sombreados, bloques
insertados (puertas, ventanas), arcos y textos. Los bloques se explotan (con su posición, escala y giro)
para que un plano dibujado dentro de un bloque también se lea; además cada inserción queda como una
entidad `bloque` para poder contar puertas y ventanas.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# Más que esto no es un plano de vivienda sino algo que no conviene procesar en la petición.
MAX_ENTIDADES = 400_000
_PROFUNDIDAD_BLOQUES = 4


class PlanoInvalido(ValueError):
    """El archivo no se puede leer como DXF; el mensaje es para el constructor."""


@dataclass
class Entidad:
    tipo: str  # linea, polilinea, bloque, arco, texto
    capa: str
    puntos: list[tuple[float, float]]
    cerrada: bool = False
    nombre: str = ""  # nombre del bloque o contenido del texto
    tamano: float = 0.0  # bloque: lado mayor; arco: radio (en unidades del dibujo)
    giro: float = 0.0  # bloque: grados; puertas y ventanas se dibujan a lo largo de su eje x


@dataclass
class Dibujo:
    unidades: int | None  # código $INSUNITS del encabezado (4 mm, 5 cm, 6 m…)
    capas: list[str]
    entidades: list[Entidad]
    avisos: list[str] = field(default_factory=list)


@dataclass
class _Bloque:
    base: tuple[float, float]
    entidades: list[Entidad]
    inserciones: list[_Insercion]
    ancho: float = 0.0


@dataclass
class _Insercion:
    nombre: str
    capa: str
    punto: tuple[float, float]
    escala: tuple[float, float]
    giro: float  # grados


def decodificar(datos: bytes) -> str:
    if datos.startswith(b"AutoCAD Binary DXF"):
        raise PlanoInvalido("El DXF está guardado en formato binario. Guárdalo como DXF de texto (ASCII).")
    if datos[:4].startswith(b"AC10"):
        raise PlanoInvalido("Es un archivo DWG. En tu programa de dibujo usa “Guardar como” → DXF.")
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        return datos.decode("cp1252", errors="replace")


def _pares(texto: str) -> list[tuple[int, str]]:
    lineas = texto.splitlines()
    pares = []
    for i in range(0, len(lineas) - 1, 2):
        codigo = lineas[i].strip()
        if not codigo.lstrip("-").isdigit():
            raise PlanoInvalido("El archivo no parece un DXF válido.")
        pares.append((int(codigo), lineas[i + 1].strip()))
    return pares


def _registros(pares: list[tuple[int, str]], desde: int, hasta: int) -> list[tuple[str, list[tuple[int, str]]]]:
    """Agrupa los pares en registros que empiezan con código 0 (una entidad, un bloque…)."""
    registros: list[tuple[str, list[tuple[int, str]]]] = []
    for codigo, valor in pares[desde:hasta]:
        if codigo == 0:
            registros.append((valor, []))
        elif registros:
            registros[-1][1].append((codigo, valor))
    return registros


def _num(valor: str) -> float:
    try:
        return float(valor)
    except ValueError:
        return 0.0


def _primero(datos: list[tuple[int, str]], codigo: int, defecto: str = "") -> str:
    return next((v for c, v in datos if c == codigo), defecto)


def _punto(datos: list[tuple[int, str]], cx: int = 10, cy: int = 20) -> tuple[float, float]:
    return (_num(_primero(datos, cx, "0")), _num(_primero(datos, cy, "0")))


def _limpiar_mtext(texto: str) -> str:
    texto = texto.replace("\\P", " ").replace("\\~", " ")
    texto = re.sub(r"\\[A-Za-z][^;\\]*;", "", texto)
    texto = re.sub(r"\\[A-Za-z]", "", texto)
    return " ".join(texto.replace("{", "").replace("}", "").split())


def _vertices_lw(datos: list[tuple[int, str]]) -> list[tuple[float, float]]:
    puntos: list[tuple[float, float]] = []
    x: float | None = None
    for codigo, valor in datos:
        if codigo == 10:
            x = _num(valor)
        elif codigo == 20 and x is not None:
            puntos.append((x, _num(valor)))
            x = None
    return puntos


def _contornos_sombreado(datos: list[tuple[int, str]]) -> list[list[tuple[float, float]]]:
    """Contornos de un HATCH: polilíneas y bordes de líneas o arcos (elipses y splines se omiten)."""
    contornos: list[list[tuple[float, float]]] = []
    i, n = 0, len(datos)
    while i < n and datos[i][0] != 91:
        i += 1
    if i >= n:
        return contornos
    total = int(_num(datos[i][1]))
    i += 1
    for _ in range(total):
        while i < n and datos[i][0] != 92:
            i += 1
        if i >= n:
            break
        bandera = int(_num(datos[i][1]))
        i += 1
        puntos: list[tuple[float, float]] = []
        if bandera & 2:  # polilínea
            while i < n and datos[i][0] != 93:
                i += 1
            cantidad = int(_num(datos[i][1])) if i < n else 0
            i += 1
            while len(puntos) < cantidad and i + 1 < n:
                if datos[i][0] == 10 and datos[i + 1][0] == 20:
                    puntos.append((_num(datos[i][1]), _num(datos[i + 1][1])))
                    i += 2
                else:
                    i += 1
        else:
            while i < n and datos[i][0] != 93:
                i += 1
            bordes = int(_num(datos[i][1])) if i < n else 0
            i += 1
            valido = True
            for _ in range(bordes):
                while i < n and datos[i][0] != 72:
                    i += 1
                if i >= n:
                    break
                tipo = int(_num(datos[i][1]))
                i += 1
                valores: dict[int, str] = {}
                while i < n and datos[i][0] not in (72, 92, 97):
                    valores.setdefault(datos[i][0], datos[i][1])
                    i += 1
                if tipo == 1:
                    puntos.append((_num(valores.get(10, "0")), _num(valores.get(20, "0"))))
                elif tipo == 2:
                    cx, cy, r = _num(valores.get(10, "0")), _num(valores.get(20, "0")), _num(valores.get(40, "0"))
                    a0, a1 = math.radians(_num(valores.get(50, "0"))), math.radians(_num(valores.get(51, "0")))
                    if valores.get(73, "1") == "0":
                        a0, a1 = -a0, -a1
                    puntos.append((cx + r * math.cos(a0), cy + r * math.sin(a0)))
                    puntos.append((cx + r * math.cos(a1), cy + r * math.sin(a1)))
                else:
                    valido = False
            if not valido:
                puntos = []
        if len(puntos) >= 3:
            contornos.append(puntos)
    return contornos


def _convertir(
    tipo: str, datos: list[tuple[int, str]], vertices: list[tuple[float, float]] | None = None
) -> list[Entidad] | _Insercion | None:
    capa = _primero(datos, 8, "0")
    if tipo == "LINE":
        return [Entidad("linea", capa, [_punto(datos), _punto(datos, 11, 21)])]
    if tipo == "LWPOLYLINE":
        puntos = _vertices_lw(datos)
        cerrada = bool(int(_num(_primero(datos, 70, "0"))) & 1)
        return [Entidad("polilinea", capa, puntos, cerrada)] if len(puntos) >= 2 else []
    if tipo == "POLYLINE":
        bandera = int(_num(_primero(datos, 70, "0")))
        if bandera & (16 | 64) or not vertices or len(vertices) < 2:  # mallas 3D: no son planta
            return []
        return [Entidad("polilinea", capa, vertices, bool(bandera & 1))]
    if tipo == "SOLID":
        esquinas = [_punto(datos, 10, 20), _punto(datos, 11, 21), _punto(datos, 13, 23), _punto(datos, 12, 22)]
        return [Entidad("polilinea", capa, esquinas, True)]
    if tipo == "HATCH":
        return [Entidad("polilinea", capa, c, True) for c in _contornos_sombreado(datos)]
    if tipo in ("ARC", "CIRCLE"):
        return [Entidad("arco", capa, [_punto(datos)], tamano=_num(_primero(datos, 40, "0")))]
    if tipo in ("TEXT", "ATTRIB"):
        texto = _primero(datos, 1).strip()
        return [Entidad("texto", capa, [_punto(datos)], nombre=texto)] if texto else []
    if tipo == "MTEXT":
        texto = _limpiar_mtext("".join(v for c, v in datos if c == 3) + _primero(datos, 1))
        return [Entidad("texto", capa, [_punto(datos)], nombre=texto)] if texto else []
    if tipo in ("INSERT", "MINSERT"):
        escala = (_num(_primero(datos, 41, "1")) or 1.0, _num(_primero(datos, 42, "1")) or 1.0)
        return _Insercion(_primero(datos, 2), capa, _punto(datos), escala, _num(_primero(datos, 50, "0")))
    return None


def _leer_entidades(registros: list[tuple[str, list[tuple[int, str]]]]) -> tuple[list[Entidad], list[_Insercion]]:
    entidades: list[Entidad] = []
    inserciones: list[_Insercion] = []
    i = 0
    while i < len(registros):
        tipo, datos = registros[i]
        vertices: list[tuple[float, float]] | None = None
        if tipo == "POLYLINE":
            vertices = []
            i += 1
            while i < len(registros) and registros[i][0] == "VERTEX":
                vertices.append(_punto(registros[i][1]))
                i += 1
            if i < len(registros) and registros[i][0] == "SEQEND":
                i += 1
            resultado = _convertir(tipo, datos, vertices)
        else:
            resultado = _convertir(tipo, datos)
            i += 1
        if isinstance(resultado, _Insercion):
            inserciones.append(resultado)
        elif resultado:
            entidades.extend(resultado)
    return entidades, inserciones


def _caja(puntos: list[tuple[float, float]]) -> tuple[float, float, float, float] | None:
    if not puntos:
        return None
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return min(xs), min(ys), max(xs), max(ys)


def _ancho_bloque(entidades: list[Entidad]) -> float:
    puntos: list[tuple[float, float]] = []
    for e in entidades:
        if e.tipo == "arco":
            (x, y), r = e.puntos[0], e.tamano
            puntos += [(x - r, y - r), (x + r, y + r)]
        elif e.tipo != "texto":
            puntos += e.puntos
    caja = _caja(puntos)
    return 0.0 if caja is None else max(caja[2] - caja[0], caja[3] - caja[1])


Matriz = tuple[float, float, float, float, float, float]  # x' = a·x + b·y + e ; y' = c·x + d·y + f
_IDENTIDAD: Matriz = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _aplicar(m: Matriz, p: tuple[float, float]) -> tuple[float, float]:
    return (m[0] * p[0] + m[1] * p[1] + m[4], m[2] * p[0] + m[3] * p[1] + m[5])


def _componer(exterior: Matriz, interior: Matriz) -> Matriz:
    a, b, c, d, e, f = exterior
    a2, b2, c2, d2, e2, f2 = interior
    return (
        a * a2 + b * c2,
        a * b2 + b * d2,
        c * a2 + d * c2,
        c * b2 + d * d2,
        a * e2 + b * f2 + e,
        c * e2 + d * f2 + f,
    )


def _matriz_insercion(insercion: _Insercion, base: tuple[float, float]) -> Matriz:
    sx, sy = insercion.escala
    giro = math.radians(insercion.giro)
    cos_g, sin_g = math.cos(giro), math.sin(giro)
    a, b, c, d = cos_g * sx, -sin_g * sy, sin_g * sx, cos_g * sy
    px, py = insercion.punto
    # Primero se resta el punto base del bloque, después se escala, gira y traslada.
    return (a, b, c, d, px - a * base[0] - b * base[1], py - c * base[0] - d * base[1])


def _explotar(
    insercion: _Insercion, bloques: dict[str, _Bloque], salida: list[Entidad], padre: Matriz, profundidad: int
) -> None:
    bloque = bloques.get(insercion.nombre)
    if bloque is None or insercion.nombre.upper().startswith(("*D", "*T")):
        return
    m = _componer(padre, _matriz_insercion(insercion, bloque.base))
    factor = math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))
    salida.append(
        Entidad(
            "bloque",
            insercion.capa,
            [_aplicar(padre, insercion.punto)],
            nombre=insercion.nombre,
            tamano=bloque.ancho * factor,
            giro=math.degrees(math.atan2(m[2], m[0])),
        )
    )
    for e in bloque.entidades:
        # En un bloque, la capa "0" toma la capa de la inserción.
        capa = insercion.capa if e.capa == "0" else e.capa
        salida.append(Entidad(e.tipo, capa, [_aplicar(m, p) for p in e.puntos], e.cerrada, e.nombre, e.tamano * factor))
    if profundidad < _PROFUNDIDAD_BLOQUES and len(salida) <= MAX_ENTIDADES:
        for anidada in bloque.inserciones:
            capa = insercion.capa if anidada.capa == "0" else anidada.capa
            _explotar(
                _Insercion(anidada.nombre, capa, anidada.punto, anidada.escala, anidada.giro),
                bloques,
                salida,
                m,
                profundidad + 1,
            )


def leer_dxf(datos: bytes) -> Dibujo:
    pares = _pares(decodificar(datos))
    secciones: dict[str, tuple[int, int]] = {}
    i = 0
    while i < len(pares):
        if pares[i] == (0, "SECTION") and i + 1 < len(pares):
            nombre = pares[i + 1][1].upper()
            fin = next((j for j in range(i + 2, len(pares)) if pares[j] == (0, "ENDSEC")), len(pares))
            secciones[nombre] = (i + 2, fin)
            i = fin
        i += 1
    if "ENTITIES" not in secciones:
        raise PlanoInvalido("El archivo no parece un DXF válido: no tiene dibujo.")

    unidades = None
    if "HEADER" in secciones:
        a, b = secciones["HEADER"]
        for j in range(a, b - 1):
            if pares[j] == (9, "$INSUNITS"):
                unidades = int(_num(pares[j + 1][1])) or None
                break

    capas: list[str] = []
    if "TABLES" in secciones:
        for tipo, datos in _registros(pares, *secciones["TABLES"]):
            if tipo == "LAYER":
                nombre = _primero(datos, 2)
                if nombre and nombre not in capas:
                    capas.append(nombre)

    bloques: dict[str, _Bloque] = {}
    if "BLOCKS" in secciones:
        registros = _registros(pares, *secciones["BLOCKS"])
        actual: tuple[str, tuple[float, float]] | None = None
        contenido: list[tuple[str, list[tuple[int, str]]]] = []
        for tipo, datos in registros:
            if tipo == "BLOCK":
                actual = (_primero(datos, 2), _punto(datos))
                contenido = []
            elif tipo == "ENDBLK":
                if actual:
                    entidades, inserciones = _leer_entidades(contenido)
                    bloques[actual[0]] = _Bloque(actual[1], entidades, inserciones, _ancho_bloque(entidades))
                actual = None
            elif actual:
                contenido.append((tipo, datos))

    entidades, inserciones = _leer_entidades(_registros(pares, *secciones["ENTITIES"]))
    avisos: list[str] = []
    for insercion in inserciones:
        _explotar(insercion, bloques, entidades, _IDENTIDAD, 1)
        if len(entidades) > MAX_ENTIDADES:
            avisos.append("El plano es muy grande; se leyó solo una parte. Borra láminas que no sean plantas.")
            break
    for e in entidades:
        if e.capa not in capas:
            capas.append(e.capa)
    return Dibujo(unidades, capas, entidades, avisos)
