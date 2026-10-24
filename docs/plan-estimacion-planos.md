# Plan de implementación — Estimación desde plano CAD/BIM + formulario

Fecha: 23/10/2026 · Estado: **pasos 1 a 5 implementados** (subir DXF o IFC → cantidades confirmadas). Falta el
paso 6, generar el cronograma y la ruta crítica (C0/E0). Ver §3.1 con lo que cambió al construirlo.

## 1. Objetivo

El constructor sube su plano (CAD en DXF o, si lo tiene, BIM en IFC), completa un formulario corto y la app
le propone el cronograma completo: los **pasos del proyecto** en orden constructivo (fases y actividades
con sus predecesoras), la duración de cada uno, la **ruta crítica** (qué actividades no pueden atrasarse sin
atrasar la entrega), cuadrillas (mano de obra por día) y materiales, con su costo. Todo cae en el cronograma
que ya existe (`Fase`, `Actividad`, `Dependencia`, `RecursoActividad`) y queda editable.

**Problema que resuelve:** "no sé por dónde empezar mi cronograma ni cuánta gente necesito". Hoy todo se
carga a mano, actividad por actividad.

**Fuera de alcance de esta mejora:**
- Planos en PDF o foto leídos con IA (se puede sumar después como otra forma de entrada).
- Cálculo estructural. La estructura se estima con proporciones típicas, no se diseña.
- Precios vivos de ferreterías (versión 2, marketplace).

## 2. Principios

1. **Es una estimación para revisar.** La app nunca la presenta como cómputo definitivo; el constructor
   confirma las cantidades antes de generar el cronograma.
2. **Cada cifra muestra su origen:** *plano* (medida del archivo), *formulario* (dato del constructor),
   *proporción* (valor típico por m²) o *editada* (corregida a mano).
3. **El constructor tiene la última palabra:** cantidades, rendimientos, precios y actividades se pueden
   editar antes y después de generar.
4. **Se reutiliza lo que existe:** la generación crea fases, actividades, predecesoras y recursos con los
   mismos servicios del cronograma, y el Gantt y los costos funcionan sin cambios.
5. **Cálculos puros y con tests:** cómputos y estimación van en `calculos/`, sin base de datos, como el
   módulo de valor ganado.
6. **Licencias:** se respeta la regla del proyecto (ver §12). No se copia código de la referencia AGPL.

## 3. Flujo del usuario (asistente de 6 pasos)

Se entra desde la obra con **Cronograma → "Estimar desde plano"**, o al crear una obra nueva.

```
1 Archivo  →  2 Unidades y pisos  →  3 Capas (solo CAD)  →  4 Formulario  →  5 Cantidades  →  6 Generar
```

| Paso | Qué ve el constructor | Qué hace la app |
|---|---|---|
| 1. Archivo | Botón "Subir plano (.dxf o .ifc)" y la opción "No tengo plano, usar solo el formulario" | Valida el formato y el tamaño (máx. 25 MB) y guarda el archivo |
| 2. Unidades y pisos | "Detectamos medidas en **cm**. ¿Es correcto?" y la lista de pisos o niveles encontrados | Lee las unidades del archivo; si no las hay, las deduce por tamaño (una puerta mide ~0,9 m) |
| 3. Capas (CAD) | Lista de capas con una sugerencia: Muros · Puertas · Ventanas · Ambientes · Ignorar | Sugiere según el nombre ("MURO", "A-WALL", "PUERTA"…) y el contenido |
| 4. Formulario | Campos de §4, con valores típicos ya llenos | Completa lo que el plano no dice |
| 5. Cantidades | Tabla editable por rubro con su origen y el plano dibujado con lo detectado resaltado | Calcula los cómputos (§6) |
| 6. Generar | Resumen: N fases, N actividades, duración total, fecha de entrega, costo, cuadrillas, la ruta crítica en rojo sobre el Gantt y avisos (ver §8.3). Elegir "Reemplazar cronograma" o "Agregar al actual" | Calcula pasos y ruta crítica (§8) y crea el cronograma |

**Vista del plano (paso 5):** dibujo en SVG del plano leído. Al tocar una fila de la tabla (por ejemplo
"Muros 1er piso: 86,4 m") se resaltan esas líneas. Así el constructor ve de un vistazo si la app entendió
bien.

