# Verdad Contable

App de control de obra para constructores (PyMEs y emprendedores de la construcción en Bolivia).
Responde dos preguntas que hoy nadie responde en obra:

1. **¿Dónde debería estar mi obra según lo que gasté, y voy atrasado?**
2. **Al final del día, entre todo el desorden y la informalidad, ¿cuánto gasté realmente en esta casa?**

Idioma de la interfaz y de la documentación: español. Moneda por defecto: Bs (bolivianos).

## Módulos

### MVP (v1)
1. **Línea de tiempo y avance**: proyecto → partidas/fases (WBS) con fechas, presupuesto y % de avance físico.
   Hitos. El avance físico se registra de forma simple (ej. "muro del 2do piso al 60%").
2. **Registro contable "gasté vs. debería"**: registro rápido de gastos diarios (materiales, mano de obra,
   subcontratos, caja chica, transporte), asignados a una partida, con foto del comprobante opcional
   (en obra muchos gastos no tienen factura). Cierre diario: total gastado hoy y acumulado por obra.
   Alerta temprana cuando el gasto o el atraso se desvían.

### Versión 2 (no construir todavía)
3. **Súper de insumos / marketplace**: ferreterías y proveedores locales publican y actualizan sus propios
   precios; el presupuesto de las fases pendientes se recalcula con precios vivos.
4. Cotizaciones rápidas de subcontratistas (plomería, carpintería, mampostería) para tener un número externo
   con el cual compararse.

## Cálculos (Valor Ganado / EVM, estándar PMBOK)
- **BAC**: presupuesto total de la partida/obra.
- **PV** (valor planificado): lo que debería haberse ejecutado a una fecha según el cronograma.
- **EV** (valor ganado): BAC × % de avance físico real.
- **AC** (costo real): suma de gastos registrados.
- **SV = EV − PV**, **SPI = EV / PV** → SPI < 1 = atrasado.
- **CV = EV − AC**, **CPI = EV / AC** → CPI < 1 = gastando más de lo que avanza.
- **EAC = BAC / CPI**: estimación de costo final.
- "Dónde debería estar según lo gastado": avance esperado = AC / BAC (comparar con el avance físico real).
Todos los cálculos van en un módulo propio con tests.

## Usuarios
- Dueño/constructor: ve todas sus obras, alertas y totales.
- Maestro de obra / encargado: registra gastos y avance desde el celular, rápido y sin complicaciones.
Debe funcionar bien en celular (mobile first).

## REGLA DE LICENCIAS (obligatoria)
- En `../referencias/OpenConstructionERP` hay un clon de OpenConstructionERP, licencia **AGPL-3.0**.
- Se puede LEER para entender ideas, funciones, flujos y estructura.
- **Nunca** copiar, adaptar, traducir ni parafrasear su código, nombres de archivos internos, esquemas de base
  de datos o textos dentro de este proyecto. Todo el código de Verdad Contable se escribe desde cero.
- No modificar nada dentro de la carpeta de referencias.

## Stack
FastAPI + SQLAlchemy/Alembic + PostgreSQL (SQLite en local) · React + TypeScript + Vite + Tailwind (PWA).
Ver docs/plan-mvp.md. Python 3.12 en local y en producción.

