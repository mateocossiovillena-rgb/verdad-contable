# Guía de diseño del frontend — Verdad Contable

Documento de referencia para rediseñar la interfaz. **Paso 1: solo investigación y criterios; no se cambió
código.** Los pasos siguientes aplican esta guía pantalla por pantalla.

Fecha: 23/10/2026 · Stack: React + TypeScript + Vite + Tailwind (PWA, mobile first).

---

## 1. Qué hacen los ERPs de construcción (investigación)

### Procore (líder del mercado, EE. UU.)
- **Web:** barra superior oscura con selector de proyecto y un menú de "herramientas" (Schedule, Daily Log,
  Budget, RFIs, Punch List…), cada una con ícono y nombre. Inicio del proyecto con tarjetas y una tabla de
  "salud del proyecto" que junta varias obras con indicadores financieros.
- **Cronograma:** Gantt con barras de color y dependencias; las tareas enlazan con el diario de obra.
- **App móvil:** versión recortada de la web, centrada en **capturar datos rápido**: botón de "creación
  rápida" para las entradas más usadas (personal, equipos, notas), fotos con GPS y fecha, y trabajo **sin
  señal** que se sincroniza solo.
- **Diario de obra:** vista de lista y de **calendario con puntos de color por día** (pendiente / aprobado /
  completo), para ver de un vistazo qué días faltan.
- Color de marca naranja, usado con moderación sobre superficies neutras.

### Autodesk Construction Cloud / Autodesk Build (ex PlanGrid)
- Encabezado oscuro, contenido en blanco y gris claro, tablas densas en la web y app de campo centrada en
  planos, tareas y fotos. Un solo color de acento (azul) para acciones.

### Fieldwire (Hilti)
- La app gira en torno a **planos y tareas**: visor de planos rápido que funciona sin señal, marcas sobre el
  plano y tareas con ubicación, rubro, prioridad y responsable. Las reseñas destacan la navegación simple.

### Buildertrend (constructoras pequeñas y residenciales)
- Barra lateral con el logo y el menú (quitaron la cabecera blanca para ganar espacio). Presupuesto de
  "costeo por obra" que muestra en tiempo real cómo afectan al margen la mano de obra, los cambios y los
  gastos imprevistos. La app móvil es lo que más valoran los equipos de campo.

### Software latinoamericano (Opus, Neodata, BrickControl, ComovApp)
- Opus y Neodata vienen del escritorio: pantallas densas tipo planilla, pestañas, catálogos de precios
  unitarios y reportes para licitación. Potentes para el ingeniero de costos, **duros para el maestro de
  obra**. Las apps móviles de la región se limitan a fotos, avance y aprobaciones.
- **Oportunidad para Verdad Contable:** ninguno resuelve bien el "cuánto gasté realmente hoy" desde el
  celular y con la informalidad local (gastos sin factura, caja chica, pagos en efectivo).

### Tableros de Valor Ganado (EVM)
- Patrón común (EcoSys de Hexagon, visuales de Power BI): **panel de indicadores** (SPI, CPI, CV, SV, EAC,
  BAC, % avance) con semáforo verde/ámbar/rojo + **curva S** (PV, EV, AC acumulados) + barras por periodo.
- Umbrales usados como ejemplo (FEMA): verde 0,95–1,05 · ámbar 0,90–0,95 · rojo por debajo de 0,90.

### Diseño para gente que trabaja en obra (guías de diseño de apps de campo)
- **Áreas de toque grandes:** 48 px como mínimo absoluto, 60 px recomendado y 72 px para la acción principal
  (guantes, manos sucias, apuro). Al menos 16 px entre botones vecinos.
- **Sol directo:** contraste alto (ideal 7:1 en el texto), nada de gris claro sobre blanco, borde fino en
  botones y campos para que no "desaparezcan" con el reflejo. El color nunca va solo: siempre con texto o ícono.
- **Una pantalla, un trabajo.** Cada tarea común se termina en unos 30 segundos y sin instrucciones.
- Botones grandes en vez de listas desplegables cuando hay pocas opciones; nada importante escondido en un
  menú hamburguesa.