El asistente guarda el avance en cada paso (estado de la estimación en el servidor): se puede cerrar y
retomar.

### 3.1 Cómo quedó implementado (23/10/2026)

- **El formulario es solo para CAD.** Un IFC trae alturas, espesores y materiales: el modelo responde el
  formulario y lo que no trae se completa con valores típicos (origen *proporción*). Flujos:
  - CAD (`.dxf`): Capas y unidades → Plantas → Datos de la obra → Cantidades → Confirmada.
  - BIM (`.ifc`): Pisos → Cantidades → Confirmada.
- **Orden CAD:** primero capas y unidades (sin saber cuáles son muros no se pueden separar las plantas),
  después las plantas: la app separa las zonas dibujadas una al lado de la otra y el constructor marca cuáles
  son plantas, les pone nombre y cuántas veces se repiten.
- **Lectores propios** de DXF ASCII e IFC (STEP), sin librerías externas, para no depender de licencias
  (`calculos/plano_dxf.py`, `calculos/plano_ifc.py`). DWG, Revit, SketchUp y PDF se rechazan con un mensaje
  que dice cómo exportar.
- **Vanos:** se asume que en el plano los muros vienen cortados en puertas y ventanas; al área de muro se le
  suman dinteles y antepechos (alto típico de puerta 2,10 m y de ventana 1,20 m si el nombre del bloque no lo
  dice, ej. `V120x100`).
- **Datos:** una tabla `estimacion` con columnas JSON (lectura, capas, plantas, formulario, medición,
  ediciones) en vez de varias tablas; las cantidades se calculan al leer y solo se guardan las correcciones a
  mano, por clave (`rubro` o `rubro:piso`). `mapeo_capa` recuerda el rol de cada capa por dueño.
- **Planos confidenciales:** se guardan con nombre aleatorio en `backend/planos/` (fuera de git), nunca se
  sirven de vuelta y se borran al borrar la estimación.
- API en `rutas/estimaciones.py`; pantalla `paginas/EstimarObra.tsx` con `VistaPlano` y `TablaCantidades`.
  Las cuadrillas y la fecha de inicio se preguntarán en el paso 6 (generar), igual para CAD y BIM.

## 4. Formulario complementario

Los campos aparecen ya llenos con valores típicos; el constructor solo cambia lo que no corresponde.
Con BIM se ocultan los campos que el modelo ya trae.

| Grupo | Campo | Ejemplo |
|---|---|---|
| Obra | Tipo de obra | Vivienda unifamiliar · Departamentos · Local comercial |
| | Número de pisos (si el plano no lo dice) | 2 |
| | Altura de piso a techo | 2,60 m |
| Muros | Tipo | Ladrillo de 6 huecos · Bloque de cemento · Adobe |
| | Espesor exterior / interior | 18 cm / 12 cm |
| Estructura | Sistema | Pórticos de H°A° (columnas y vigas) |
| | Tipo de losa | Alivianada con plastoform · Maciza · Viguetas pretensadas |
| | Cubierta | Losa · Calamina sobre madera · Teja |
| | Fundación | Zapatas aisladas · Cimiento corrido de H°C° |
| Acabados | Nivel | Económico · Medio · Alto |
| | Piso | Cerámica · Porcelanato · Cemento pulido |
| Instalaciones | Baños / cocinas (si el plano no los marca) | 2 / 1 |
| Ejecución | Cuadrillas disponibles por oficio | Albañilería 2 · Fierreros 1 · Electricista 1 |
| | Fecha de inicio | Hoy |
| | Fecha de entrega deseada (opcional) | 30/06/2027 |
| | Días de trabajo por semana | 6 |
| | Subcontratos (no los hace la cuadrilla propia) | Instalación eléctrica, carpintería |

La fecha de entrega deseada no cambia el cálculo: sirve para avisar si la ruta crítica no llega y cuántas
cuadrillas harían falta (§8.3). Lo subcontratado genera la actividad sin cuadrilla propia y sin competir
por gente con las demás.

## 5. Lectura de archivos

### 5.1 DXF (fase E1)
- **Librería:** lector de DXF con licencia permisiva (por ejemplo `ezdxf`, MIT). Confirmar la licencia
  antes de agregarla (§12).
