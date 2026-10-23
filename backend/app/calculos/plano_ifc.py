"""Lector de modelos BIM en IFC (formato STEP de texto), escrito desde cero.

Saca por piso (`IfcBuildingStorey`): muros, losas, columnas, vigas, puertas, ventanas, ambientes y
cubierta, con sus cantidades. Usa los conjuntos de cantidades del modelo (`Qto_…`) cuando existen; si no,
calcula con la geometría extruida más simple (perfil rectangular o poligonal × altura) y el eje del muro.
Lo que el modelo trae (alturas, espesores, materiales) reemplaza las preguntas del formulario.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from app.calculos.computos import Abertura, Formulario, PisoMedido
from app.calculos.medicion_plano import area_poligono, normalizar
from app.calculos.plano_dxf import PlanoInvalido


class Ref(int):
    """Referencia a otra entidad (#123)."""


class Enum(str):
    """Valor enumerado (.T., .ROOF.)."""


_REGISTRO = re.compile(r"#(\d+)\s*=\s*([A-Za-z0-9_]+)\s*\(((?:'(?:[^']|'')*'|[^;'])*)\)\s*;", re.S)
_PREFIJOS = {"MILLI": 0.001, "CENTI": 0.01, "DECI": 0.1, "KILO": 1000.0}
_UNIDADES_PIE = {"FOOT": 0.3048, "INCH": 0.0254}

MUROS = {"IFCWALL", "IFCWALLSTANDARDCASE", "IFCWALLELEMENTEDCASE"}
LOSAS = {"IFCSLAB", "IFCSLABSTANDARDCASE", "IFCSLABELEMENTEDCASE"}
COLUMNAS = {"IFCCOLUMN", "IFCCOLUMNSTANDARDCASE"}
VIGAS = {"IFCBEAM", "IFCBEAMSTANDARDCASE"}
PUERTAS = {"IFCDOOR", "IFCDOORSTANDARDCASE"}
VENTANAS = {"IFCWINDOW", "IFCWINDOWSTANDARDCASE"}
ELEMENTOS = MUROS | LOSAS | COLUMNAS | VIGAS | PUERTAS | VENTANAS | {"IFCSPACE", "IFCROOF"}


def _texto_step(crudo: str) -> str:
    """Decodifica las secuencias de IFC: '' → ', \\X2\\00F1\\X0\\ → ñ, \\X\\F1 → ñ."""
    texto = crudo.replace("''", "'")

    def x2(m: re.Match) -> str:
        hexa = m.group(1)
        return "".join(chr(int(hexa[i : i + 4], 16)) for i in range(0, len(hexa), 4))

    texto = re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", x2, texto)
    texto = re.sub(r"\\X\\([0-9A-Fa-f]{2})", lambda m: bytes.fromhex(m.group(1)).decode("latin-1"), texto)
    return texto


def _argumentos(texto: str) -> list:
    valores, _ = _lista(texto, 0, cierre=None)
    return valores


def _lista(texto: str, i: int, cierre: str | None) -> tuple[list, int]:
    valores: list = []
    n = len(texto)
    while i < n:
        c = texto[i]
        if c in " \r\n\t,":
            i += 1
        elif c == ")":
            return valores, i + 1
        elif c == "(":
            sub, i = _lista(texto, i + 1, ")")
            valores.append(sub)
        elif c == "'":
            j = i + 1
            while j < n:
                if texto[j] == "'":
                    if j + 1 < n and texto[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            valores.append(_texto_step(texto[i + 1 : j]))
            i = j + 1
        elif c == "#":
            j = i + 1
            while j < n and texto[j].isdigit():
                j += 1
            valores.append(Ref(int(texto[i + 1 : j])))
            i = j
        elif c in "$*":
            valores.append(None)
            i += 1
        elif c == ".":
            j = texto.index(".", i + 1)
            valores.append(Enum(texto[i + 1 : j]))
            i = j + 1
        elif c.isalpha():
            j = i
            while j < n and (texto[j].isalnum() or texto[j] == "_"):
                j += 1
            # Valor con tipo, como IFCLENGTHMEASURE(2.5): se guarda solo el valor.
            k = j
            while k < n and texto[k] in " \t":
                k += 1
            if k < n and texto[k] == "(":
                sub, i = _lista(texto, k + 1, ")")
                valores.append(sub[0] if len(sub) == 1 else sub)
            else:
                valores.append(Enum(texto[i:j]))
                i = j
        else:
            j = i
            while j < n and texto[j] not in ",)":
                j += 1
            crudo = texto[i:j].strip()
            try:
                valores.append(float(crudo) if any(ch in crudo for ch in ".Ee") else int(crudo))
            except ValueError:
                valores.append(None)
            i = j
    if cierre:
        raise PlanoInvalido("El archivo IFC está incompleto o dañado.")
    return valores, i


class Modelo:
    def __init__(self, texto: str):
        if "ISO-10303-21" not in texto[:200] or "DATA;" not in texto:
            raise PlanoInvalido("El archivo no parece un IFC válido.")
        self._crudo: dict[int, tuple[str, str]] = {}
        self.por_tipo: dict[str, list[int]] = defaultdict(list)
        for m in _REGISTRO.finditer(texto, texto.index("DATA;")):
            numero, tipo = int(m.group(1)), m.group(2).upper()
            self._crudo[numero] = (tipo, m.group(3))
            self.por_tipo[tipo].append(numero)
        self._cache: dict[int, list] = {}
        if not self._crudo:
            raise PlanoInvalido("El archivo IFC no tiene elementos.")

    def tipo(self, ref: int | None) -> str:
        return self._crudo[ref][0] if ref in self._crudo else ""

    def args(self, ref: int | None) -> list:
        if ref is None or ref not in self._crudo:
            return []
        if ref not in self._cache:
            self._cache[ref] = _argumentos(self._crudo[ref][1])
        return self._cache[ref]

    def arg(self, ref: int | None, indice: int):
        datos = self.args(ref)
        return datos[indice] if indice < len(datos) else None

    def de_tipos(self, tipos: set[str]) -> list[int]:
        return [n for t in tipos for n in self.por_tipo.get(t, [])]


def _num(valor) -> float | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, Ref):
        return float(valor)
    return None


@dataclass
class _Elemento:
    ref: int
    tipo: str
    nombre: str = ""
    nombre_largo: str = ""
    cantidades: dict[str, float] = field(default_factory=dict)
    propiedades: dict[str, object] = field(default_factory=dict)
    materiales: list[str] = field(default_factory=list)
    espesor_material: float | None = None


@dataclass
class PisoLeido:
    nombre: str
    elevacion: float
    medido: PisoMedido
    elementos: dict[str, int]  # conteo por tipo, para el paso de pisos


@dataclass
class ModeloLeido:
    pisos: list[PisoLeido]
    formulario: Formulario  # lo que el modelo responde del formulario; el resto queda típico
    datos_del_modelo: list[str]  # campos del formulario que salieron del modelo
    avisos: list[str]


def _factores(modelo: Modelo) -> tuple[float, float, float]:
    largo = area = volumen = None
    for ref in modelo.por_tipo.get("IFCSIUNIT", []):
        _dims, tipo, prefijo, nombre = (modelo.args(ref) + [None] * 4)[:4]
        f = _PREFIJOS.get(str(prefijo), 1.0) if prefijo else 1.0
        if tipo == "LENGTHUNIT" and largo is None:
            largo = f
        elif tipo == "AREAUNIT" and area is None:
            area = f * f
        elif tipo == "VOLUMEUNIT" and volumen is None:
            volumen = f * f * f
    for ref in modelo.por_tipo.get("IFCCONVERSIONBASEDUNIT", []):
        datos = modelo.args(ref)
        if len(datos) >= 3 and datos[1] == "LENGTHUNIT" and str(datos[2]).upper() in _UNIDADES_PIE:
            largo = _UNIDADES_PIE[str(datos[2]).upper()]
    largo = largo or 1.0
    return largo, area or largo * largo, volumen or largo**3


def _geometria(modelo: Modelo, ref: int, factor: float) -> dict[str, float]:
    """Medidas simples desde la representación: eje (largo) y sólido extruido (perfil × altura)."""
    medidas: dict[str, float] = {}
    forma = modelo.arg(ref, 6)
    if modelo.tipo(forma) != "IFCPRODUCTDEFINITIONSHAPE":
        return medidas
    for rep in modelo.arg(forma, 2) or []:
        identificador = str(modelo.arg(rep, 1) or "")
        for item in modelo.arg(rep, 3) or []:
            tipo = modelo.tipo(item)
            if identificador == "Axis" and tipo == "IFCPOLYLINE":
                puntos = [modelo.arg(p, 0) or [] for p in modelo.arg(item, 0) or []]
                largo = sum(
                    ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
                    for a, b in zip(puntos, puntos[1:], strict=False)
                    if len(a) >= 2 and len(b) >= 2
                )
                if largo:
                    medidas["eje"] = largo * factor
            elif tipo == "IFCEXTRUDEDAREASOLID":
                perfil, profundidad = modelo.arg(item, 0), _num(modelo.arg(item, 3))
                if profundidad is None:
                    continue
                medidas["altura"] = profundidad * factor
                tipo_perfil = modelo.tipo(perfil)
                if tipo_perfil == "IFCRECTANGLEPROFILEDEF":
                    x, y = _num(modelo.arg(perfil, 3)), _num(modelo.arg(perfil, 4))
                    if x and y:
                        medidas["largo"] = max(x, y) * factor
                        medidas["ancho"] = min(x, y) * factor
                        medidas["area_perfil"] = x * y * factor * factor
                elif tipo_perfil == "IFCARBITRARYCLOSEDPROFILEDEF":
                    curva = modelo.arg(perfil, 2)
                    puntos = []
                    if modelo.tipo(curva) == "IFCPOLYLINE":
                        puntos = [modelo.arg(p, 0) or [] for p in modelo.arg(curva, 0) or []]
                    elif modelo.tipo(curva) == "IFCINDEXEDPOLYCURVE":
                        puntos = modelo.arg(modelo.arg(curva, 0), 0) or []
                    puntos = [(p[0], p[1]) for p in puntos if len(p) >= 2]
                    if len(puntos) >= 3:
                        medidas["area_perfil"] = area_poligono(puntos) * factor * factor
                if "area_perfil" in medidas:
                    medidas["volumen"] = medidas["area_perfil"] * medidas["altura"]
    return medidas


def leer_ifc(datos: bytes) -> ModeloLeido:
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        texto = datos.decode("latin-1")
    modelo = Modelo(texto)
    f_largo, f_area, f_volumen = _factores(modelo)
    avisos: list[str] = []

    elementos: dict[int, _Elemento] = {}
    for ref in modelo.de_tipos(ELEMENTOS):
        elementos[ref] = _Elemento(ref, modelo.tipo(ref), str(modelo.arg(ref, 2) or ""), str(modelo.arg(ref, 7) or ""))

    # Cantidades y propiedades asociadas a cada elemento
    for rel in modelo.por_tipo.get("IFCRELDEFINESBYPROPERTIES", []):
        relacionados, definicion = modelo.arg(rel, 4) or [], modelo.arg(rel, 5)
        tipo_def = modelo.tipo(definicion)
        valores: dict[str, float] = {}
        propiedades: dict[str, object] = {}
        if tipo_def == "IFCELEMENTQUANTITY":
            for q in modelo.arg(definicion, 5) or []:
                tipo_q, args_q = modelo.tipo(q), modelo.args(q)
                if len(args_q) < 4 or _num(args_q[3]) is None:
                    continue
                factor = {"IFCQUANTITYLENGTH": f_largo, "IFCQUANTITYAREA": f_area, "IFCQUANTITYVOLUME": f_volumen}
                valores[str(args_q[0])] = _num(args_q[3]) * factor.get(tipo_q, 1.0)
        elif tipo_def == "IFCPROPERTYSET":
            for p in modelo.arg(definicion, 4) or []:
                if modelo.tipo(p) == "IFCPROPERTYSINGLEVALUE":
                    propiedades[str(modelo.arg(p, 0))] = modelo.arg(p, 2)
        for r in relacionados:
            if r in elementos:
                elementos[r].cantidades.update({k: v for k, v in valores.items() if k not in elementos[r].cantidades})
                elementos[r].propiedades.update(propiedades)

    # Materiales
    for rel in modelo.por_tipo.get("IFCRELASSOCIATESMATERIAL", []):
        relacionados, material = modelo.arg(rel, 4) or [], modelo.arg(rel, 5)
        nombres: list[str] = []
        espesor = 0.0
        tipo_m = modelo.tipo(material)
        if tipo_m == "IFCMATERIALLAYERSETUSAGE":
            material, tipo_m = modelo.arg(material, 0), "IFCMATERIALLAYERSET"
        if tipo_m == "IFCMATERIAL":
            nombres.append(str(modelo.arg(material, 0) or ""))
        elif tipo_m == "IFCMATERIALLAYERSET":
            for capa in modelo.arg(material, 0) or []:
                nombres.append(str(modelo.arg(modelo.arg(capa, 0), 0) or ""))
                espesor += _num(modelo.arg(capa, 1)) or 0.0
        elif tipo_m == "IFCMATERIALLIST":
            nombres += [str(modelo.arg(m, 0) or "") for m in modelo.arg(material, 0) or []]
        for r in relacionados:
            if r in elementos:
                elementos[r].materiales += [n for n in nombres if n]
                if espesor:
                    elementos[r].espesor_material = espesor * f_largo

    # A qué piso pertenece cada elemento (directo o a través de un padre: cubierta → losas, piso → ambientes)
    piso_de: dict[int, int] = {}
    pisos_ref = modelo.por_tipo.get("IFCBUILDINGSTOREY", [])
    for rel in modelo.por_tipo.get("IFCRELCONTAINEDINSPATIALSTRUCTURE", []):
        estructura = modelo.arg(rel, 5)
        for r in modelo.arg(rel, 4) or []:
            piso_de[r] = estructura
    padre: dict[int, int] = {}
    for rel in modelo.por_tipo.get("IFCRELAGGREGATES", []):
        for r in modelo.arg(rel, 5) or []:
            padre[r] = modelo.arg(rel, 4)

    def piso_de_elemento(ref: int) -> int | None:
        actual, vistos = ref, 0
        while actual is not None and vistos < 10:
            if actual in pisos_ref:
                return actual
            if actual in piso_de:
                destino = piso_de[actual]
                if destino in pisos_ref:
                    return destino
                actual = destino
            else:
                actual = padre.get(actual)
            vistos += 1
        return None

    por_piso: dict[int, list[_Elemento]] = defaultdict(list)
    sin_piso = 0
    for e in elementos.values():
        p = piso_de_elemento(e.ref)
        if p is None:
            sin_piso += 1
        else:
            por_piso[p].append(e)
    if sin_piso:
        avisos.append(f"{sin_piso} elementos del modelo no están asignados a ningún piso y no se contaron.")

    geometrias: dict[int, dict[str, float]] = {}

    def medida(ref: int, clave: str) -> float | None:
        if ref not in geometrias:
            geometrias[ref] = _geometria(modelo, ref, f_largo)
        return geometrias[ref].get(clave)

    alturas: list[float] = []
    espesores_ext: list[float] = []
    espesores_int: list[float] = []
    espesores_losa: list[float] = []
    materiales_muro: list[str] = []
    hay_cubierta_losa = False
    sin_cantidades = 0
    pisos: list[PisoLeido] = []
    for ref in sorted(pisos_ref, key=lambda r: _num(modelo.arg(r, 9)) or 0.0):
        nombre = str(modelo.arg(ref, 2) or modelo.arg(ref, 7) or f"Piso {len(pisos) + 1}")
        elevacion = (_num(modelo.arg(ref, 9)) or 0.0) * f_largo
        medido = PisoMedido(nombre=nombre)
        conteo: dict[str, int] = defaultdict(int)
        largo = area_muros = area_ext = perim_ext = hormigon = area_losa = area_cubierta = 0.0
        hay_externos = False
        alturas_piso: list[float] = []
        anchos_piso: list[float] = []
        area_amb = 0.0
        for e in por_piso.get(ref, []):
            q = e.cantidades

            def g(clave: str, elemento: _Elemento = e) -> float | None:
                return medida(elemento.ref, clave)

            if e.tipo in MUROS:
                conteo["muros"] += 1
                l_muro = q.get("Length") or g("eje") or g("largo") or 0.0
                h_muro = q.get("Height") or g("altura")
                ancho = q.get("Width") or e.espesor_material or g("ancho")
                if not q:
                    sin_cantidades += 1
                cara = q.get("NetSideArea") or q.get("GrossSideArea") or (l_muro * h_muro if h_muro else None)
                largo += l_muro
                if cara:
                    area_muros += cara
                if h_muro:
                    alturas_piso.append(h_muro)
                if ancho:
                    anchos_piso.append(ancho)
                externo = e.propiedades.get("IsExternal")
                if externo is not None:
                    hay_externos = True
                if externo == "T":
                    perim_ext += l_muro
                    area_ext += cara or 0.0
                    if ancho:
                        espesores_ext.append(ancho)
                elif ancho:
                    espesores_int.append(ancho)
                materiales_muro += e.materiales
            elif e.tipo in LOSAS:
                tipo_losa = str(modelo.arg(e.ref, 8) or "")
                area = q.get("NetArea") or q.get("GrossArea") or g("area_perfil") or 0.0
                volumen = q.get("NetVolume") or q.get("GrossVolume") or g("volumen")
                espesor = q.get("Width") or q.get("Depth") or e.espesor_material or g("altura")
                if volumen is None and espesor:
                    volumen = area * espesor
                hormigon += volumen or 0.0
                if tipo_losa == "ROOF" or modelo.tipo(padre.get(e.ref)) == "IFCROOF":
                    area_cubierta += area
                    hay_cubierta_losa = True
                    conteo["cubierta"] += 1
                else:
                    area_losa += area
                    conteo["losas"] += 1
                if espesor:
                    espesores_losa.append(espesor)
            elif e.tipo in COLUMNAS or e.tipo in VIGAS:
                conteo["columnas" if e.tipo in COLUMNAS else "vigas"] += 1
                hormigon += q.get("NetVolume") or q.get("GrossVolume") or g("volumen") or 0.0
                if e.tipo in COLUMNAS:
                    medido.columnas += 1
            elif e.tipo in PUERTAS or e.tipo in VENTANAS:
                alto, ancho = _num(modelo.arg(e.ref, 8)), _num(modelo.arg(e.ref, 9))
                abertura = Abertura(round((ancho or 0.9) * f_largo, 2), round(alto * f_largo, 2) if alto else None)
                (medido.puertas if e.tipo in PUERTAS else medido.ventanas).append(abertura)
                conteo["puertas" if e.tipo in PUERTAS else "ventanas"] += 1
            elif e.tipo == "IFCSPACE":
                area = q.get("NetFloorArea") or q.get("GrossFloorArea") or g("area_perfil") or 0.0
                area_amb += area
                medido.ambientes.append(e.nombre_largo or e.nombre or f"Ambiente {len(medido.ambientes) + 1}")
                conteo["ambientes"] += 1
            elif e.tipo == "IFCROOF":
                area = q.get("NetArea") or q.get("GrossArea") or q.get("ProjectedArea")
                if area:
                    area_cubierta += area
                    hay_cubierta_losa = True
                conteo["cubierta"] += 1

        medido.largo_muros = round(largo, 2)
        medido.area_muros = round(area_muros, 2) if area_muros else None
        if alturas_piso:
            medido.altura = round(statistics.median(alturas_piso), 2)
            alturas += alturas_piso
        if anchos_piso:
            medido.espesor_muros = round(statistics.median(anchos_piso), 3)
        if hay_externos:
            medido.perimetro_exterior = round(perim_ext, 2)
            medido.area_muros_exterior = round(area_ext, 2)
        medido.volumen_hormigon = round(hormigon, 3) if hormigon else None
        medido.area_ambientes = round(area_amb, 2) if conteo["ambientes"] else None
        medido.area_planta = round(max(area_losa, area_amb * 1.12), 2)
        if not hay_externos:
            # Sin dato de muros exteriores: fachada de un rectángulo de la misma área.
            medido.perimetro_exterior = round(4 * medido.area_planta**0.5, 2)
        medido.area_cubierta = round(area_cubierta, 2) if area_cubierta else None
        medido.banos = sum(1 for a in medido.ambientes if re.search(r"\bBANO|\bWC\b|SS\.?HH", normalizar(a)))
        medido.cocinas = sum(1 for a in medido.ambientes if "COCINA" in normalizar(a) or "KITCHEN" in normalizar(a))
        pisos.append(PisoLeido(nombre, round(elevacion, 2), medido, dict(conteo)))

    if not pisos:
        raise PlanoInvalido("El modelo no tiene pisos (IfcBuildingStorey). Exporta el IFC con los niveles.")
    if sin_cantidades:
        avisos.append(
            f"{sin_cantidades} muros no traen cantidades (Qto); se midieron con su geometría. "
            "Si puedes, exporta el IFC con “cantidades base”."
        )

    formulario = Formulario()
    del_modelo: list[str] = []
    if alturas:
        formulario.altura_piso = round(statistics.median(alturas), 2)
        del_modelo.append("altura_piso")
    if espesores_ext:
        formulario.espesor_exterior = round(statistics.median(espesores_ext), 3)
        del_modelo.append("espesor_exterior")
    if espesores_int:
        formulario.espesor_interior = round(statistics.median(espesores_int), 3)
        del_modelo.append("espesor_interior")
    texto_materiales = normalizar(" ".join(materiales_muro))
    tipo_muro = None
    if "ADOBE" in texto_materiales:
        tipo_muro = "adobe"
    elif re.search(r"BLOQUE|BLOCK|CMU", texto_materiales):
        tipo_muro = "bloque_cemento"
    elif re.search(r"LADRILLO|BRICK", texto_materiales):
        tipo_muro = "ladrillo_6h"
    if tipo_muro:
        formulario.tipo_muro = tipo_muro
        del_modelo.append("tipo_muro")
    if espesores_losa:
        espesor = statistics.median(espesores_losa)
        formulario.losa = "maciza" if espesor <= 0.16 else "alivianada"
        del_modelo.append("losa")
    if hay_cubierta_losa:
        formulario.cubierta = "losa"
        del_modelo.append("cubierta")
    return ModeloLeido(pisos, formulario, del_modelo, avisos)
