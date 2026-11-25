# Guía de implementación — Kit TCM para pymes constructoras

**Qué es.** Un kit para que una pyme constructora controle el costo de sus obras con el marco *Total Cost
Management* (TCM) de AACE International, sin software caro ni un departamento de costos. Son tres piezas:
la app web **Verdad Contable** (funciona en el celular), **plantillas Excel** para cargar y descargar datos,
y esta guía.

**Para quién.** Pymes que hacen viviendas u obras menores, con un responsable de presupuestos (dueño,
ingeniero o técnico) y un encargado en obra. Se necesita: una computadora con Excel, un celular con
internet en obra y unas 2 horas para la puesta en marcha.

## Qué cubre el kit y de qué práctica AACE sale

| Paso | Práctica recomendada AACE | Dónde está en el kit |
|---|---|---|
| Clasificar el estimado (clase 5 a 1, rango de exactitud) | 17R-97 / 56R-08 | Hoja *Clasificación* · pestaña **Estimado** |
| Estimar con APU por actividad (WBS) | 17R-97 (metodología por clase) | Hojas *Actividades* y *APU-Insumos* · pestaña **Estimado** |
| Documentar la base del estimado | 34R-05 | Hoja *Base del estimado* · pestaña **Base** |
| Aprobar la línea base y su curva S | Control de proyecto (TCM) | Pestaña **Línea base** |
| Medir el valor ganado (PV, EV, AC, CPI, SPI) | 82R-13 | Pestaña **Resumen** y pantalla **Partidas** |
| Pronosticar el costo final (EAC, ETC, VAC) | 80R-13 | Pestaña **Resumen** |
| Registrar riesgos y estimar la contingencia | 44R-08 | Pestaña **Riesgos** · libro *riesgos-y-cambios.xlsx* |
| Controlar los cambios | Control de cambios (TCM) | Pestaña **Cambios** · libro *riesgos-y-cambios.xlsx* |

## Puesta en marcha (una vez por obra)

1. **Crear la cuenta** del dueño en la app y agregar al encargado (Cuenta → Equipo).
2. **Llenar la plantilla** `plantillas/plantilla-kit-tcm.xlsx` (solo celdas amarillas). Usar
   `ejemplo/vivienda-120m2.xlsx` como modelo:
   - *Datos de obra*: nombre, fecha de inicio y los % del APU de la empresa (cargas sociales, IVA de la mano
     de obra, herramientas, gastos generales, utilidad, IT).
   - *Clasificación*: qué entregables existen (no / parcial / completo).
   - *Actividades*: código único, fase, unidad, cómputo, duración y predecesoras. Opcional: la regla de medición
     del avance (% físico, 0/100 o 50/50).
   - *APU-Insumos*: materiales, mano de obra y equipo **por unidad** de cada actividad.
   - *Base del estimado*: propósito, alcance, supuestos, exclusiones, fuentes y fecha de precios.
3. **Importar** en Obras → *Importar desde Excel*. La vista previa muestra los errores con su hoja, fila y
   columna. No se graba nada hasta confirmar.
4. **Revisar** en la pestaña Estimado la clase, el rango probable y el APU de cada actividad.
5. **Registrar los riesgos** (pestaña Riesgos) y usar la suma de P × I como contingencia si corresponde.
6. **Aprobar la línea base** (pestaña Línea base) cuando el cliente acepta el presupuesto. Desde ese momento
   el valor ganado mide contra esa foto, aunque después se edite el plan.

## Rutina de control

| Cuándo | Quién | Qué hace |
|---|---|---|
| Cada día | Encargado | Registra los gastos (con foto del comprobante) y cierra el día desde el celular |
| Cada semana | Encargado o residente | Registra el % de avance de las actividades en curso |
| Cada semana | Dueño | Revisa el Resumen: CPI, SPI, curva S y los tres EAC. Si CPI o SPI bajan de 0,90, busca la causa en Partidas |
| Cada mes | Dueño y residente | Revisa el registro de riesgos: cierra los que pasaron y agrega los nuevos |
| Cuando alguien pide un cambio | Dueño | Lo registra en Cambios. Si se aprueba, se crea la versión siguiente de la línea base |
| Al cierre de mes o de obra | Dueño | Exporta el estimado a Excel (incluye valor ganado, riesgos y cambios) para el archivo o el cliente |

**Cómo leer los pronósticos.**
- **EAC = AC + (BAC − EV):** el desvío fue algo puntual que no se va a repetir.
- **EAC = BAC / CPI:** se sigue gastando con la misma eficiencia.
- **EAC = AC + (BAC − EV) / (CPI × SPI):** el atraso también encarece lo que falta.

Si los tres EAC superan el BAC, el sobrecosto es probable: hay que actuar ya (renegociar, cambiar el método)
o registrar un cambio.

## Reglas que conviene respetar

- **La línea base no se edita.** Después de la v1, solo un cambio aprobado crea una versión nueva, y la
  versión guarda qué cambio la originó.
- **Un riesgo que ya no aplica se cierra, no se borra.** Lo mismo con los cambios resueltos: así queda el
  historial para la próxima obra.
- **La regla 0/100 o 50/50** sirve para actividades cortas o difíciles de medir (artefactos, ventanas). Para el
  resto, conviene el % físico.

## Simplificaciones del kit (decirlas al presentar)

- El **% de definición** se calcula con pesos por entregable. Las normas usan una matriz de madurez
  cualitativa. Los valores de la tabla de clases se editan en `backend/app/tcm/clases_estimado.toml`.
- El **BAC es el precio de venta del APU** (incluye utilidad e impuestos). Por eso el CPI se ve más
  favorable que si se midiera solo contra el costo.
- El **PV** se reparte en forma lineal por días calendario dentro de cada actividad.
- La **contingencia** es la suma de los valores esperados P × I, no una simulación de Monte Carlo.
- Los **precios del ejemplo** son ilustrativos (Santa Cruz, noviembre de 2026).

## Contenido de la carpeta

Ver `README.md`. Para regenerar los Excel desde el código: `python -m app.tcm.kit` (en `backend/`).