- **Unidades:** variable `$INSUNITS` del encabezado; si falta, se deduce y se pregunta en el paso 2.
- **Capas:** se listan todas con la cantidad de entidades por tipo y se sugiere un rol según el nombre.
  El mapeo elegido se guarda por dueño, para que el próximo plano del mismo arquitecto salga solo.
- **Muros:**
  - Si son polilíneas cerradas o sombreados (HATCH): perímetro y área → largo del eje del muro.
  - Si son pares de líneas paralelas: se agrupan las paralelas a la distancia del espesor y se toma el eje.
  - Se descuentan los vanos donde hay bloques de puerta o ventana.
- **Ambientes:** polilíneas cerradas en la capa de ambientes, o regiones que encierran los muros; los
  textos dentro de cada región dan su nombre ("Dormitorio 1", "Baño").
- **Puertas y ventanas:** bloques (INSERT) en sus capas; el ancho sale de la geometría del bloque o del
  nombre ("P-090", "V120x100").
- **Pisos:** por capa o prefijo ("PB-", "P1-") o por regiones separadas del dibujo; el constructor
  confirma en el paso 2.
- **Casos difíciles que se avisan y no rompen el flujo:**
  - Bloques explotados.
  - Todo dibujado en una sola capa.
  - Escalas mezcladas.
  - Archivos con varias láminas.

  En esos casos se muestra "No pudimos leer X, ingrésalo a mano" y la cantidad pasa a origen *formulario*.

### 5.2 IFC / BIM (fase E2)
- **Librería:** lector de IFC (por ejemplo IfcOpenShell, LGPL). Confirmar las condiciones de uso en el
  servidor (§12).
- **Entidades:** `IfcWall`, `IfcSlab`, `IfcColumn`, `IfcBeam`, `IfcDoor`, `IfcWindow`, `IfcSpace`,
  `IfcStair`, `IfcRoof` y `IfcBuildingStorey` (pisos).
- **Cantidades:** se usan los conjuntos de cantidades del modelo (`Qto_WallBaseQuantities`,
  `Qto_SlabBaseQuantities`…) cuando existen; si no, se calculan con la geometría.
- **Materiales:** si el modelo los trae, se ocultan esas preguntas del formulario.
- **Revit (.rvt):** no se lee directo; se pide exportar a IFC (Revit, ArchiCAD y otros lo hacen).

### 5.3 DWG (fase E4, solo si hace falta)
Pedir "Guardar como DXF" resuelve casi todos los casos. Si los pilotos muestran que es una molestia real,
se evalúa un convertidor, revisando antes su licencia (§12).

## 6. Cómputos (cantidades por rubro)

Módulo puro `calculos/computos.py`: recibe la geometría ya leída (largos, áreas, conteos por piso) y el
formulario, y devuelve cantidades con su origen.

| Rubro | Unidad | Cómo se calcula | Origen |
|---|---|---|---|
| Excavación de fundaciones | m³ | Largo de muros × sección típica según la fundación | proporción |
| Cimientos y sobrecimientos | m³ | Largo de muros de planta baja × sección | plano + proporción |
| Columnas, vigas, losa (hormigón) | m³ | Área de losa × espesor equivalente según el tipo; columnas y vigas por m² | proporción (BIM: plano) |
| Fierro | kg | kg por m³ de hormigón según el elemento | proporción |
| Muros de ladrillo/bloque | m² | Largo del eje × altura − vanos | plano + formulario |
| Revoque interior / exterior | m² | m² de muro × caras (interior 2, exterior 1 + 1 exterior) | plano |
| Contrapiso y piso | m² | Suma de áreas de ambientes | plano |
| Cielo raso | m² | Área de ambientes | plano |
| Cubierta | m² | Área de planta del último nivel × factor de pendiente | plano + formulario |
| Puertas / ventanas | pza / m² | Conteo y medidas de bloques | plano |
| Pintura | m² | Revoques + cielo raso | plano |
| Instalación eléctrica | punto | Bloques, o puntos típicos por ambiente | plano o proporción |
| Instalación sanitaria | punto | Por baño y cocina | formulario |

## 7. Catálogo de rendimientos y consumos

Es el corazón de la estimación. Hay un catálogo **base** (cargado por nosotros) y cada dueño puede
**personalizar** sus valores sin tocar el base.

