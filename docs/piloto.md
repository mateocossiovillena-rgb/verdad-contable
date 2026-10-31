# Piloto: puesta en marcha con un constructor

Dirección de la app: **https://verdad-contable.onrender.com** (Render → servicio verdad-contable).

## 1. Crear la cuenta del dueño

Lo hace el constructor (o tú con él), desde el celular o la computadora:

1. Abrir la dirección de la app.
2. En la pantalla de ingreso, tocar **Crear cuenta**.
3. Llenar **Tu nombre o el de tu empresa**, **Correo** y **Clave** (mínimo 8 caracteres).
4. **Crear cuenta**. Queda dentro de la app, en **Obras**.

Si el dueño olvida su clave (todavía no hay recuperación por correo): Render → servicio verdad-contable →
**Shell** → `python -m app.cambiar_clave correo@del.dueno`. Imprime una clave temporal de 10 letras para
pasársela por un canal privado.

Cada dueño ve solo sus obras. No hay usuarios demo en producción: `python -m app.datos_demo` se niega a
correr con `ENTORNO=produccion`.

## 2. Crear la obra

1. **Obras → Nueva obra**.
2. **Nombre de la obra**, **Cliente**, **Ubicación**, **Fecha de inicio**, **Moneda** (Bs o USD) y, si lo
   tiene, **Presupuesto total**.
3. Guardar. Dentro de la obra, en **Cronograma**, cargar fases y actividades (a mano o con **Estimar desde
   plano**). Cada actividad con fechas y costo alimenta el semáforo de la pestaña **Resumen**.

## 3. Crear al encargado (maestro de obra) con PIN

1. **Cuenta → Equipo: encargados de obra → Nuevo encargado**.
2. **Nombre**, **Celular** (el mismo número con el que va a entrar) y **PIN** de 6 números.
3. Marcar las obras que puede ver y guardar.
4. Pasarle al encargado la dirección de la app, su celular y su PIN. Entra con **Correo o número de
   celular** = su celular y **Clave o PIN** = el PIN.

Si olvida el PIN: Equipo → lápiz junto a su nombre → **PIN nuevo**. Para quitarle el acceso, desde el mismo
lugar. Tras 5 intentos fallidos la cuenta se bloquea 15 minutos.

## 4. Instalar la app en el celular (PWA)

No pasa por Play Store ni App Store; se instala desde el navegador.

**Android (Chrome):**
1. Abrir la dirección de la app en Chrome.
2. Menú ⋮ → **Instalar aplicación** (o **Agregar a la pantalla principal**).
3. Aparece el ícono de Verdad Contable junto a las demás apps.

**iPhone (Safari; en Chrome de iPhone no se puede):**
1. Abrir la dirección en Safari.
2. Botón **Compartir** (cuadro con flecha) → **Agregar a inicio** → **Agregar**.

Sin señal, los gastos y avances quedan en cola en el celular y se envían solos al volver la conexión.
No hay que cerrar sesión: dura 30 días.

## 5. Respaldos

- GitHub Actions (`.github/workflows/respaldo.yml`) saca un `pg_dump` de la base de producción todos los
  días a las 03:00 (Bolivia), **lo restaura en una base vacía para comprobarlo** y lo guarda 30 días en
  la pestaña Actions del repo. Si falla, GitHub manda un correo.
- Sacar uno a mano: GitHub → Actions → Respaldo → **Run workflow**.
- Restaurar (necesita `gh` y `pg_restore` o Docker):

  ```bash
  scripts/restaurar.sh --bajar                    # baja el último respaldo a respaldos/
  scripts/restaurar.sh respaldos/<archivo>.dump "<External Database URL de Render>"
  ```

  Pide escribir RESTAURAR porque borra lo que haya en la base destino. Conviene probar primero contra una
  base nueva y recién después contra producción.
- Las fotos de comprobantes viven en el disco de Render (`/data`), que sobrevive a cada publicación. Render
  le saca una foto (snapshot) al disco cada día y la guarda 7 días; se restaura desde el panel del servicio
  → Disks. Pendiente: pasar las fotos a R2.