- **Primero sin señal:** se guarda en el celular, se envía después y siempre se ve el estado de la conexión.
- Guardar el avance de un formulario a medio llenar; evitar gestos de deslizar para borrar.

---

## 2. Conclusiones: qué copiar y qué evitar

| Lo que hacen bien los grandes | Cómo lo aplicamos |
|---|---|
| Superficies neutras y **un solo color de acento** para acciones | Naranja de marca solo en el botón principal y la navegación activa |
| Captura rápida en el celular (creación rápida) | Pantalla "Hoy" con dos botones gigantes: **+ Gasto** y **+ Avance** |
| Semáforos de salud por obra | Semáforo con **texto** ("A tiempo", "Atrasado", "Sobrecosto") |
| Curva S + panel de índices | En "Detalle de obra": curva S arriba e índices en lenguaje simple debajo |
| Calendario con puntos por día | Cierre diario: calendario con días cerrados, abiertos y sin registro |
| Trabajo sin señal | La barra de pendientes que ya existe, con un estilo más claro |

| Lo que evitamos | Por qué |
|---|---|
| Pantallas densas tipo planilla (Opus/Neodata) | El maestro de obra usa el celular de pie, al sol |
| Siglas sin explicar (SPI, CPI) para el encargado | Se muestran como "Vas 8 % atrasado"; la sigla queda para el dueño |
| Emojis como íconos | Se ven distintos en cada celular, se leen mal al sol y parecen poco serios |
| Encabezado de color sólido a todo lo ancho | Le quita protagonismo al único botón naranja que importa |

---

## 3. Principios de diseño de Verdad Contable

1. **Dos usuarios, dos densidades.** El *encargado* ve pantallas grandes y simples, de una acción. El
   *dueño* ve más datos (tablas, índices y curvas), pero siempre con una frase que los explique.
2. **El número primero.** Cada pantalla responde una pregunta con una cifra grande: "Gastado hoy",
   "¿Voy atrasado?", "¿Cuánto costará al final?".
3. **Legible al sol.** Contraste alto, letra base de 16 px, bordes visibles.
4. **El color significa algo.** Cada color tiene un único significado y siempre va acompañado de texto.
5. **Sin señal no es un error.** Guardar siempre y avisar con calma cuando queda algo pendiente de envío.
6. **Serio, no genérico.** Nada de degradados, emojis ni tarjetas de colores chillones: es una herramienta de
   trabajo para cuidar plata.

---

## 4. Tokens de diseño (sobre lo que ya existe)

Se respeta el sistema actual (`tailwind.config.js` con `marca` naranja y base `stone`). Solo se ordena.

### 4.1 Colores

| Uso | Clase Tailwind | Notas |
|---|---|---|
| Fondo de la app | `bg-stone-50` | Neutro cálido; hoy el lienzo no tiene fondo propio |
| Tarjeta / superficie | `bg-white` + `border border-stone-200` + `shadow-sm` | Borde visible para el reflejo del sol |
| Texto principal | `text-stone-900` | |
| Texto secundario | `text-stone-600` | **No** `stone-500` sobre blanco en pantallas de campo (poco contraste al sol) |
| Texto terciario / ayuda | `text-stone-500` | Solo para textos poco importantes |
| Acción principal | `bg-marca-600` → `hover:bg-marca-700` | **Un solo botón primario por pantalla** |
| Navegación activa | `text-marca-700` | |
| Bien / a tiempo | `emerald-700` sobre `emerald-50` | |
| Atención / atraso | `amber-800` sobre `amber-50` | **No usar naranja para alertas:** se confunde con la marca |
| Problema / sobrecosto | `red-700` sobre `red-50` | Con moderación |
| Sin datos | `stone-600` sobre `stone-100` | |

> El naranja es el color de la seguridad en obra y también lo usa Procore: encaja con el rubro. Por eso
> mismo **solo sirve para "tocá aquí"**, nunca para alertas.

