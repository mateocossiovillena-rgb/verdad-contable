# Guion de la demo — Verdad Contable

Demo de 5 minutos para un constructor, en la red wifi local (sin publicar en internet).
Duración total con preguntas: 15–20 minutos.

## 1. Preparar (la noche anterior o una hora antes)

Las fechas de la obra demo se calculan desde **hoy**: cárgala el mismo día (o la noche anterior) para que
"ayer sin cerrar" y el atraso de la losa salgan como se cuenta abajo.

En PowerShell, desde la carpeta del proyecto:

```powershell
# 1. Compilar la app web (solo si cambió el frontend)
cd frontend; npm run build; cd ..

# 2. Base de datos aparte para la demo (no toca tu base de desarrollo)
cd backend
Remove-Item demo.db -ErrorAction SilentlyContinue
$env:DATABASE_URL = "sqlite:///demo.db"
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.datos_demo

# 3. Servidor visible en el wifi
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- En los celulares abrir `http://<IP de la laptop>:8000`. La IP sale con `ipconfig` ("Dirección IPv4",
  ej. `192.168.0.12`); cambia según la red, revísala en el lugar de la demo.
- Si Windows pregunta por el firewall, permitir **solo redes privadas**. Si el celular no carga, revisar que
  la red wifi esté marcada como "Privada" en Windows.
- Al terminar, cerrar el servidor con `Ctrl+C`. Así nadie más entra.

**Usuarios demo**

| Rol | Usuario | Clave |
|---|---|---|
| Dueño (laptop o tu celular) | `demo@verdadcontable.bo` | `demo1234` |
| Encargado (celular del constructor) | `70000000` | PIN `123456` |

Tras 5 claves equivocadas seguidas la cuenta se bloquea 15 minutos (protección contra quien adivina PINs).
Si pasa en la demo, reiniciar el servidor (`Ctrl+C` y volver a correr el paso 3) lo desbloquea.

**Revisión previa (2 min):** entrar como dueño y como encargado; tomar una foto de prueba desde el celular
y anular ese gasto después en *Gastos*.

## 2. La historia

"Casa familia Quispe", Zona Sur de La Paz, presupuesto Bs 262.000, lleva 7 semanas. La obra parece ir bien,
pero la **losa del 2do piso** va atrasada y gastando de más, y eso arrastra a toda la obra.

## 3. Guion (5 minutos)

**Paso 1 — La pregunta (30 s).** "Si hoy te pregunto cuánto gastaste realmente en la casa de los Quispe y si
vas atrasado, ¿cuánto tardas en responderme?" Dejar que responda.

**Paso 2 — Mis obras, como dueño (1 min).** Tarjeta de la obra con semáforo **amarillo**, gastado contra
presupuesto. Entrar al detalle:
- La frase: "Gastaste el 45 % del presupuesto y avanzaste el 44 %… deberías ir en 55 %: vas atrasado."
- La proyección: "A este ritmo la obra costará unos Bs 7.000 más de lo presupuestado."
- La curva: dónde debería estar contra dónde está.

**Paso 3 — ¿Dónde está el problema? (1 min).** *Partidas*: la losa del 2do piso en **rojo** (25 % de avance
cuando debería ir mucho más) y los muros del 1er piso en amarillo. Luego la pestaña *Cronograma*: la losa
está en la **ruta crítica** (en rojo), o sea que su atraso corre la fecha de entrega.

**Paso 4 — El celular del maestro de obra (1,5 min).** Darle el celular al constructor, con la sesión del
encargado abierta:
- *+ Gasto*: "Cemento 10 bolsas", Bs 650, material, partida "Losa 2do piso", foto del comprobante, marcar
  "sin factura". Menos de 15 segundos.
- *+ Avance*: losa al 35 %.
- *Cierre del día*: total de hoy y acumulado.

**Paso 5 — Vuelve al dueño (30 s).** Refrescar el detalle de la obra: el gasto de hoy ya está y el avance de
la losa subió. *Alertas*: "No se cerró el día de ayer" y las partidas en rojo.

**Paso 6 — Cierre (30 s).** "Esto es lo que ves cada noche, sin pedirle cuentas a nadie." Mostrar
*Cuenta → Equipo*: así das de alta a tu encargado con su celular y un PIN, y solo ve sus obras.

## 4. Preguntas para el constructor (lo más valioso de la demo)

1. ¿Cómo controlas hoy lo que se gasta en obra? ¿Cuánto de eso no tiene factura?
2. ¿Tu maestro de obra usaría esto todos los días? ¿Qué lo frenaría?
3. ¿El presupuesto lo armas por partidas? ¿En Excel, en un programa, en papel?
4. ¿Cuánto pagarías al mes por esto? ¿Por obra o por empresa?
5. ¿Tienes un plano en DXF (AutoCAD) de una obra real que nos puedas prestar para probar la estimación?

## 5. Qué no mostrar todavía

- **Estimar desde plano**: decir "próximamente". Aún no se probó con un plano real y los rendimientos del
  catálogo son ilustrativos.
- **Costos de mano de obra y materiales del cronograma**: la obra demo no los tiene cargados (verás Bs 0), y
  todavía no se conectan con el gasto real.
- **Instalar como app**: sin HTTPS (en la red local) el celular no ofrece "instalar". Se usa desde el navegador.
