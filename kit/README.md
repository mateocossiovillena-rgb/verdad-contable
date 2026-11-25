# Kit TCM para pymes constructoras

Control de costos de obra con el marco Total Cost Management (AACE International), sobre la app
**Verdad Contable** y plantillas Excel.

| Archivo | Para qué sirve |
|---|---|
| `guia-implementacion.md` | **Empezar aquí.** Qué cubre el kit, cómo ponerlo en marcha y la rutina de control (1–2 páginas) |
| `plantillas/plantilla-kit-tcm.xlsx` | Plantilla vacía del estimado: datos de obra, clasificación, actividades, APU-insumos y base del estimado. Se importa en la app |
| `plantillas/riesgos-y-cambios.xlsx` | Registro de riesgos y bitácora de cambios vacíos (también se descargan desde cada obra, con lo ya cargado) |
| `ejemplo/vivienda-120m2.xlsx` | La plantilla llena con una vivienda de 120 m² en Santa Cruz (34 actividades en 7 fases), lista para importar |
| `ejemplo/estimado-vivienda-en-ejecucion.xlsx` | Lo que exporta la app de esa vivienda con 9 semanas de ejecución: clase, APU, base del estimado, línea base, PV semanal, valor ganado con pronósticos, riesgos y cambios |
| `prueba-de-uso.md` | Guion de la prueba de uso con una pyme: perfil, 5 tareas con metas de tiempo, tipos de error, SUS y preguntas abiertas |
| `prueba/hoja-de-registro.xlsx` | Hoja para llenar durante la prueba: tiempos, errores por tipo y SUS de hasta 3 participantes, con un resumen automático |

Los archivos `.xlsx` se generan desde el código para que siempre coincidan con la app:
`cd backend && python -m app.tcm.kit`. El ejemplo también se puede cargar en la cuenta demo local con
`python -m app.tcm.ejemplo`.