### 4.2 Tipografía

- Fuente del sistema (ya se usa así): carga rápido y se lee bien en Android de gama baja.
- Base `text-base` (16 px). Nunca menos de `text-sm` (14 px) para datos; `text-xs` solo para metadatos.
- Títulos de pantalla: `text-lg font-semibold tracking-tight`. Nada de `font-extrabold`.
- **Cifra protagonista:** `text-4xl font-semibold tracking-tight tabular-nums` (hoy es `font-bold` y sin
  `tabular-nums`).
- **Todo monto, porcentaje, índice o fecha en columna lleva `tabular-nums`**, y en tablas va alineado a la
  derecha.
- Montos: siempre con `bs()` / `dinero()` de `formato.ts` (`Bs 12.345,60`, `$us 1.000,00`).

### 4.3 Medidas y forma

| Elemento | Medida |
|---|---|
| Botón normal / campo | `min-h-12` (48 px); hoy es `min-h-11` |
| Botón principal de campo | `min-h-14` a `h-16` (56–64 px) |
| Botones grandes de "Hoy" | `h-28` o más (ya está bien) |
| Separación entre botones | `gap-4` (16 px) |
| Radio | `rounded-xl` en botones y campos, `rounded-2xl` en tarjetas (ya está así) |
| Margen lateral | `px-4` |
| Ancho máximo | `max-w-3xl` en celular y tablet; en escritorio, ver §6.5 |

### 4.4 Íconos

- Reemplazar **todos** los emojis (🏗️ 🔔 👷 💸 🧱 📋 ⚠️ 📶 ✔) por íconos SVG de trazo fino y del mismo
  grosor. Recomendado: **lucide-react** (licencia ISC, compatible) o SVG propios.
- Tamaño 20–24 px y siempre acompañados de texto.

### 4.5 Movimiento y respuesta al toque

- Botones y tarjetas tocables: `transition active:scale-[0.98]`.
- Foco visible: `focus-visible:ring-2 focus-visible:ring-marca-500 focus-visible:ring-offset-2`.
- Al guardar: confirmación breve ("Gasto guardado · Bs 350,00") en un aviso abajo; nunca una ventana que
  bloquee la pantalla.

---

## 5. Componentes (en `componentes/ui.tsx`)

Los cambios se hacen **dentro** de cada componente para que se apliquen en toda la app.

| Componente | Hoy | Debe quedar |
|---|---|---|
| `Tarjeta` | `ring-1 ring-stone-200` | `border border-stone-200 shadow-sm`; prop `tocable` con `active:scale` y hover sutil |
| `Boton` | `min-h-11`, 3 variantes | `min-h-12`; variantes `primario`, `secundario` (borde visible), `peligro` y `fantasma` (texto); foco visible; estado de carga con texto ("Guardando…") |
| `Entrada` / `Selector` | `min-h-11`, anillo | `min-h-12`, borde `stone-300`, `inputMode="decimal"` en los montos |
| `PuntoSemaforo` | Punto de color; texto opcional | **Píldora con texto siempre**: `rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset` + punto o ícono |
| `BarraAvance` | Barra naranja + marca negra de "plan" | Barra con color según estado (verde/ámbar/rojo) + marca del plan con etiqueta ("debería: 62 %") |
| `MensajeError` | Caja roja | Igual, más una acción ("Reintentar") cuando sirva |
| `Cargando` | "Cargando…" centrado | Esqueletos grises con la forma de la tarjeta, para que la pantalla no salte |
| **Nuevo** `Metrica` | — | Etiqueta, cifra con `tabular-nums` y variación en píldora (ver §7) |
| **Nuevo** `Aviso` (toast) | — | Confirmaciones breves abajo, sobre la barra de menú |
| **Nuevo** `EstadoVacio` | Textos sueltos | Ícono, frase útil y una acción ("Todavía no hay gastos hoy · + Gasto") |
| **Nuevo** `OpcionGrande` | — | Botones grandes para elegir entre pocas opciones (tipo de gasto) en vez de un `<select>` |

