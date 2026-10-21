import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ButtonHTMLAttributes, type FormEvent, type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { dinero, fecha } from "../formato";
import type { Actividad, Cronograma, Fase } from "../tipos";
import { Gantt } from "../componentes/Gantt";
import { Marco } from "../componentes/Marco";
import { Boton, BotonEnlace, Campo, Cargando, Entrada, MensajeError, Selector, Tarjeta } from "../componentes/ui";

const FASES_SUGERIDAS = ["Obra gruesa", "Instalaciones", "Acabados"];

function useCronograma(obraId: string | undefined) {
  return useQuery({
    queryKey: ["cronograma", obraId],
    queryFn: () => api<Cronograma>(`/api/obras/${obraId}/cronograma`),
  });
}

/** Cada cambio devuelve el cronograma recalculado: se pinta de inmediato sin volver a pedirlo. */
function useCambio(obraId: string | undefined) {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ ruta, metodo, cuerpo }: { ruta: string; metodo: string; cuerpo?: unknown }) =>
      api<Cronograma>(ruta, metodo, cuerpo),
    onSuccess: (c) => {
      cliente.setQueryData(["cronograma", obraId], c);
      cliente.setQueryData(["obra", obraId], c.obra);
      cliente.invalidateQueries({ queryKey: ["obras"] });
    },
  });
}

/** Página de la obra: datos, línea de tiempo y edición de fases y actividades. */
export function DetalleObra() {
  const { obraId } = useParams();
  const cronograma = useCronograma(obraId);
  const c = cronograma.data;

  return (
    <Marco titulo={c?.obra.nombre ?? "Obra"} volver="/obras">
      {cronograma.isLoading && <Cargando />}
      <MensajeError error={cronograma.error} />
      {c && (
        <>
          <Tarjeta className="space-y-2">
            <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              <Dato titulo="Cliente" valor={c.obra.cliente || "—"} />
              <Dato titulo="Ubicación" valor={c.obra.ubicacion || "—"} />
              <Dato titulo="Inicio" valor={fecha(c.obra.fecha_inicio)} />
              <Dato titulo="Fin según cronograma" valor={fecha(c.obra.fecha_fin)} />
              <Dato titulo="Presupuesto total" valor={dinero(c.obra.presupuesto_total, c.obra.moneda)} />
              <Dato titulo="Moneda" valor={c.obra.moneda} />
            </div>
            <div className="flex gap-2 pt-1">
              <BotonEnlace a={`/obras/${obraId}/editar`} variante="secundario" className="flex-1">
                ✏️ Editar obra
              </BotonEnlace>
              <BotonEnlace a={`/obras/${obraId}/hoy`} variante="secundario" className="flex-1">
                📋 Registro de hoy
              </BotonEnlace>
            </div>
          </Tarjeta>

          <Tarjeta>
            <h2 className="mb-3 font-semibold">Línea de tiempo</h2>
            <Gantt cronograma={c} />
          </Tarjeta>

          <h2 className="pt-2 text-lg font-semibold">Fases y actividades</h2>
          {c.fases.map((f, i) => (
            <TarjetaFase key={f.id} obraId={obraId!} cronograma={c} fase={f} posicion={i} />
          ))}
          <NuevaFase obraId={obraId!} existentes={c.fases.map((f) => f.nombre)} />
        </>
      )}
    </Marco>
  );
}

function Dato({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div className="min-w-0">
      <div className="text-stone-500">{titulo}</div>
      <div className="truncate font-medium">{valor}</div>
    </div>
  );
}

function NuevaFase({ obraId, existentes }: { obraId: string; existentes: string[] }) {
  const [nombre, setNombre] = useState("");
  const cambio = useCambio(obraId);
  const crear = (n: string) =>
    cambio.mutate({ ruta: `/api/obras/${obraId}/fases`, metodo: "POST", cuerpo: { nombre: n } }, { onSuccess: () => setNombre("") });
  const sugeridas = FASES_SUGERIDAS.filter((s) => !existentes.includes(s));

  return (
    <Tarjeta className="space-y-3">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (nombre.trim()) crear(nombre.trim());
        }}
      >
        <Entrada value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre de la nueva fase" />
        <Boton type="submit" disabled={cambio.isPending || !nombre.trim()} className="shrink-0">
          + Fase
        </Boton>
      </form>
      {existentes.length === 0 && sugeridas.length > 0 && (
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="text-stone-500">Sugeridas:</span>
          {sugeridas.map((s) => (
            <button
              key={s}
              type="button"
              className="rounded-full bg-marca-50 px-3 py-1 text-marca-700 ring-1 ring-marca-100"
              onClick={() => crear(s)}
              disabled={cambio.isPending}
            >
              + {s}
            </button>
          ))}
        </div>
      )}
      <MensajeError error={cambio.error} />
    </Tarjeta>
  );
}