**Por rubro se guarda:**
- **Actividad que genera** y **fase** (Obra gruesa, Instalaciones, Acabados…).
- **Cuadrilla tipo:** por ejemplo 1 albañil + 1 ayudante, con el jornal de cada cargo.
- **Rendimiento:** unidades por día por cuadrilla (por ejemplo, m² de muro por día).
- **Consumos de material por unidad:** por ejemplo, por m² de muro, ladrillos, cemento y arena, con
  unidad y precio de referencia.
- **Predecesoras tipo:** por ejemplo, revoque después de muros; piso después de contrapiso.
- **Desfase tipo:** por ejemplo, días de fraguado de la losa.

**Ejemplo de forma (los valores son ilustrativos y se deben calibrar con fuentes locales y con los pilotos):**

| Rubro | Cuadrilla | Rendimiento | Consumos por unidad |
|---|---|---|---|
| Muro de ladrillo 6H (m²) | 1 albañil + 1 ayudante | 10 m²/día | ladrillos, cemento (kg), arena (m³) |
| Revoque interior (m²) | 1 albañil + 1 ayudante | 14 m²/día | cemento, cal, arena |
| Contrapiso (m²) | 1 albañil + 2 ayudantes | 25 m²/día | cemento, arena, grava |

**Fuentes para el catálogo base:** rendimientos y consumos de referencia del medio boliviano, validados
con 2 o 3 constructores antes del piloto. Cada valor guarda su fuente.

## 8. Generación del cronograma

Módulo puro `calculos/estimacion.py`: entra cantidades + catálogo + formulario y sale una propuesta de
fases y actividades. Después un servicio la guarda con la lógica actual del cronograma.

1. **Actividades:** una por rubro y por piso cuando importa el orden (muros PB → losa PB → muros P1…).
2. **Duración:** `ceil(cantidad / (rendimiento × cuadrillas asignadas))`, mínimo 1 día. Las cuadrillas
   salen del formulario (§4) por oficio.
3. **Mano de obra:** `RecursoActividad` de tipo `mano_obra`, con `por_dia = true`, cantidad = personas
   de la cuadrilla × cuadrillas y precio = jornal del catálogo.
4. **Materiales:** `RecursoActividad` de tipo `material`, con cantidad = cantidad del rubro × consumo y
   precio de referencia del catálogo.
5. **Predecesoras:** las del catálogo, más las de orden por piso; los desfases van en
   `dependencia.desfase_dias`.
6. **Fechas:** las calcula `calculos/cronograma.py` como hoy, desde la fecha de inicio del formulario.
7. **Modo de guardado:**
   - "Reemplazar": borra el cronograma actual, previa confirmación clara.
   - "Agregar": crea fases nuevas con el sufijo "(estimado)".
8. **Partidas (EVM):** opcional en esta mejora. Se completa cuando se una actividades con partidas (plan
   MVP §7, "Unir actividades con partidas"); entonces cada fase estimada podrá crear su partida con
   presupuesto = costo estimado.

### 8.1 Pasos del proyecto (secuencia constructiva tipo)

El catálogo trae una secuencia tipo por tipo de obra. La estimación solo incluye los pasos con cantidad
mayor que cero (sin cubierta de teja no hay "Cubierta de teja") y repite por piso los que dependen del piso.
Ejemplo para una vivienda de 2 pisos con pórticos de H°A° (orden y desfases ilustrativos, a calibrar con
los pilotos):

| # | Fase | Paso (actividad) | Predecesoras tipo | Desfase |
|---|---|---|---|---|
| 1 | Preliminares | Limpieza, replanteo e instalación de faenas | — | |
| 2 | Movimiento de tierras | Excavación de fundaciones | 1 | |
| 3 | Fundaciones | Zapatas y cimiento corrido | 2 | |
| 4 | Fundaciones | Sobrecimiento | 3 | |
| 5 | Obra gruesa PB | Columnas PB | 3 | |
| 6 | Obra gruesa PB | Muros PB | 4, 5 | |
| 7 | Obra gruesa PB | Vigas y losa PB | 5 | |
| 8 | Obra gruesa P1 | Columnas P1 | 7 | 7 días de fraguado |
| 9 | Obra gruesa P1 | Muros P1 | 8 | |
| 10 | Obra gruesa P1 | Vigas y losa o cubierta P1 | 8 | |
| 11 | Instalaciones | Eléctrica y sanitaria empotrada (por piso) | muros del piso | |
| 12 | Acabados | Revoque interior y exterior (por piso) | 11 del piso; exterior: 10 | |
| 13 | Acabados | Contrapiso y piso (por piso) | 12 del piso | |
| 14 | Acabados | Cielo raso | losa del piso, 11 | |
| 15 | Acabados | Carpintería: puertas y ventanas | 12 | |
| 16 | Acabados | Pintura | 12, 14 | |
| 17 | Entrega | Artefactos, limpieza final y entrega | 13, 15, 16 | |

