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
Ver docs/plan-mvp.md. Python local: 3.10 (no usar f-strings anidados con las mismas comillas).

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
  - [ ] Próximos: ruta crítica (CPM), equipo, comparar con presupuesto → docs/plan-mvp.md §7
  - [ ] Estimación desde plano CAD/BIM + formulario → pasos del proyecto y ruta crítica (propuesta)
        → docs/plan-estimacion-planos.md (orden: C0 ruta crítica → E0 → E1…)
    - [ ] EN CURSO: subir plano DXF (CAD) o IFC (BIM); formulario solo para CAD. Lectores propios, sin
          librerías externas (licencias). Hecho: `calculos/plano_dxf.py`, `calculos/medicion_plano.py`,
          `calculos/plano_ifc.py`, `calculos/computos.py`, planos de prueba en `tests/planos_prueba.py`,
          tablas `Estimacion` y `MapeoCapa` en modelos.py, `CARPETA_PLANOS` en config.
          Falta: migración Alembic, `app/planos.py` + `rutas/estimaciones.py` (subir con cuerpo binario
          `?nombre=`, capas+unidades, plantas, formulario solo dxf, cantidades con ediciones, geometría),
          tests, página `EstimarObra` + `VistaPlano` + `TablaCantidades`, botón en Cronograma.
          Después: generar cronograma y ruta crítica desde las cantidades.
  - [ ] Íconos PNG, prueba en celular real
  - [ ] Dockerfile, CI (GitHub Actions), README con instrucciones
- [ ] Fase 3: piloto con 2 constructores