---

## 6. Pantallas

### 6.1 Estructura común (`Marco`)
```
┌─────────────────────────────┐
│ ‹  Casa Mendoza       Salir │  ← cabecera blanca, borde inferior, texto stone-900
├─────────────────────────────┤
│ ⟳ 2 registros esperando señal│  ← solo si hay pendientes (ámbar suave)
├─────────────────────────────┤
│        contenido            │  ← fondo stone-50
│                             │
├─────────────────────────────┤
│  Obras   Alertas(3)  Cuenta │  ← menú inferior con íconos SVG; activo en marca-700
└─────────────────────────────┘
```
- Cabecera **blanca** en vez de naranja sólido: más contraste y el naranja queda para la acción.
- El menú del dueño **ya no enlaza "Equipo"** (quedó fuera del MVP). Propuesta: Obras · Alertas · Cuenta.
- Las alertas muestran un contador en el ícono.
- "Salir" se mueve a Cuenta; en la cabecera es fácil tocarlo sin querer.

### 6.2 Hoy (encargado) — la pantalla más importante
```
┌─────────────────────────────┐
│ Gastado hoy · 23/10/2026    │
│ Bs 1.250,00                 │  ← text-4xl tabular-nums
│ Acumulado obra Bs 84.300,00 │
│ [● Día abierto]             │
├──────────────┬──────────────┤
│   + Gasto    │  + Avance    │  ← h-28, primario y secundario fuerte
├──────────────┴──────────────┤
│       Cierre del día        │  ← secundario
├─────────────────────────────┤
│ Gastos de hoy               │
│ Cemento 10 bolsas  Bs 650,00│  ← monto a la derecha, tabular-nums
│ Materiales · Losa · sin fac.│
└─────────────────────────────┘
```
- Solo **un** botón naranja lleno (+ Gasto). + Avance va como secundario con borde grueso.

### 6.3 Nuevo gasto (pendiente de construir)
Pensada para terminarse en menos de 30 segundos:
1. **Monto** primero, campo grande con teclado numérico (`inputMode="decimal"`) y `Bs` fijo a la izquierda.
2. **Tipo** con 5 botones grandes (Materiales, Mano de obra, Subcontrato, Caja chica, Transporte), no un
   desplegable.
3. **Partida**: la última usada viene marcada.
4. Descripción opcional, interruptor "Tiene factura" y botón **Foto del comprobante** a todo el ancho.
5. Botón fijo abajo: **Guardar Bs 650,00**, que repite el monto como confirmación.
- Sin señal: se guarda igual y avisa "Guardado en el celular · se enviará con señal".

### 6.4 Nuevo avance (pendiente de construir)
- Elegir la partida o actividad → deslizador grande (ya existe el estilo de `input[type=range]`) con el
  porcentaje en `text-4xl` → foto opcional → Guardar.
- Mostrar al lado "Antes: 40 % → Ahora: 60 %".

### 6.5 Mis obras y Detalle de obra (dueño)
**Lista de obras:** cada tarjeta con nombre, cliente y fechas, semáforo en píldora con texto, barra de
avance real contra plan y dos cifras (Gastado de Presupuesto · Hoy).

**Detalle de obra**, de arriba hacia abajo:
1. **Respuesta en una frase:** "Vas **8 % atrasado** y gastando **5 % más** de lo que avanzas." Los colores
   salen del semáforo.
2. **Tres métricas:** Avance real contra esperado · Gastado contra presupuesto · Costo final estimado (EAC).
3. **Curva S** (`Curva.tsx`): PV gris discontinuo, EV verde y AC en el color de la marca; leyenda debajo,
   no encima.
4. **Índices para el dueño** (SPI, CPI, CV, SV) en una tabla compacta, cada uno con su píldora y una
   explicación corta al tocarlo.
5. Pestañas: **Cronograma (Gantt) · Partidas · Gastos · Costos**.
- **Escritorio (≥ 1024 px):** dos columnas (métricas y curva a la izquierda, alertas y último movimiento a
  la derecha) y `max-w-6xl`. Las tablas se aprovechan en la web, como en Procore y Buildertrend.

