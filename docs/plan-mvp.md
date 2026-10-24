# Plan del MVP — Verdad Contable

Objetivo: que un constructor sepa en 10 segundos **cuánto gastó realmente** en una obra y **si va atrasado
o gastando de más**. Mobile first, en español, moneda Bs.

## 1. Pantallas

**Encargado / maestro de obra (celular)**
1. **Inicio de obra**: total gastado hoy, botones grandes "+ Gasto" y "+ Avance".
2. **Nuevo gasto** (≤ 15 s): monto, tipo (material, mano de obra, subcontrato, caja chica, transporte),
   partida, nota corta, foto del comprobante opcional, casilla "sin factura". Fecha = hoy por defecto.
3. **Registrar avance**: elegir partida → deslizador de % (pasos de 5 %) → nota/foto opcional.
4. **Cierre del día**: lista de gastos de hoy, total del día y acumulado; botón "Cerrar día".

**Dueño / constructor (celular y escritorio)**
5. **Mis obras**: tarjeta por obra con semáforo (verde/amarillo/rojo), gastado vs. presupuesto, SPI y CPI.
6. **Detalle de obra**: indicadores EVM, frase clara ("Gastaste el 45 % del presupuesto pero avanzaste el 30 %"),
   curva PV/EV/AC en el tiempo, lista de partidas con su desvío.
7. **Partidas y cronograma**: crear/editar partidas (nombre, fase, inicio, fin, presupuesto) e hitos.
8. **Gastos**: listado filtrable (fecha, partida, tipo, sin factura), exportar a Excel.
9. **Alertas**: obras/partidas fuera de rango y días sin cierre.
10. **Equipo**: invitar encargados y asignarlos a obras.

## 2. Modelo de datos (propio)

| Entidad | Campos principales |
|---|---|
| `usuario` | id, nombre, teléfono/correo, rol (`dueno`, `encargado`) |
| `obra` | id, dueño_id, nombre, ubicación, fecha_inicio, fecha_fin, moneda (Bs) |
| `asignacion` | usuario_id, obra_id (qué encargado ve qué obra) |
| `partida` | id, obra_id, código (1, 1.1…), nombre, fase, fecha_inicio, fecha_fin, presupuesto (BAC), orden |
| `hito` | id, obra_id, nombre, fecha_prevista, fecha_real |
| `avance` | id, partida_id, fecha, porcentaje (0–100), nota, foto, usuario_id — **solo se agregan registros** |
| `gasto` | id, obra_id, partida_id, fecha, monto (decimal), tipo, descripción, con_factura (sí/no), foto, usuario_id, creado_en |
| `cierre_dia` | id, obra_id, fecha, total_dia, acumulado, usuario_id |

Reglas: montos en `NUMERIC(14,2)`; los gastos no se borran, se anulan (campo `anulado` + motivo) para
mantener la trazabilidad; un día cerrado solo lo reabre el dueño.

## 3. Cálculo EVM (módulo `calculos/`, sin acceso a BD, con tests)

Para una fecha de corte `t`, por partida y luego sumado por obra:
- **BAC** = presupuesto de la partida.
- **PV(t)** = BAC × fracción de días transcurridos entre inicio y fin (0 antes, 1 después; reparto lineal).
- **% avance** = último registro de `avance` con fecha ≤ t (0 si no hay).
- **EV** = BAC × % avance. **AC** = suma de gastos no anulados con fecha ≤ t.
- **SV = EV − PV**, **SPI = EV / PV**; **CV = EV − AC**, **CPI = EV / AC**; **EAC = BAC / CPI**.
- **Avance esperado según gasto** = AC / BAC, comparado con el % de avance real.
- Gastos sin partida van a una partida "Generales" de la obra para que AC cuadre con el total gastado.
- Si el denominador es 0 → resultado "sin dato" (`None`), nunca 0.
- **Alertas**: SPI < 0,90 o CPI < 0,90 (amarillo), < 0,80 (rojo); AC > BAC; partida con gasto y 0 % de avance
  por más de 7 días; obra sin cierre ayer. Umbrales configurables por obra.
- Tests con casos a mano (en Excel) que incluyan: sin gastos, sin fechas, avance 100 %, gasto > presupuesto.

## 4. Stack recomendado

- **Backend**: Python 3.12 + **FastAPI** + SQLAlchemy/Alembic + **PostgreSQL**. El dueño ya conoce Python y el
  módulo de cálculos queda en Python puro con `pytest`.
- **Frontend**: **React + TypeScript + Vite** como **PWA** instalable (Tailwind para estilos, React Query para
  datos). Cola local de registros para cuando no hay señal.
