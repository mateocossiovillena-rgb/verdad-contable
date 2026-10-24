"""Planos de prueba hechos por nosotros (nunca planos de clientes).

`casa_dxf()` arma una casa de 10 × 8 m en centímetros con dos plantas dibujadas una al lado de la otra:
muros exteriores de 18 cm y uno interior de 12 cm con dos líneas, dos ambientes, una puerta y dos
ventanas por planta. `casa_ifc()` es la misma idea en BIM, con cantidades del modelo.
"""

from __future__ import annotations


def _par(codigo: int, valor) -> str:
    return f"{codigo}\n{valor}\n"


def linea(capa: str, x1, y1, x2, y2) -> str:
    return _par(0, "LINE") + _par(8, capa) + _par(10, x1) + _par(20, y1) + _par(11, x2) + _par(21, y2)


def polilinea(capa: str, puntos, cerrada: bool = True) -> str:
    texto = _par(0, "LWPOLYLINE") + _par(8, capa) + _par(90, len(puntos)) + _par(70, 1 if cerrada else 0)
    for x, y in puntos:
        texto += _par(10, x) + _par(20, y)
    return texto


def insercion(capa: str, bloque: str, x, y, giro: float = 0) -> str:
    return _par(0, "INSERT") + _par(8, capa) + _par(2, bloque) + _par(10, x) + _par(20, y) + _par(50, giro)


def texto(capa: str, x, y, contenido: str) -> str:
    return _par(0, "TEXT") + _par(8, capa) + _par(10, x) + _par(20, y) + _par(40, 15) + _par(1, contenido)


def arco(capa: str, x, y, radio) -> str:
    return _par(0, "ARC") + _par(8, capa) + _par(10, x) + _par(20, y) + _par(40, radio) + _par(50, 0) + _par(51, 90)


def documento(entidades: list[str], capas: list[str], bloques: dict[str, list[str]], unidades: int | None = 5) -> str:
    salida = _par(0, "SECTION") + _par(2, "HEADER")
    if unidades is not None:
        salida += _par(9, "$INSUNITS") + _par(70, unidades)
    salida += _par(0, "ENDSEC")
    salida += _par(0, "SECTION") + _par(2, "TABLES") + _par(0, "TABLE") + _par(2, "LAYER")
    for capa in capas:
        salida += _par(0, "LAYER") + _par(2, capa) + _par(70, 0)
    salida += _par(0, "ENDTAB") + _par(0, "ENDSEC")
    salida += _par(0, "SECTION") + _par(2, "BLOCKS")
    for nombre, contenido in bloques.items():
        salida += _par(0, "BLOCK") + _par(8, "0") + _par(2, nombre) + _par(10, 0) + _par(20, 0)
        salida += "".join(contenido) + _par(0, "ENDBLK")
    salida += _par(0, "ENDSEC")
    salida += _par(0, "SECTION") + _par(2, "ENTITIES") + "".join(entidades) + _par(0, "ENDSEC") + _par(0, "EOF")
    return salida


CAPAS = ["0", "A-MURO", "PUERTAS", "VENTANAS", "AMBIENTES", "TEXTOS", "COTAS"]
BLOQUES = {
    "P-090": [linea("0", 0, 0, 90, 0), arco("0", 0, 0, 90)],
    "V120x100": [linea("0", 0, 0, 120, 0), linea("0", 0, 18, 120, 18)],
}


def planta(dx: float, nombres: tuple[str, str]) -> list[str]:
    """Una planta de 10 × 8 m (en cm) desplazada `dx` en x."""
    e = []
    # Muros exteriores: cara exterior (rectángulo de 1000 × 800) y cara interior a 18 cm.
    for x1, y1, x2, y2 in ((0, 0, 1000, 0), (1000, 0, 1000, 800), (1000, 800, 0, 800), (0, 800, 0, 0)):
        e.append(linea("A-MURO", x1 + dx, y1, x2 + dx, y2))
    for x1, y1, x2, y2 in ((18, 18, 982, 18), (982, 18, 982, 782), (982, 782, 18, 782), (18, 782, 18, 18)):
        e.append(linea("A-MURO", x1 + dx, y1, x2 + dx, y2))
    # Muro interior de 12 cm en x = 500.
    e.append(linea("A-MURO", 494 + dx, 18, 494 + dx, 782))
    e.append(linea("A-MURO", 506 + dx, 18, 506 + dx, 782))
    e.append(polilinea("AMBIENTES", [(18 + dx, 18), (494 + dx, 18), (494 + dx, 782), (18 + dx, 782)]))
    e.append(polilinea("AMBIENTES", [(506 + dx, 18), (982 + dx, 18), (982 + dx, 782), (506 + dx, 782)]))
    e.append(texto("TEXTOS", 200 + dx, 400, nombres[0]))
    e.append(texto("TEXTOS", 700 + dx, 400, nombres[1]))
    e.append(insercion("PUERTAS", "P-090", 500 + dx, 300, 90))
    e.append(insercion("VENTANAS", "V120x100", 200 + dx, 0))
    e.append(insercion("VENTANAS", "V120x100", 700 + dx, 0))
    e.append(linea("COTAS", dx, -100, 1000 + dx, -100))
    return e


def casa_dxf(unidades: int | None = 5) -> bytes:
    entidades = planta(0, ("DORMITORIO 1", "BAÑO")) + planta(1500, ("DORMITORIO 2", "COCINA"))
    return documento(entidades, CAPAS, BLOQUES, unidades).encode("utf-8")