### 6.6 Gantt
- Barra de fondo `stone-200` y relleno según el avance; color por estado (a tiempo, atrasada, crítica).
- Línea de "hoy" en `marca-600` con la etiqueta "Hoy".
- En celular: lista por fase que se abre y cierra y barra compacta; desplazamiento horizontal solo dentro
  del Gantt, nunca en toda la página.

### 6.7 Cierre del día
- Agregar un **calendario del mes con un punto por día** (idea de Procore): verde = cerrado, ámbar = con
  gastos sin cerrar, gris = sin registro. Se toca un día para ir a él.
- Botón final: **Cerrar el día con Bs 1.250,00** (ya existe; está bien).

### 6.8 Alertas
- Lista ordenada por gravedad: píldora (Atraso / Sobrecosto / Día sin cerrar), obra, frase y fecha.
- Se toca la alerta para ir directo a donde se resuelve.

### 6.9 Ingresar y Registro
- Logo y nombre arriba, un solo formulario y un botón primario. Mantener la sesión abierta (en obra no se
  quiere volver a escribir la contraseña).

---

## 7. Fragmentos de referencia

Métrica:
```tsx
<div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
  <p className="text-sm text-stone-600">Gastado hoy</p>
  <p className="mt-1 text-4xl font-semibold tracking-tight tabular-nums text-stone-900">Bs 1.250,00</p>
  <span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-600/20">
    12 % sobre lo planificado
  </span>
</div>
```

Píldora de semáforo:
```tsx
// verde
"bg-emerald-50 text-emerald-700 ring-emerald-600/20"  // "A tiempo"
// amarillo
"bg-amber-50 text-amber-800 ring-amber-600/20"        // "Atención"
// rojo
"bg-red-50 text-red-700 ring-red-600/10"              // "Problema"
// sin dato
"bg-stone-100 text-stone-600 ring-stone-500/10"       // "Sin datos"
```

Fila de tabla de gastos (dueño):
```tsx
<td className="whitespace-nowrap px-3 py-2.5 text-right tabular-nums text-stone-900">Bs 650,00</td>
```

---

## 8. Diagnóstico del frontend actual (sin cambios aplicados)

| # | Hallazgo | Dónde | Prioridad |
|---|---|---|---|
| 1 | Emojis como íconos en el menú, los botones y los avisos | `Marco.tsx`, `Hoy.tsx` | Alta |
| 2 | Cifras sin `tabular-nums` (saltan al actualizarse y no alinean) | `Hoy.tsx`, `Obras.tsx`, `DetalleObra.tsx` | Alta |
| 3 | El semáforo puede mostrarse solo como un punto de color | `ui.tsx` → `PuntoSemaforo` | Alta |
| 4 | Cabecera naranja sólida compite con el botón principal | `Marco.tsx` | Media |
| 5 | Dos botones naranjas del mismo peso en "Hoy" | `Hoy.tsx` | Media |
| 6 | El menú enlaza "Equipo", que está fuera del MVP | `Marco.tsx` | Media |
| 7 | Texto secundario `stone-500` sobre blanco: se lee mal al sol | Varias | Media |
| 8 | Áreas de toque de 44 px (`min-h-11`); el objetivo es 48 px o más | `ui.tsx` | Media |
| 9 | La app no tiene fondo propio; las tarjetas usan anillo en vez de borde | `index.css`, `ui.tsx` | Baja |
| 10 | "Cargando…" en texto plano en vez de esqueletos | `ui.tsx` | Baja |

Lo que **ya está bien** y se mantiene: mobile first, botones grandes en "Hoy", cola sin señal con aviso,
formato `es-BO` de los montos, cierre del día con el monto en el botón, marca naranja propia y base `stone`.

---

## 9. Orden sugerido de trabajo (próximos pasos)

1. **Base:** tokens y componentes de `ui.tsx` (Tarjeta, Boton, Entrada, Píldora, Metrica, Aviso,
   EstadoVacio) y fondo de la app. Con esto mejora todo de una vez.
