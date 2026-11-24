# Prueba de uso del Kit TCM con una pyme constructora

> **Qué mide:** si una persona de una pyme puede usar el kit sola, cuánto tarda, en qué se equivoca y qué
> le parece (**usabilidad**). **No mide impacto**: no dice si la empresa controla mejor sus costos ni si
> gana más dinero. Eso pediría un seguimiento de varios meses y una comparación que esta prueba no hace.

## 1. Datos de la prueba

| Campo | Valor |
|---|---|
| Pyme | _(nombre)_ |
| Rubro y tamaño | _(ej. viviendas unifamiliares, 8 trabajadores, 3–5 obras al año)_ |
| Ciudad | _(ej. Santa Cruz de la Sierra)_ |
| Fecha y lugar | _(oficina de la pyme)_ |
| Moderador | _(estudiante)_ |
| Observador / tomador de tiempos | _(compañero)_ |
| Equipo | Laptop con Excel y navegador; Verdad Contable en local o en la web; cronómetro |

## 2. Perfil del participante

- Trabaja en la pyme y hoy prepara presupuestos o controla gastos de obra (dueño, ingeniero residente,
  técnico de presupuestos o administrador).
- Usa Excel en su trabajo (como mínimo, sabe llenar una planilla y guardar el archivo).
- **No** vio el kit antes de la prueba y no participó en su desarrollo.
- Se anota: cargo, años de experiencia en obra, cómo presupuesta hoy (Excel propio, programa, a mano) y si
  conoce valor ganado (sí / de oído / no).

## 3. Preparación (moderador, antes de empezar)

1. Cuenta del participante creada y vacía (o la cuenta demo sin la obra de ejemplo).
2. Archivo `kit/ejemplo/vivienda-120m2.xlsx` copiado en el escritorio con el nombre `obra-pyme.xlsx`
   (es la obra que el participante va a "cargar"; así todos parten de los mismos datos).
3. Hoja de registro impresa (sección 6) y cronómetro en cero.
4. Leer el guion de bienvenida: _"Vamos a probar el sistema, no a ti. Si algo no se entiende, es culpa
   del sistema. Piensa en voz alta. Solo te ayudaré si me lo pides o si te quedas trabado más de 2 minutos."_

## 4. Tareas

El tiempo corre desde que se lee la tarea hasta que el participante dice "listo". Si pasa el **tiempo
máximo** (el doble de la meta) se detiene, se anota "no completó" y se pasa a la siguiente.

| # | Tarea (se lee tal cual) | Se completa cuando… | Meta | Máx. |
|---|---|---|---|---|
| 1 | "Carga la obra desde el archivo `obra-pyme.xlsx` del escritorio." | La obra aparece en Mis obras | 4 min | 8 min |
| 2 | "Esta obra ya tiene planos estructurales completos. Actualiza la clasificación y dime qué clase de estimado es y entre qué montos puede terminar." | Dice la clase y el rango (mínimo–máximo) correctos | 3 min | 6 min |
| 3 | "Aprueba la línea base del presupuesto y dime cuánto dinero debería estar ejecutado al final de la semana 8." | Dice el PV acumulado de la semana 8 (tabla o curva S) | 3 min | 6 min |
| 4 | "Registra que la excavación de cimientos está al 100 % y que se gastaron Bs 2.000 en ella. Luego dime si la obra va bien de costo y cuánto costará al final." | Lee CPI, SPI y EAC y los interpreta | 5 min | 10 min |
| 5 | "Registra el riesgo 'suba del precio del fierro' y un cambio pedido por el cliente: 'agregar un baño de visitas'." | Ambos quedan guardados | 5 min | 10 min |

> Tareas 4 y 5: el EVM con pronósticos (Fase 2) y los registros de riesgos y cambios (Fases 3 y 4) se terminan
> después de la entrega del 25/11. La prueba se hace cuando estén listas; si se adelanta, se aplican solo las
> tareas 1 a 3.