def casa_ifc() -> bytes:
    """Dos pisos en milímetros. Planta baja con cantidades (Qto) y un muro que solo trae geometría."""
    return b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('casa.ifc','2026-10-23T00:00:00',(''),(''),'','','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCPROJECT('p',$,'Casa de prueba',$,$,$,$,$,#2);
#2=IFCUNITASSIGNMENT((#3,#4,#5));
#3=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#4=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#5=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#10=IFCBUILDINGSTOREY('s0',$,'Planta baja',$,$,$,$,$,.ELEMENT.,0.);
#11=IFCBUILDINGSTOREY('s1',$,'Planta alta',$,$,$,$,$,.ELEMENT.,2800.);
#20=IFCWALLSTANDARDCASE('w1',$,'Muro exterior',$,$,$,$,$);
#21=IFCWALLSTANDARDCASE('w2',$,'Muro interior',$,$,$,#70,$);
#22=IFCDOOR('d1',$,'Puerta',$,$,$,$,$,2100.,900.);
#23=IFCWINDOW('v1',$,'Ventana',$,$,$,$,$,1000.,1200.);
#24=IFCSLAB('l1',$,'Losa PB',$,$,$,$,$,.FLOOR.);
#25=IFCSPACE('e1',$,'101',$,$,$,$,'Ba\\X2\\00F1\\X0\\o',.ELEMENT.,.INTERNAL.,$);
#26=IFCSPACE('e2',$,'102',$,$,$,$,'Cocina',.ELEMENT.,.INTERNAL.,$);
#27=IFCSLAB('l2',$,'Cubierta',$,$,$,$,$,.ROOF.);
#28=IFCCOLUMN('c1',$,'Columna',$,$,$,$,$);
#30=IFCQUANTITYLENGTH('Length',$,$,36000.);
#31=IFCQUANTITYLENGTH('Height',$,$,2600.);
#32=IFCQUANTITYLENGTH('Width',$,$,180.);
#33=IFCQUANTITYAREA('NetSideArea',$,$,85.);
#34=IFCELEMENTQUANTITY('q1',$,'Qto_WallBaseQuantities',$,$,(#30,#31,#32,#33));
#35=IFCRELDEFINESBYPROPERTIES('r1',$,$,$,(#20),#34);
#36=IFCQUANTITYAREA('NetArea',$,$,80.);
#37=IFCQUANTITYVOLUME('NetVolume',$,$,9.6);
#38=IFCELEMENTQUANTITY('q2',$,'Qto_SlabBaseQuantities',$,$,(#36,#37));
#39=IFCRELDEFINESBYPROPERTIES('r2',$,$,$,(#24),#38);
#40=IFCQUANTITYAREA('NetFloorArea',$,$,6.5);
#41=IFCELEMENTQUANTITY('q3',$,'Qto_SpaceBaseQuantities',$,$,(#40));
#42=IFCRELDEFINESBYPROPERTIES('r3',$,$,$,(#25),#41);
#43=IFCQUANTITYAREA('NetFloorArea',$,$,12.);
#44=IFCELEMENTQUANTITY('q4',$,'Qto_SpaceBaseQuantities',$,$,(#43));
#45=IFCRELDEFINESBYPROPERTIES('r4',$,$,$,(#26),#44);
#46=IFCQUANTITYAREA('NetArea',$,$,85.);
#47=IFCELEMENTQUANTITY('q5',$,'Qto_SlabBaseQuantities',$,$,(#46));
#48=IFCRELDEFINESBYPROPERTIES('r5',$,$,$,(#27),#47);
#49=IFCQUANTITYVOLUME('NetVolume',$,$,0.25);
#50=IFCPROPERTYSINGLEVALUE('IsExternal',$,IFCBOOLEAN(.T.),$);
#51=IFCPROPERTYSET('ps1',$,'Pset_WallCommon',$,(#50));
#52=IFCRELDEFINESBYPROPERTIES('r6',$,$,$,(#20),#51);
#53=IFCPROPERTYSINGLEVALUE('IsExternal',$,IFCBOOLEAN(.F.),$);
#54=IFCPROPERTYSET('ps2',$,'Pset_WallCommon',$,(#53));
#55=IFCRELDEFINESBYPROPERTIES('r7',$,$,$,(#21),#54);
#56=IFCELEMENTQUANTITY('q6',$,'Qto_ColumnBaseQuantities',$,$,(#49));
#57=IFCRELDEFINESBYPROPERTIES('r8',$,$,$,(#28),#56);
#60=IFCMATERIAL('Ladrillo 6 huecos');
#61=IFCRELASSOCIATESMATERIAL('m1',$,$,$,(#20,#21),#60);
#70=IFCPRODUCTDEFINITIONSHAPE($,$,(#71));
#71=IFCSHAPEREPRESENTATION($,'Body','SweptSolid',(#72));
#72=IFCEXTRUDEDAREASOLID(#73,$,$,2600.);
#73=IFCRECTANGLEPROFILEDEF(.AREA.,$,$,7640.,120.);
#80=IFCRELCONTAINEDINSPATIALSTRUCTURE('c0',$,$,$,(#20,#21,#22,#23,#24,#28),#10);
#81=IFCRELCONTAINEDINSPATIALSTRUCTURE('c1',$,$,$,(#27),#11);
#82=IFCRELAGGREGATES('a0',$,$,$,#10,(#25,#26));
ENDSEC;
END-ISO-10303-21;
"""