2. **Marco:** cabecera blanca, menú con íconos SVG, quitar "Equipo" y agregar Cuenta.
3. **Hoy + Cierre** (pantallas del encargado).
4. **Nuevo gasto y Nuevo avance** (hoy "En construcción"), ya con este diseño.
5. **Mis obras y Detalle de obra** (frase resumen, métricas, curva S, pestañas, escritorio).
6. **Alertas** y Gastos.
7. Prueba en un celular real, al sol y con señal débil.

## 10. Lista de revisión por pantalla

- [ ] ¿Responde una pregunta con una cifra grande?
- [ ] ¿Hay un solo botón naranja?
- [ ] ¿Todos los números tienen `tabular-nums` y, en tablas, alineación a la derecha?
- [ ] ¿Cada color va acompañado de texto?
- [ ] ¿Los controles miden 48 px o más y hay 16 px entre botones?
- [ ] ¿Se lee al sol (texto `stone-600` o más oscuro y bordes visibles)?
- [ ] ¿Funciona sin señal y lo dice?
- [ ] ¿Queda algún emoji, degradado o tarjeta de color chillón?
- [ ] ¿La tarea principal se termina en unos 30 segundos?

---

## Fuentes

- Procore: [Gestión de proyectos](https://www.procore.com/project-management) ·
  [Creación rápida en el diario (iOS)](https://v2.support.procore.com/en-au/product-manuals/daily-log-ios/tutorials/create-daily-log-entries-with-quick-capture/) ·
  [Vista de calendario del diario](https://support.procore.com/tc/procore/Legacy/Release_Documentation_Archives/2019/Daily_Log%3A_Calendar_View_on_the_Procore_iOS_App) ·
  [Mejoras móviles del diario](https://constructionjunkie.com/blog/2020/1/22/procore-adds-3-enhancements-to-daily-logs-amp-safety-incident-logging-on-mobile)
- Fieldwire: [App Store](https://apps.apple.com/us/app/fieldwire-construction-app/id780165517) ·
  [G2: Buildertrend vs Fieldwire](https://www.g2.com/compare/buildertrend-vs-fieldwire-by-hilti)
- Autodesk Build: [Comparativa con Fieldwire](https://tr-web.dev.trustradius.com/compare-products/fieldwire-vs-autodesk-build)
- Buildertrend: [Novedades del producto](https://buildertrend.com/?p=44402) ·
  [Hoja de ruta: presupuesto](https://buildertrend-publicroadmap.launchnotes.io/board/budget-changes)
- Latinoamérica: [Comparativa de software de presupuestos](https://oneestimate.ai/es/blog/software-presupuestos-construccion-comparativa) ·
  [ComparaSoftware: construcción](https://www.comparasoftware.com/construccion) ·
  [Folleto OPUS24](https://www.ecosoft.com.mx/opusv24.pdf)
- EVM: [EcoSys (Hexagon)](https://docs.hexagonppm.com/r/en-US/EcoSys-Projects-Help-4.11/Version-4.11/983530) ·
  [Visual de curva S EVM](https://marketplace.microsoft.com/product/web-apps/abdalla_dabes.evm-s-curve-visual) ·
  [Tablero FEMA (umbrales)](https://hazards.fema.gov/femaportal/resources/mip_faq/mipfaq_13.htm)
- Diseño para campo: [Affective: apps para obreros](https://weareaffective.com/learning-centre/how-should-i-design-apps-for-construction-workers) ·
  [Apps de campo que fallan](https://dev.to/kundanparmarseo/oil-and-gas-mobile-app-why-apps-built-for-offices-always-fail-in-the-field-3000)

> Nota: Procore y Autodesk no publican su sistema de diseño completo. Lo dicho sobre su aspecto sale de sus
> páginas de producto, sus manuales de ayuda y las reseñas. Las medidas de toque y contraste son
> recomendaciones de práctica, no una norma: hay que validarlas en un celular real en obra.