function TarjetaFase({
  obraId,
  cronograma,
  fase,
  posicion,
}: {
  obraId: string;
  cronograma: Cronograma;
  fase: Fase;
  posicion: number;
}) {
  const cambio = useCambio(obraId);
  const [renombrando, setRenombrando] = useState(false);
  const [nombre, setNombre] = useState(fase.nombre);
  const [confirmarBorrar, setConfirmarBorrar] = useState(false);
  const [formulario, setFormulario] = useState<"nueva" | number | null>(null);
  const ids = cronograma.fases.map((f) => f.id);

  function mover(delta: number) {
    const nuevo = [...ids];
    [nuevo[posicion], nuevo[posicion + delta]] = [nuevo[posicion + delta], nuevo[posicion]];
    cambio.mutate({ ruta: `/api/obras/${obraId}/fases/orden`, metodo: "PUT", cuerpo: { ids: nuevo } });
  }

  function renombrar(e: FormEvent) {
    e.preventDefault();
    cambio.mutate(
      { ruta: `/api/fases/${fase.id}`, metodo: "PUT", cuerpo: { nombre } },
      { onSuccess: () => setRenombrando(false) },
    );
  }

  return (
    <Tarjeta className="space-y-3">
      {renombrando ? (
        <form onSubmit={renombrar} className="flex gap-2">
          <Entrada value={nombre} onChange={(e) => setNombre(e.target.value)} autoFocus required />
          <Boton type="submit" disabled={cambio.isPending} className="shrink-0">
            Guardar
          </Boton>
          <Boton type="button" variante="secundario" onClick={() => setRenombrando(false)} className="shrink-0">
            ✕
          </Boton>
        </form>
      ) : (
        <div className="flex items-center gap-1">
          <h3 className="flex-1 truncate font-semibold">{fase.nombre}</h3>
          <BotonIcono titulo="Subir" onClick={() => mover(-1)} disabled={posicion === 0 || cambio.isPending}>
            ↑
          </BotonIcono>
          <BotonIcono titulo="Bajar" onClick={() => mover(1)} disabled={posicion === ids.length - 1 || cambio.isPending}>
            ↓
          </BotonIcono>
          <BotonIcono
            titulo="Renombrar"
            onClick={() => {
              setNombre(fase.nombre);
              setRenombrando(true);
            }}
          >
            ✏️
          </BotonIcono>
          <BotonIcono titulo="Borrar fase" onClick={() => setConfirmarBorrar(true)}>
            🗑️
          </BotonIcono>
        </div>
      )}

      {confirmarBorrar && (
        <div className="space-y-2 rounded-xl bg-red-50 p-3 text-sm text-red-900 ring-1 ring-red-200">
          <p>
            ¿Borrar la fase «{fase.nombre}»
            {fase.actividades.length > 0 && ` y sus ${fase.actividades.length} actividad(es)`}?
          </p>
          <div className="flex gap-2">
            <Boton
              variante="peligro"
              onClick={() => cambio.mutate({ ruta: `/api/fases/${fase.id}`, metodo: "DELETE" })}
              disabled={cambio.isPending}
            >
              Sí, borrar
            </Boton>
            <Boton variante="secundario" onClick={() => setConfirmarBorrar(false)}>
              Cancelar
            </Boton>
          </div>
        </div>
      )}
      <MensajeError error={cambio.error} />

      {fase.actividades.length === 0 && formulario === null && (
        <p className="text-sm text-stone-500">Sin actividades todavía.</p>
      )}
      <ul className="divide-y divide-stone-100">
        {fase.actividades.map((a) =>
          formulario === a.id ? (
            <li key={a.id} className="py-2">
              <FormActividad
                obraId={obraId}
                cronograma={cronograma}
                faseId={fase.id}
                actividad={a}
                alTerminar={() => setFormulario(null)}
              />
            </li>
          ) : (
            <FilaActividad key={a.id} actividad={a} cronograma={cronograma} alEditar={() => setFormulario(a.id)} />
          ),
        )}
      </ul>
      {formulario === "nueva" ? (
        <FormActividad obraId={obraId} cronograma={cronograma} faseId={fase.id} alTerminar={() => setFormulario(null)} />
      ) : (
        <Boton variante="secundario" className="w-full" onClick={() => setFormulario("nueva")}>
          + Actividad
        </Boton>
      )}
    </Tarjeta>
  );
}

function BotonIcono({
  titulo,
  children,
  ...props
}: { titulo: string; children: ReactNode } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      title={titulo}
      aria-label={titulo}
      className="flex h-9 w-9 items-center justify-center rounded-lg text-stone-600 hover:bg-stone-100 disabled:opacity-30"
      {...props}
    >
      {children}
    </button>
  );
}

function FilaActividad({
  actividad: a,
  cronograma,
  alEditar,
}: {
  actividad: Actividad;
  cronograma: Cronograma;
  alEditar: () => void;
}) {
  const nombres = new Map(cronograma.fases.flatMap((f) => f.actividades).map((x) => [x.id, x.nombre]));
  return (
    <li className="flex items-center gap-2 py-2">
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{a.nombre}</div>
        <div className="text-xs text-stone-500">
          {a.duracion_dias} día(s) · {fecha(a.fecha_inicio)} – {fecha(a.fecha_fin)}
        </div>
        {a.predecesoras.length > 0 && (
          <div className="truncate text-xs text-stone-500">
            Después de: {a.predecesoras.map((p) => nombres.get(p)).join(", ")}
          </div>
        )}
      </div>
      <BotonIcono titulo="Editar actividad" onClick={alEditar}>
        ✏️
      </BotonIcono>
    </li>
  );
}