Cada predecesora guarda su **origen**: *técnica* (del catálogo: no se puede revocar sin muro) o *por
cuadrilla* (agregada en §8.2 porque falta gente). Así el constructor sabe cuáles puede romper sumando gente.

### 8.2 Cuadrillas compartidas

Si dos pasos del mismo oficio se cruzan en el tiempo y no alcanzan las cuadrillas del formulario, el
generador no los deja en paralelo: pone el de menor holgura primero y agrega una predecesora *por
cuadrilla*. Es una nivelación simple y explicable, no una optimización. Los subcontratos no compiten.

### 8.3 Ruta crítica

Se calcula con el mismo módulo del cronograma (`calculos/cronograma.py`) ampliado según el plan MVP §7:

1. **Paso hacia adelante** (ya existe): inicio y fin tempranos desde la fecha de inicio.
2. **Paso hacia atrás** (nuevo): desde el fin de la obra, inicio y fin tardíos sobre el mismo orden
   topológico.
3. **Holgura total** = inicio tardío − inicio temprano. Holgura 0 = **ruta crítica**.
4. **Tipos de enlace y desfases:** FC, más CC con desfase (por ejemplo "revoque exterior empieza 3 días
   después de que empiezan los muros"), usando `dependencia.tipo` y `dependencia.desfase_dias`.
5. **Calendario:** la duración se cuenta en días de trabajo según "días por semana" del formulario
   (feriados de Bolivia, en una segunda etapa).

En el paso 6 el constructor ve:
- El Gantt con la ruta crítica en rojo y la holgura de cada paso ("puede atrasarse 4 días sin mover la
  entrega").
- **Entrega estimada** frente a la deseada: "Llegas el 12/07/2027, 12 días después de lo que querías".
- **Qué cuadrilla acorta la obra:** se recalcula sumando una cuadrilla de cada oficio de la ruta crítica
  y se muestra la mejor opción: "Con 1 cuadrilla más de albañilería terminas 18 días antes (+Bs 9.400 en
  jornales)". Es un cálculo puro, sin guardar, que se repite por oficio.

Después de generar, la ruta crítica se recalcula sola en cada cambio del cronograma, como hoy las fechas.

## 9. Modelo de datos (nuevo, propio)

| Tabla | Campos principales | Para qué |
|---|---|---|
| `estimacion` | obra_id, creado_por, estado (archivo, unidades, capas, formulario, cantidades, generada), tipo_archivo (dxf, ifc, ninguno), archivo, unidades, formulario (JSON), creado_en | Un asistente en curso o terminado por obra |
| `estimacion_capa` | estimacion_id, capa, rol (muros, puertas, ventanas, ambientes, ignorar) | Mapeo de capas del paso 3 |
| `mapeo_capa_dueno` | dueno_id, nombre_capa, rol | Recordar el mapeo para el próximo plano |
| `cantidad_estimada` | estimacion_id, rubro, piso, cantidad, unidad, origen (plano, formulario, proporcion, editada), cantidad_original | Tabla del paso 5; se guarda la original para medir cuánto se corrigió |
| `rubro` | codigo, nombre, unidad, fase_sugerida, actividad_nombre | Catálogo base |
| `rendimiento` | rubro_id, dueno_id (null = base), cuadrilla (JSON de cargos y jornales), unidades_por_dia, fuente | Base y personalizados |
| `consumo` | rubro_id, dueno_id (null = base), material, unidad, cantidad_por_unidad, precio_referencia | Materiales por unidad de rubro |
| `rubro_predecesora` | rubro_id, predecesor_id, desfase_dias | Orden tipo de las actividades |
| `secuencia_tipo` | tipo_obra, rubro_id, orden, por_piso | Pasos del proyecto por tipo de obra (§8.1) |
| `actividad` (cambio) | + `estimacion_id` (nullable), + `rubro_id` (nullable), + `holgura_dias` (calculada y guardada como las fechas) | Saber qué actividades salieron de una estimación y cuáles son críticas |
| `dependencia` (cambio) | + `origen` (tecnica, cuadrilla, manual); `tipo` admite CC además de FC | Explicar por qué existe cada predecesora |

Los archivos subidos se guardan como las fotos (carpeta del servidor, nombre aleatorio) y nunca se sirven
públicos.

## 10. API (borrador)

| Método y ruta | Uso |
|---|---|
| `POST /api/obras/{id}/estimaciones` | Crear estimación (con o sin archivo) |
| `GET /api/estimaciones/{id}` | Estado y datos del asistente |
| `PUT /api/estimaciones/{id}/unidades` | Confirmar unidades y pisos |
| `GET /api/estimaciones/{id}/capas` · `PUT …/capas` | Ver y guardar el mapeo de capas |
| `GET /api/estimaciones/{id}/geometria` | Geometría simplificada para dibujar el plano en SVG |
| `PUT /api/estimaciones/{id}/formulario` | Guardar el formulario |
| `GET /api/estimaciones/{id}/cantidades` · `PUT …/cantidades` | Ver y editar cantidades |
| `GET /api/estimaciones/{id}/propuesta` | Vista previa: pasos, predecesoras, fechas, holguras, ruta crítica, entrega estimada, sugerencia de cuadrillas y costo, sin guardar |
| `POST /api/estimaciones/{id}/generar` | Crear el cronograma (`modo`: reemplazar · agregar) |
| `GET/PUT /api/catalogo/rendimientos` | Ver y personalizar los rendimientos del dueño |

Todo solo para el dueño (`solo_dueno`); el encargado no ve estimaciones.

## 11. Frontend

- **Página `EstimarObra`** (asistente de 6 pasos) con una barra de progreso arriba, un botón principal
  por paso y "Atrás" secundario.
- **Componente `VistaPlano`** (SVG): dibuja la geometría y resalta la selección. Con zoom y arrastre
  simples, que se usen bien en el celular.
- **Componente `TablaCantidades`:** rubro, piso, cantidad, unidad y píldora de origen (plano, formulario,
  proporción, editada); montos y cantidades con `tabular-nums` y alineados a la derecha.
- **Gantt (cambio):** barras de la ruta crítica en rojo, holgura como tramo claro después de la barra y un
  interruptor "Solo ruta crítica". Lo usa tanto el paso 6 como la pestaña Cronograma.
- **Página `Catalogo`** (desde Cuenta): rendimientos y consumos del dueño, con "Volver al valor base".
- Diseño según `guia-diseno-frontend.md`. El paso 3 de capas es el más técnico: textos simples y
  sugerencias ya marcadas.

## 12. Licencias (regla obligatoria del proyecto)

| Necesidad | Opción candidata | Licencia | Decisión |
|---|---|---|---|
| Leer DXF | ezdxf | MIT | Usar, previa confirmación |
| Leer IFC | IfcOpenShell | LGPL | Revisar las condiciones de uso en el servidor antes de adoptarla |
| Convertir DWG | LibreDWG / ODA File Converter | GPL / propietaria gratuita | **No adoptar sin revisión**: GPL puede obligar a liberar código; ODA tiene términos propios |
| Catálogo de rendimientos | Datos propios y fuentes públicas citadas | — | No copiar tablas con derechos de autor sin permiso |

Nada de esto sale de `../referencias/OpenConstructionERP`. Se puede leer para entender ideas, sin copiar
código, nombres internos, esquemas ni textos.

## 13. Fases de implementación

| Fase | Entregable | Tamaño | Criterio de aceptación |
|---|---|---|---|
| **C0. Ruta crítica** (requisito) | Paso hacia atrás, holguras, enlaces CC, días de trabajo por semana y Gantt en rojo (plan MVP §7) sobre el cronograma actual | S–M | En el cronograma demo, las actividades críticas salen con holgura 0 y coinciden con un cálculo a mano |
| **E0. Catálogo + formulario sin plano** | Tablas `rubro`, `rendimiento`, `consumo`, `rubro_predecesora`, `secuencia_tipo` con el catálogo base; `calculos/estimacion.py` con tests (pasos, cuadrillas compartidas, sugerencia de cuadrillas); asistente con los pasos 4, 5 y 6 usando proporciones por m² | M | Una vivienda de 120 m² y 2 pisos genera sus pasos, su ruta crítica y un cronograma editable en menos de 3 minutos |
| **E1. DXF** | Lector DXF, pasos 1, 2 y 3, `VistaPlano`, cómputos desde geometría, mapeo de capas recordado por dueño | L | Con 5 planos reales de pilotos: muros, pisos y revoques dentro del ±10 % del cómputo manual de un técnico |
| **E2. IFC** | Lector IFC y formulario reducido | M | Con 2 modelos de prueba, las cantidades coinciden con las del software BIM de origen |
| **E3. Rendimientos reales** | Con los avances y gastos registrados, comparar los días reales con los estimados por rubro y sugerir ajustes al catálogo del dueño | M | Tras una obra terminada, la app muestra "tus muros rinden X m²/día, el catálogo dice Y" |
| **E4. DWG** (opcional) | Conversión DWG → DXF | S–M | Solo si los pilotos lo piden y la licencia está aprobada |

**Orden recomendado:** C0 → E0 → E1 → piloto → E3 → E2 → E4. C0 sirve también a quien carga el
cronograma a mano; E0 ya da valor sin plano y deja listo el catálogo del que dependen las demás fases.

## 14. Pruebas

- **Unitarias** (`backend/tests/`):
  - Cómputos con geometrías sintéticas (un rectángulo de muros, con puertas y ventanas).
  - Estimación con el catálogo de prueba.
  - Cálculo de duraciones y predecesoras.
  - Ruta crítica: paso hacia atrás, holguras, enlaces CC con desfase, cronogramas con dos caminos
    paralelos (uno crítico y otro con holgura).
  - Cuadrillas compartidas: dos pasos del mismo oficio con una sola cuadrilla quedan en serie.
  - Mapeo de capas por nombre.
- **Planos de prueba:** carpeta `backend/tests/planos/` con DXF pequeños hechos por nosotros (muro
  simple, casa de 2 ambientes, bloques explotados, unidades en mm). Nunca planos de clientes en el
  repositorio.
- **Validación con pilotos:** 5 planos reales (con permiso) comparados contra el cómputo manual de un
  técnico; se registra la diferencia por rubro.
- **Métrica de calidad en producción:** diferencia entre `cantidad_original` y la cantidad editada por el
  constructor. Si un rubro se corrige mucho, se revisa su lectura o su proporción.

## 15. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Planos CAD desordenados (capas, bloques explotados, escalas) | Paso de capas con sugerencias, vista del plano y carga manual como respaldo; se recuerda el mapeo por dueño |
| Rendimientos base poco realistas para la zona | Calibrar con constructores antes del piloto; personalización por dueño; aprendizaje E3 |
| El constructor toma la estimación como definitiva | Textos "estimación para revisar", origen visible en cada cifra y confirmación obligatoria en el paso 5 |
| Archivos grandes o pesados de procesar | Límite de 25 MB, procesamiento en segundo plano con estado "Leyendo plano…", geometría simplificada para el SVG |
| Licencias de librerías | Tabla §12 y revisión antes de cada dependencia nueva |
| Datos del cliente (planos son confidenciales) | Archivos privados por dueño, nunca públicos; opción de borrar el plano después de generar |

## 16. Decisiones pendientes

1. Fuente del catálogo base de rendimientos y consumos para Bolivia (y si conviene uno por región:
   altiplano, valles, llanos).
2. Si E0 se lanza antes que el resto, como "Estimar sin plano" dentro de Nueva obra.
3. Si el procesamiento de archivos pesados necesita una cola de tareas, o alcanza con hacerlo dentro de la
   misma petición con límite de tamaño.
4. Si se guardan los planos después de generar o se borran por defecto.
5. Si la secuencia tipo (§8.1) se valida por región o alcanza una sola para empezar.
6. Cuándo sumar feriados de Bolivia al calendario de trabajo.