- **Fotos**: almacenamiento tipo S3 barato (Cloudflare R2) con compresión en el celular antes de subir.
- **Login**: enlace o código por WhatsApp/SMS para el encargado; correo y contraseña para el dueño.
- **Despliegue**: un solo servicio (FastAPI sirve también el frontend compilado) + Postgres gestionado en
  Railway/Render/Fly. Sin Redis ni colas en el MVP.
- **Exportar**: Excel con `openpyxl`.

## 5. Pasos en orden

1. Repositorio, estructura, CI con tests y linters; despliegue "hola mundo".
2. Módulo `calculos/` con tests (antes que cualquier pantalla).
3. Modelo de datos y migraciones; datos de prueba de una obra realista.
4. API: obras, partidas, avances, gastos, cierres, con permisos por rol y obra.
5. Login (dueño y encargado).
6. Pantallas del encargado: nuevo gasto, avance, cierre del día (probar en celular real).
7. Pantallas del dueño: mis obras, detalle con indicadores y curva, partidas.
8. Fotos de comprobantes y modo sin señal.
9. Alertas y exportación a Excel.
10. Prueba interna con una obra real → ajustes → Fase 3 (piloto con 2 constructores).

Fuera del MVP: marketplace de insumos, cotizaciones de subcontratistas, compras comprometidas, facturación.

## 6. Cronograma de la obra (implementado)

- **Obra**: nombre, ubicación, cliente, fecha de inicio, moneda (Bs/USD) y presupuesto total opcional.
  La fecha de fin ya no se pide: es el fin de la última actividad.
- **Fase** (`fase`): agrupa actividades; se crean, renombran, borran (con sus actividades) y reordenan.
- **Actividad** (`actividad`): nombre, duración en días calendario, fecha de inicio manual y predecesoras.
  Con predecesoras, el inicio es el día siguiente al fin de la última de ellas (la fecha manual se ignora).
  `fecha_inicio` y `fecha_fin` se guardan ya calculadas y se recalculan en cada cambio.
- **Dependencia** (`dependencia`): enlace predecesora → sucesora con `tipo` (hoy solo `FC`, fin-comienzo)
  y `desfase_dias` (hoy 0). Las dependencias circulares se rechazan nombrando el ciclo.
- Cálculo en `backend/app/calculos/cronograma.py` (sin base de datos, con tests): orden topológico +
  paso hacia adelante del CPM.
- Pantalla de la obra: datos, línea de tiempo (Gantt por fase con marca de hoy) y editor de fases/actividades.
- **Mano de obra y materiales por actividad** (`recurso_actividad`), en el mismo formulario de la actividad:
  - Mano de obra: cargo, personas y costo por persona, pagado **por día** (jornal: × duración de la actividad)
    o **por la actividad** (destajo: no cambia con la duración).
  - Materiales: descripción, cantidad, unidad y precio unitario → cantidad × precio.
  - Costo por actividad (mano de obra, materiales, total), por fase y por obra, en la moneda de la obra.
    Cálculo en `backend/app/calculos/costos.py`, redondeado al centavo.

## 7. Próximos pasos (preparados en el modelo, sin implementar)

**Ruta crítica (CPM)**
1. Paso hacia atrás sobre el mismo orden topológico de `calculos/cronograma.py`: inicio y fin tardíos.
2. Holgura total = inicio tardío − inicio temprano; actividades con holgura 0 = ruta crítica.
3. Usar `dependencia.tipo` para los otros enlaces (CC comienzo-comienzo, FF fin-fin, CF) y
   `dependencia.desfase_dias` para esperas (ej. fraguado del hormigón). Hoy el cálculo ya suma el desfase.
4. Mostrar la ruta crítica en rojo en el Gantt y la holgura de cada actividad.
5. Opcional: calendario laboral (días hábiles, feriados de Bolivia) en lugar de días calendario.

**Costos de las actividades (mano de obra y materiales ya están)**
1. Equipo y maquinaria (mezcladora, vibradora, volqueta): nuevo valor `equipo` en `recurso_actividad.tipo`,
   con pago por día o por la actividad como la mano de obra.
2. Comparar el costo de las actividades con `obra.presupuesto_total` (aviso si lo supera).
3. ~~Unir actividades con partidas (EVM)~~ **hecho**: cada actividad tiene su partida (`partida.actividad_id`,
   `desde_cronograma`), sincronizada en cada recálculo del cronograma (`servicios.sincronizar_partidas`):
   nombre, fase, fechas (→ PV) y costo de mano de obra + materiales como presupuesto (→ BAC; si la actividad
   no tiene costos se conserva el presupuesto). Esas partidas no se editan ni borran desde Partidas. Al borrar
   la actividad se borra su partida, salvo que tenga gastos o avances: queda como partida suelta.
   Partidas sueltas (manuales) siguen existiendo para lo que no está en el cronograma.