function FormActividad({
  obraId,
  cronograma,
  faseId,
  actividad,
  alTerminar,
}: {
  obraId: string;
  cronograma: Cronograma;
  faseId: number;
  actividad?: Actividad;
  alTerminar: () => void;
}) {
  const cambio = useCambio(obraId);
  const [nombre, setNombre] = useState(actividad?.nombre ?? "");
  const [duracion, setDuracion] = useState(String(actividad?.duracion_dias ?? 1));
  const [inicio, setInicio] = useState(actividad?.inicio_manual ?? cronograma.obra.fecha_inicio);
  const [predecesoras, setPredecesoras] = useState<number[]>(actividad?.predecesoras ?? []);
  const [fase, setFase] = useState(faseId);
  const [confirmarBorrar, setConfirmarBorrar] = useState(false);

  const alternar = (id: number) =>
    setPredecesoras(predecesoras.includes(id) ? predecesoras.filter((p) => p !== id) : [...predecesoras, id]);

  function enviar(e: FormEvent) {
    e.preventDefault();
    const cuerpo = {
      nombre,
      duracion_dias: Number(duracion),
      inicio_manual: predecesoras.length ? null : inicio || null,
      predecesoras,
      ...(actividad && { fase_id: fase }),
    };
    const pedido = actividad
      ? { ruta: `/api/actividades/${actividad.id}`, metodo: "PUT", cuerpo }
      : { ruta: `/api/fases/${faseId}/actividades`, metodo: "POST", cuerpo };
    cambio.mutate(pedido, { onSuccess: alTerminar });
  }

  const opciones = cronograma.fases
    .map((f) => ({ fase: f, actividades: f.actividades.filter((a) => a.id !== actividad?.id) }))
    .filter((g) => g.actividades.length > 0);

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-xl bg-stone-50 p-3 ring-1 ring-stone-200">
      <Campo etiqueta="Actividad">
        <Entrada value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Muros de ladrillo" required autoFocus />
      </Campo>
      <div className="grid grid-cols-2 gap-3">
        <Campo etiqueta="Duración (días)">
          <Entrada type="number" inputMode="numeric" min={1} value={duracion} onChange={(e) => setDuracion(e.target.value)} required />
        </Campo>
        <Campo etiqueta="Fecha de inicio">
          <Entrada type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} disabled={predecesoras.length > 0} />
        </Campo>
      </div>
      {actividad && cronograma.fases.length > 1 && (
        <Campo etiqueta="Fase">
          <Selector value={fase} onChange={(e) => setFase(Number(e.target.value))}>
            {cronograma.fases.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nombre}
              </option>
            ))}
          </Selector>
        </Campo>
      )}
      {opciones.length > 0 && (
        <fieldset>
          <legend className="mb-1 text-sm font-medium text-stone-700">Empieza después de (predecesoras)</legend>
          <div className="max-h-48 space-y-2 overflow-y-auto rounded-xl bg-white p-2 ring-1 ring-stone-200">
            {opciones.map((g) => (
              <div key={g.fase.id}>
                <div className="text-xs font-semibold uppercase tracking-wide text-stone-400">{g.fase.nombre}</div>
                {g.actividades.map((a) => (
                  <label key={a.id} className="flex min-h-9 items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="h-5 w-5 accent-marca-600"
                      checked={predecesoras.includes(a.id)}
                      onChange={() => alternar(a.id)}
                    />
                    <span className="flex-1 truncate">{a.nombre}</span>
                    <span className="text-xs text-stone-400">termina {fecha(a.fecha_fin)}</span>
                  </label>
                ))}
              </div>
            ))}
          </div>
          {predecesoras.length > 0 && (
            <p className="mt-1 text-xs text-stone-500">
              El inicio se calcula solo: el día después de que termine la última predecesora.
            </p>
          )}
        </fieldset>
      )}
      <MensajeError error={cambio.error} />
      <div className="flex flex-wrap gap-2">
        <Boton type="submit" disabled={cambio.isPending}>
          {cambio.isPending ? "Guardando…" : actividad ? "Guardar" : "Agregar actividad"}
        </Boton>
        <Boton type="button" variante="secundario" onClick={alTerminar}>
          Cancelar
        </Boton>
        {actividad &&
          (confirmarBorrar ? (
            <Boton
              type="button"
              variante="peligro"
              className="ml-auto"
              disabled={cambio.isPending}
              onClick={() => cambio.mutate({ ruta: `/api/actividades/${actividad.id}`, metodo: "DELETE" }, { onSuccess: alTerminar })}
            >
              ¿Seguro? Borrar
            </Boton>
          ) : (
            <Boton type="button" variante="secundario" className="ml-auto" onClick={() => setConfirmarBorrar(true)}>
              🗑️ Borrar
            </Boton>
          ))}
      </div>
    </form>
  );
}