## Estado
- [x] Fase 0: análisis funcional de la referencia → docs/analisis-referencia.md
- [x] Fase 1: plan del MVP, stack y modelo de datos → docs/plan-mvp.md
- [ ] Fase 2: construir MVP (en curso)
  - [x] Backend: cálculos EVM, modelos, migración inicial, API, datos demo, 36 tests (`backend/`)
  - [x] Frontend base: api, cola sin señal, sesión, UI, Marco, Curva, Ingresar/Registro, Obras, Hoy/Cierre
  - [x] App.tsx (rutas), main.tsx (+ registro de sw.js), index.css; npm install + build
  - [x] Cronograma: obra (cliente, moneda Bs/USD, presupuesto total), fases, actividades con predecesoras,
        Gantt por fase con marca de hoy (FormObra, DetalleObra, `calculos/cronograma.py`, 51 tests)
  - [x] Rediseño según `guia-diseno-frontend.md`: íconos SVG propios (`componentes/iconos.tsx`), componentes
        base en `ui.tsx` (Pildora, Metrica, Pestanas, Interruptor, OpcionGrande, avisos), cabecera blanca,
        menú Obras · Alertas · Cuenta (Equipo fuera del menú)
  - [x] Pantallas NuevoGasto, NuevoAvance, Partidas+hitos, Gastos (filtros, Excel, anular), Alertas, Cuenta;
        DetalleObra con pestañas Resumen (frase, métricas, curva S, índices) y Cronograma
  - [ ] Revisar el rediseño en celular real (al sol, con señal débil)
  - [x] Mano de obra (por día o por la actividad) y materiales por actividad, con costos por fase y obra
  - [ ] Próximos: equipo, comparar con presupuesto → docs/plan-mvp.md §7 (ruta crítica ya está)
  - [ ] Estimación desde plano CAD/BIM + formulario → pasos del proyecto y ruta crítica (propuesta)
        → docs/plan-estimacion-planos.md (orden: C0 ruta crítica → E0 → E1…)
    - [x] Subir plano DXF (CAD) o IFC (BIM) y confirmar capas/unidades, plantas, formulario (solo CAD) y
          cantidades editables. Lectores propios sin librerías externas (licencias): `calculos/plano_dxf.py`,
          `medicion_plano.py`, `plano_ifc.py`, `computos.py`; servicio `app/planos.py`; API
          `rutas/estimaciones.py`; pantalla `EstimarObra` (botón en Cronograma); 84 tests.
    - [x] Ruta crítica (holguras, Gantt en rojo) y paso "Cronograma": catálogo base ilustrativo
          (`calculos/catalogo.py`), generador `calculos/estimacion.py` (secuencia por piso, cuadrillas
          compartidas, sugerencia de cuadrilla), vista previa y "Crear cronograma" (agregar o reemplazar).
    - [ ] Siguiente: calibrar el catálogo con constructores y hacerlo editable por dueño; probar con un plano
          real; enlaces CC; feriados de Bolivia.
  - [x] Preparación de la demo: pantalla Equipo (Cuenta → Equipo: crear encargado, PIN, obras, quitar acceso),
        límite de intentos de ingreso (5 por cuenta / 20 por IP en 15 min, en memoria), `CLAVE_SECRETA`
        obligatoria con `ENTORNO=produccion`, datos demo con cronograma y ruta crítica, guion en
        `docs/guion-demo.md`; 111 tests. Entorno local: `backend/.venv` (`pip install -r requirements-dev.txt`).
  - [x] Cronograma unido al EVM: cada actividad crea y mantiene su partida (fechas → PV, costo → BAC), así el
        plano → cronograma → gastos/avance → semáforo es un solo flujo (docs/plan-mvp.md §7.3); 119 tests.
        Bases con cronograma anterior: `python -m app.sincronizar` una vez tras `alembic upgrade head`.
  - [x] Duración de actividades en días, semanas (por defecto) o meses: se guarda cantidad + unidad y el backend
        la convierte a `duracion_dias` (semana = 7, mes = 30, hacia arriba) con `cronograma.a_dias`; 125 tests.
  - [x] "Gastos generales" como costo indirecto (nivel de esfuerzo: EV = PV, fechas de la obra si no tiene
        propias): sin alertas de fechas ni avance y sin atrasar a la obra; íconos PNG 192/512;
        `python -m app.cambiar_clave` para dar clave temporal a un dueño; 131 tests.
  - [ ] Prueba en celular real (antes de pasar el link a constructores)
  - [x] Dockerfile, CI (GitHub Actions: lint, tests, migraciones en PostgreSQL, build), README,
        `render.yaml` (Railway tenía cerradas las cuentas nuevas); Python 3.12. Plan de publicación y cobro acordado: fotos a R2, respaldos, Brevo, cobros por QR.
  - [x] Publicada en Render con el Blueprint (2026-10-30): https://verdad-contable.onrender.com,
        `/api/salud` responde ok. Ver "Publicación" abajo.
