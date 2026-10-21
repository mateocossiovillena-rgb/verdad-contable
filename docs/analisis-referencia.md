# Análisis de la referencia (OpenConstructionERP)

> Solo lectura funcional. Licencia AGPL-3.0: aquí se anotan **ideas**, no código ni esquemas.
> Fuentes revisadas: README, MODULES.md, docs/architecture/ y un vistazo (nombres y docstrings) a los
> módulos de cronograma, avance, finanzas y EVM. ~11 archivos.

## Qué es
Un ERP de construcción para empresas medianas/grandes: más de 190 módulos (presupuestos BOQ, BIM/CAD,
licitaciones, facturación electrónica de varios países, IA, CRM…). Es de escritorio primero, pensado
para oficina técnica, y requiere PostgreSQL, Redis, almacenamiento S3, etc.

## Qué nos sirve (como idea)
1. **Cálculo EVM como funciones puras y aisladas.** Separan la matemática de PV/EV/AC/SPI/CPI/EAC de la
   base de datos para probarla con tests unitarios. Coincide con nuestra regla de "módulo propio con tests".
2. **Índices indefinidos = "sin dato", no cero.** Si PV o AC es 0, SPI/CPI no existen; la interfaz debe
   mostrar "—" en vez de un 0 o un infinito engañoso.
3. **Dinero en decimales exactos**, nunca en flotantes; redondeo a 2 decimales solo al mostrar.
4. **El avance se registra como historial (solo agregar).** Cada registro de "% de avance" es una nueva
   observación con fecha; el avance actual es la última. Permite ver la curva en el tiempo y no se pierde
   información si alguien se equivoca.
5. **PV repartido en el tiempo.** El presupuesto de cada partida se distribuye entre su fecha de inicio y fin;
   PV a una fecha = parte acumulada a esa fecha. Para el MVP basta un reparto lineal.
6. **Advertencias de distorsión.** Avisar cuando los números no tienen sentido (ej. avance 100 % sin gastos,
   gastos sin avance, partida sin fechas). Útil para nuestras alertas tempranas.
7. **Comprometido vs. gastado.** Distinguen lo ya pagado de lo prometido (órdenes firmadas). Idea para v2;
   en el MVP solo contamos lo gastado.
8. **Diseño para el trabajador de obra** (su documento de diseño móvil): una sola columna, botones grandes en la
   parte inferior de la pantalla, pocos toques, rol restringido que solo ve su obra y no puede borrar,
   y tolerancia a perder la señal (guardar en el teléfono y sincronizar después). Es justo nuestro maestro de obra.

## Qué sobra para nosotros
- BIM/CAD/IFC, cómputos sobre planos, nubes de puntos, 4D/5D.
- Catálogos de 120 000 ítems de costo, búsqueda vectorial, IA, OCR.
- Facturación electrónica de otros países, pagos, retenciones, contabilidad GAAP.
- Sistema de plugins/marketplace de módulos, 44 idiomas, colaboración en tiempo real.
- CPM, calendarios laborales, rutas críticas, Last Planner, tipos múltiples de % de avance.
- Infraestructura pesada (Redis, Celery, MinIO, Qdrant). Nosotros: una base de datos y listo.

## Conclusión
Lo útil es la **disciplina del cálculo** (puro, decimal, con tests, índices indefinidos) y el **enfoque móvil
para el encargado**. Todo lo demás es alcance de un ERP corporativo que no necesita una PyME boliviana.
Nuestro diferencial, que la referencia no cubre, es el gasto informal sin factura y el cierre diario simple.