Variante con plantilla vacía (si hay tiempo, al final): "Descarga la plantilla vacía y carga una actividad
de tu última obra con 3 insumos". Sirve para ver si la plantilla se entiende sin el ejemplo.

## 5. Tipos de error (para la hoja de registro)

| Código | Tipo | Ejemplo |
|---|---|---|
| D | Dato mal cargado | Escribe 1,5 en vez de 15; elige "Parcial" en vez de "Completo" |
| P | Paso omitido | No aprueba la línea base antes de buscar la curva S |
| A | Pidió ayuda | Pregunta al moderador dónde está algo o qué significa un término |
| S | Error del sistema | Mensaje de error, pantalla en blanco, botón que no responde |

Un mismo momento puede tener más de un código (ej. un error del sistema que lo obliga a pedir ayuda: S + A).

## 6. Hoja de registro (una por participante)

Participante: ________ Cargo: ________ Experiencia (años): ____ Presupuesta con: ________ Conoce EVM: sí / de oído / no

| # | Inicio | Fin | Tiempo (min) | ¿Completó? (sí / con ayuda / no) | D | P | A | S | Observaciones (qué hizo, dónde dudó, qué dijo) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | |
| 2 | | | | | | | | | |
| 3 | | | | | | | | | |
| 4 | | | | | | | | | |
| 5 | | | | | | | | | |

**Indicadores que se reportan** (por tarea y en total): tiempo medio frente a la meta; tasa de éxito
(sí / con ayuda / no); número de errores por tipo; puntaje SUS; temas repetidos en los comentarios.

## 7. Cuestionario SUS (System Usability Scale)

Escala de 1 (totalmente en desacuerdo) a 5 (totalmente de acuerdo). Se marca una sola opción por frase.

| # | Afirmación | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Creo que me gustaría usar este sistema con frecuencia. | | | | | |
| 2 | El sistema me pareció innecesariamente complejo. | | | | | |
| 3 | El sistema me pareció fácil de usar. | | | | | |
| 4 | Creo que necesitaría ayuda de una persona técnica para poder usar este sistema. | | | | | |
| 5 | Las distintas funciones del sistema están bien integradas. | | | | | |
| 6 | El sistema me pareció demasiado inconsistente. | | | | | |
| 7 | Imagino que la mayoría de las personas aprendería a usar este sistema muy rápido. | | | | | |
| 8 | El sistema me pareció muy engorroso de usar. | | | | | |
| 9 | Me sentí muy seguro(a) usando el sistema. | | | | | |
| 10 | Tuve que aprender muchas cosas antes de poder usar el sistema. | | | | | |

**Cálculo:** frases impares → (respuesta − 1); frases pares → (5 − respuesta). Se suman los 10 valores y se
multiplica por 2,5 → puntaje de 0 a 100. Referencia usual: 68 es el promedio; por encima de 80 es bueno.

## 8. Preguntas abiertas (al final, grabadas o anotadas)

1. ¿Qué fue lo más difícil o confuso? ¿En qué tarea?
2. ¿Qué parte te sería más útil en tus obras reales? ¿Cuál no usarías?
3. ¿La plantilla Excel se parece a cómo presupuestas hoy? ¿Qué le cambiarías?
4. ¿Se entendió qué es la clase del estimado y la línea base? ¿Cómo lo explicarías a un colega?
5. ¿Pagarías por algo así o lo usarías si fuera gratis? ¿Qué le falta para que lo uses?

## 9. Cuidados

- Se pide consentimiento verbal para anotar y, si se graba, para grabar. Los datos de la pyme se presentan
  sin nombres de clientes ni montos reales si la pyme lo pide.
- El moderador no explica la interfaz durante las tareas; solo responde cuando le preguntan (y se anota "A").
- Una sola pyme con 1–3 participantes da hallazgos cualitativos de usabilidad, no resultados estadísticos.