- [ ] Fase 3: piloto con 2 constructores → docs/piloto.md
- [ ] Kit TCM (AACE) para pymes — proyecto final de Costos Industriales, rama `kit-tcm` (no publicar en `main` sin
      decidirlo). Plan: fases 1 estimado + línea base + Excel, 2 EVM AACE (82R-13/80R-13), 3 riesgos (44R-08),
      4 cambios, 5 kit y prueba de uso.
  - [x] Fase 1: clase del estimado (`app/tcm/clases_estimado.toml` editable, valores 56R-08 a verificar por el
        usuario; `tcm/clasificacion.py`), APU con % por obra (`calculos/costos.py`: cargas sociales, IVA m. de obra,
        herramientas, GG, utilidad, IT; equipo como tipo de recurso), Base del estimado (34R-05), línea base
        versionada e inmutable (`LineaBase`/`LineaBasePartida`; el EVM mide contra la vigente en
        `servicios.datos_obra`), PV semanal (`tcm/linea_base.py`), plantilla Excel + importador con vista previa
        (`tcm/plantilla.py`), exportación (`tcm/exportar.py`), API `rutas/tcm.py`, pestañas Estimado/Base/Línea base
        y página ImportarObra; ejemplo `python -m app.tcm.ejemplo` → `kit/ejemplo/vivienda-120m2.xlsx`; guion
        `kit/prueba-de-uso.md`; 163 tests. Decisión: BAC = precio de venta total del APU.
  - [x] Fase 2: regla de medición del avance por partida (`Partida.regla_medicion`: % físico, 0/100, 50/50;
        `vg.fraccion_ganada`; PUT `/partidas/{id}/medicion`; columna J de la plantilla), pronósticos 80R-13
        (`tcm/pronostico.py`: EAC atípico, BAC/CPI, CPI×SPI, ETC, VAC, TCPI) en `/indicadores`, Resumen con
        nomenclatura AACE (equivalencias BCWS/BCWP/ACWP), hoja "Valor ganado" con curva PV/EV/AC en el Excel;
        obra de ejemplo en ejecución (`ejemplo.cargar_en_ejecucion`, 9 semanas, sobrecosto y atraso); 179 tests.
  - [x] Fase 3: registro de riesgos 44R-08 (`Riesgo`, `tcm/riesgos.py`: valor esperado P × I, días esperados, nivel
        por matriz 3×3, resumen de abiertos); API `/obras/{id}/riesgos`, `/riesgos/{id}`, POST
        `/obras/{id}/riesgos/contingencia` (copia Σ P × I a la Base del estimado); pestaña Riesgos; 6 riesgos de
        ejemplo; 192 tests. Importar/exportar riesgos por Excel queda para la fase 4.

## Publicación (Render)
- Blueprint `render.yaml`: servicio web `verdad-contable` (Docker, Starter, Virginia) + Postgres
  `verdad-contable-db` (basic-256mb, PG 17) + disco de 1 GB en `/data` (fotos y planos). ~US$13–14/mes.
- Se publica solo al hacer push a `main` si pasa GitHub Actions (`autoDeployTrigger: checksPass`).
- Variables: `DATABASE_URL` (de la base), `CLAVE_SECRETA` (generada por Render), `ENTORNO=produccion`,
  `CARPETA_FOTOS`, `CARPETA_PLANOS`.
- Soporte: clave temporal de un dueño → Render → Shell → `python -m app.cambiar_clave correo`.
- La API key de Render **nunca** va en el repo ni en este archivo; se usa como variable de entorno
  `RENDER_API_KEY` fuera del proyecto.
- Orden pendiente: 1) prueba en celular real 2) R2 (fotos y respaldos), correo con Brevo y recuperación de
  clave, términos, anti-abuso, borrar cuenta 3) cobros (Bs 140/mes, QR, activación manual en panel admin)
  4) dominio propio, Sentry + UptimeRobot, demo 5) abrir al público.
