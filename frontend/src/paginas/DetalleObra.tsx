import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { dinero, fecha, indice, leerMonto, pct } from "../formato";
import type { Actividad, Cronograma, Fase, IndicadoresObra, Recurso, TipoRecurso } from "../tipos";
import { Curva } from "../componentes/Curva";
import { Gantt } from "../componentes/Gantt";
import { Marco } from "../componentes/Marco";
import {
  IconoAbajo,
  IconoAdelante,
  IconoArriba,
  IconoBasura,
  IconoCerrar,
  IconoCierre,
  IconoLadrillos,
  IconoLapiz,
  IconoMas,
  IconoRecibo,
} from "../componentes/iconos";
import {
  Boton,
  BotonEnlace,
  BotonIcono,
  Campo,
  Cargando,
  Entrada,
  MensajeError,
  Metrica,
  Pestanas,
  Pildora,
  PildoraSemaforo,
  Selector,
  Tarjeta,
  TONO_SEMAFORO,
  type Tono,
} from "../componentes/ui";
import { useIndicadores } from "./Partidas";

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

type Vista = "resumen" | "cronograma";

/** Página de la obra: resumen de valor ganado y cronograma con fases y actividades. */
export function DetalleObra() {
  const { obraId } = useParams();
  const [parametros, setParametros] = useSearchParams();
  const vista: Vista = parametros.get("vista") === "cronograma" ? "cronograma" : "resumen";
  const cronograma = useCronograma(obraId);
  const c = cronograma.data;

  return (
    <Marco
      titulo={c?.obra.nombre ?? "Obra"}
      volver="/obras"
      ancho
      accion={
        <Link
          to={`/obras/${obraId}/editar`}
          className="flex h-10 w-10 items-center justify-center rounded-lg text-stone-700 hover:bg-stone-100"
          aria-label="Editar obra"
          title="Editar obra"
        >
          <IconoLapiz />
        </Link>
      }
    >
      <Pestanas<Vista>
        opciones={[
          { valor: "resumen", texto: "Resumen" },
          { valor: "cronograma", texto: "Cronograma" },
        ]}
        activa={vista}
        cambiar={(v) => setParametros(v === "resumen" ? {} : { vista: v }, { replace: true })}
      />
      {vista === "resumen" ? (
        <Resumen obraId={obraId!} />
      ) : (
        <>
          {cronograma.isLoading && <Cargando />}
          <MensajeError error={cronograma.error} reintentar={() => cronograma.refetch()} />
          {c && (
            <>
              <Tarjeta>
                <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3">
                  <Dato titulo="Cliente" valor={c.obra.cliente || "—"} />
                  <Dato titulo="Ubicación" valor={c.obra.ubicacion || "—"} />
                  <Dato titulo="Moneda" valor={c.obra.moneda} />
                  <Dato titulo="Inicio" valor={fecha(c.obra.fecha_inicio)} />
                  <Dato titulo="Fin según cronograma" valor={fecha(c.obra.fecha_fin)} />
                  <Dato titulo="Presupuesto total" valor={dinero(c.obra.presupuesto_total, c.obra.moneda)} />
                  <Dato titulo="Mano de obra (actividades)" valor={dinero(c.costo_mano_obra, c.obra.moneda)} />
                  <Dato titulo="Materiales (actividades)" valor={dinero(c.costo_materiales, c.obra.moneda)} />
                  <Dato titulo="Costo total de actividades" valor={dinero(c.costo_total, c.obra.moneda)} />
                  <p className="col-span-full text-xs text-stone-600">
                    Cada actividad es también una partida: ahí el encargado registra sus gastos y su avance.
                  </p>
                </div>
              </Tarjeta>

              <Tarjeta className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0 flex-1 basis-60">
                  <h2 className="font-semibold text-stone-900">Estimar desde plano</h2>
                  <p className="text-sm text-stone-600">
                    Sube el plano CAD (DXF) o BIM (IFC) y calcula las cantidades de la obra.
                  </p>
                </div>
                <BotonEnlace a={`/obras/${obraId}/estimar`} variante="secundario">
                  Subir plano
                </BotonEnlace>
              </Tarjeta>

              <Tarjeta>
                <h2 className="mb-3 font-semibold text-stone-900">Línea de tiempo</h2>
                <Gantt cronograma={c} />
              </Tarjeta>

              <h2 className="pt-2 text-lg font-semibold tracking-tight text-stone-900">Fases y actividades</h2>
              {c.fases.map((f, i) => (
                <TarjetaFase key={f.id} obraId={obraId!} cronograma={c} fase={f} posicion={i} />
              ))}
              <NuevaFase obraId={obraId!} existentes={c.fases.map((f) => f.nombre)} />
            </>
          )}
        </>
      )}
    </Marco>
  );
}

/** Tono de un índice (SPI o CPI) con los mismos umbrales de alerta de la obra. */
function tonoIndice(valor: number | null, d: IndicadoresObra): Tono {
  if (valor === null) return "neutro";
  if (valor < d.obra.umbral_rojo) return "problema";
  if (valor < d.obra.umbral_amarillo) return "atencion";
  return "bien";
}

const TEXTO_TONO: Record<Tono, string> = { bien: "Bien", atencion: "Atención", problema: "Problema", neutro: "Sin datos" };

/** Responde en una frase y con tres cifras: ¿voy atrasado?, ¿cuánto gasté?, ¿cuánto costará al final? */
function Resumen({ obraId }: { obraId: string }) {
  const datos = useIndicadores(obraId);
  const d = datos.data;
  if (datos.isLoading) return <Cargando filas={3} />;
  if (!d) return <MensajeError error={datos.error} reintentar={() => datos.refetch()} />;

  const i = d.indicadores;
  const m = d.obra.moneda;
  const tono = TONO_SEMAFORO[d.semaforo];
  const borde: Record<Tono, string> = {
    bien: "border-l-emerald-600",
    atencion: "border-l-amber-500",
    problema: "border-l-red-600",
    neutro: "border-l-stone-300",
  };
  const indices: { sigla: string; valor: string; tono: Tono; explicacion: string }[] = [
    {
      sigla: "SPI",
      valor: indice(i.spi),
      tono: tonoIndice(i.spi, d),
      explicacion: "Cronograma: menos de 1 = vas atrasado.",
    },
    {
      sigla: "CPI",
      valor: indice(i.cpi),
      tono: tonoIndice(i.cpi, d),
      explicacion: "Costo: menos de 1 = gastas más de lo que avanzas.",
    },
    {
      sigla: "SV",
      valor: dinero(i.sv, m),
      tono: i.pv === 0 ? "neutro" : i.sv < 0 ? "atencion" : "bien",
      explicacion: "Lo avanzado menos lo planificado, en dinero.",
    },
    {
      sigla: "CV",
      valor: dinero(i.cv, m),
      tono: i.ac === 0 ? "neutro" : i.cv < 0 ? "atencion" : "bien",
      explicacion: "Lo avanzado menos lo gastado, en dinero.",
    },
  ];

  return (
    <div className="space-y-4 lg:grid lg:grid-cols-5 lg:gap-4 lg:space-y-0">
      <div className="space-y-4 lg:col-span-3">
        <Tarjeta className={`space-y-2 border-l-4 ${borde[tono]}`}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm tabular-nums text-stone-600">Al {fecha(d.corte)}</span>
            <PildoraSemaforo valor={d.semaforo} />
          </div>
          <p className="text-base leading-relaxed text-stone-900">{d.frases.join(" ")}</p>
          {d.advertencias.map((a) => (
            <p key={a.codigo} className="text-sm text-amber-800">
              {a.mensaje}
            </p>
          ))}
        </Tarjeta>

        <Tarjeta className="grid gap-4 sm:grid-cols-3">
          <Metrica
            etiqueta="Avance real"
            valor={pct(i.avance_real)}
            detalle={`Debería: ${pct(i.avance_planificado)} · Según lo gastado: ${pct(i.avance_esperado_por_gasto)}`}
          />
          <Metrica etiqueta="Gastado" valor={dinero(i.ac, m)} detalle={`de ${dinero(i.bac, m)} presupuestado`} />
          <Metrica
            etiqueta="Costo final estimado"
            valor={dinero(i.eac, m)}
            detalle={
              i.eac !== null && i.bac > 0
                ? i.eac > i.bac
                  ? `${dinero(i.eac - i.bac, m)} sobre el presupuesto`
                  : "Dentro del presupuesto"
                : "Falta avance o gasto para estimar"
            }
          />
        </Tarjeta>

        <Tarjeta>
          <h2 className="mb-3 font-semibold text-stone-900">Curva de avance y gasto</h2>
          <Curva puntos={d.curva} hitos={d.hitos} corte={d.corte} />
        </Tarjeta>
      </div>

      <div className="space-y-4 lg:col-span-2">
        <div className="grid grid-cols-2 gap-3">
          <BotonEnlace a={`/obras/${obraId}/hoy`} className="col-span-2">
            <IconoCierre />
            Registro de hoy
          </BotonEnlace>
          <BotonEnlace a={`/obras/${obraId}/partidas`} variante="secundario">
            <IconoLadrillos />
            Partidas
          </BotonEnlace>
          <BotonEnlace a={`/obras/${obraId}/gastos`} variante="secundario">
            <IconoRecibo />
            Gastos
          </BotonEnlace>
        </div>

        <Tarjeta className="p-0">
          <h2 className="px-4 pb-1 pt-4 font-semibold text-stone-900">Índices de valor ganado</h2>
          <ul className="divide-y divide-stone-100">
            {indices.map((x) => (
              <li key={x.sigla} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-stone-900">{x.sigla}</div>
                  <div className="text-sm text-stone-600">{x.explicacion}</div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <span className="font-semibold tabular-nums text-stone-900">{x.valor}</span>
                  <Pildora tono={x.tono}>{TEXTO_TONO[x.tono]}</Pildora>
                </div>
              </li>
            ))}
          </ul>
        </Tarjeta>

        {d.partidas.length > 0 && (
          <Tarjeta className="p-0">
            <div className="flex items-center justify-between px-4 pb-1 pt-4">
              <h2 className="font-semibold text-stone-900">Partidas</h2>
              <Link to={`/obras/${obraId}/partidas`} className="inline-flex items-center gap-1 text-sm font-medium text-stone-700 hover:text-stone-900">
                Ver todas <IconoAdelante tamano={16} />
              </Link>
            </div>
            <ul className="divide-y divide-stone-100">
              {d.partidas
                .filter((p) => !p.partida.es_generales)
                .slice(0, 6)
                .map((p) => (
                  <li key={p.partida.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                    <span className="min-w-0 truncate text-sm text-stone-800">{p.partida.nombre}</span>
                    <span className="flex shrink-0 items-center gap-2">
                      <span className="text-sm tabular-nums text-stone-700">{Math.round(p.porcentaje_avance)} %</span>
                      <PildoraSemaforo valor={p.semaforo} />
                    </span>
                  </li>
                ))}
            </ul>
          </Tarjeta>
        )}
      </div>
    </div>
  );
}

function Dato({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div className="min-w-0">
      <div className="text-stone-600">{titulo}</div>
      <div className="truncate font-medium tabular-nums text-stone-900">{valor}</div>
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
          <IconoMas tamano={18} />
          Fase
        </Boton>
      </form>
      {existentes.length === 0 && sugeridas.length > 0 && (
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="text-stone-600">Sugeridas:</span>
          {sugeridas.map((s) => (
            <button
              key={s}
              type="button"
              className="min-h-10 rounded-full border border-stone-300 bg-white px-3 font-medium text-stone-800 hover:bg-stone-50"
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
          <BotonIcono titulo="Cancelar" onClick={() => setRenombrando(false)} className="h-12 w-12">
            <IconoCerrar />
          </BotonIcono>
        </form>
      ) : (
        <div className="flex items-center gap-1">
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-semibold text-stone-900">{fase.nombre}</h3>
            {fase.costo_total > 0 && (
              <div className="text-sm tabular-nums text-stone-600">{dinero(fase.costo_total, cronograma.obra.moneda)}</div>
            )}
          </div>
          <BotonIcono titulo="Subir" onClick={() => mover(-1)} disabled={posicion === 0 || cambio.isPending}>
            <IconoArriba />
          </BotonIcono>
          <BotonIcono titulo="Bajar" onClick={() => mover(1)} disabled={posicion === ids.length - 1 || cambio.isPending}>
            <IconoAbajo />
          </BotonIcono>
          <BotonIcono
            titulo="Renombrar"
            onClick={() => {
              setNombre(fase.nombre);
              setRenombrando(true);
            }}
          >
            <IconoLapiz tamano={18} />
          </BotonIcono>
          <BotonIcono titulo="Borrar fase" onClick={() => setConfirmarBorrar(true)}>
            <IconoBasura tamano={18} />
          </BotonIcono>
        </div>
      )}

      {confirmarBorrar && (
        <div className="space-y-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-900">
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
        <p className="text-sm text-stone-600">Sin actividades todavía.</p>
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
          <IconoMas tamano={18} />
          Actividad
        </Boton>
      )}
    </Tarjeta>
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
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate font-medium text-stone-900">{a.nombre}</span>
          {a.critica && <Pildora tono="problema">Ruta crítica</Pildora>}
        </div>
        <div className="text-sm tabular-nums text-stone-600">
          {a.duracion_dias} día(s) · {fecha(a.fecha_inicio)} – {fecha(a.fecha_fin)}
          {!a.critica && a.holgura_dias > 0 && ` · puede atrasarse ${a.holgura_dias} día(s)`}
        </div>
        {a.predecesoras.length > 0 && (
          <div className="truncate text-sm text-stone-600">
            Después de: {a.predecesoras.map((p) => nombres.get(p)).join(", ")}
          </div>
        )}
        {a.costo_total > 0 && (
          <div className="text-sm tabular-nums text-stone-600">
            M. obra {dinero(a.costo_mano_obra, cronograma.obra.moneda)} · Materiales{" "}
            {dinero(a.costo_materiales, cronograma.obra.moneda)} ·{" "}
            <span className="font-semibold text-stone-900">{dinero(a.costo_total, cronograma.obra.moneda)}</span>
          </div>
        )}
      </div>
      <BotonIcono titulo="Editar actividad" onClick={alEditar}>
        <IconoLapiz tamano={18} />
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
  const [recursos, setRecursos] = useState<FilaRecurso[]>(() => (actividad?.recursos ?? []).map(aFila));
  const dias = Number(duracion) || 0;

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
      recursos: recursos.map((r) => ({
        tipo: r.tipo,
        descripcion: r.descripcion,
        unidad: r.unidad,
        cantidad: leerMonto(r.cantidad),
        precio_unitario: leerMonto(r.precio_unitario),
        por_dia: r.por_dia,
      })),
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
    <form onSubmit={enviar} className="space-y-3 rounded-xl border border-stone-200 bg-stone-50 p-3">
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
          <legend className="mb-1 text-sm font-medium text-stone-800">Empieza después de (predecesoras)</legend>
          <div className="max-h-48 space-y-2 overflow-y-auto rounded-xl border border-stone-200 bg-white p-2">
            {opciones.map((g) => (
              <div key={g.fase.id}>
                <div className="text-xs font-semibold uppercase tracking-wide text-stone-500">{g.fase.nombre}</div>
                {g.actividades.map((a) => (
                  <label key={a.id} className="flex min-h-10 items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="h-5 w-5 accent-marca-600"
                      checked={predecesoras.includes(a.id)}
                      onChange={() => alternar(a.id)}
                    />
                    <span className="flex-1 truncate">{a.nombre}</span>
                    <span className="text-xs tabular-nums text-stone-500">termina {fecha(a.fecha_fin)}</span>
                  </label>
                ))}
              </div>
            ))}
          </div>
          {predecesoras.length > 0 && (
            <p className="mt-1 text-xs text-stone-600">
              El inicio se calcula solo: el día después de que termine la última predecesora.
            </p>
          )}
        </fieldset>
      )}
      <SeccionRecursos tipo="mano_obra" filas={recursos} cambiar={setRecursos} dias={dias} moneda={cronograma.obra.moneda} />
      <SeccionRecursos tipo="material" filas={recursos} cambiar={setRecursos} dias={dias} moneda={cronograma.obra.moneda} />
      <div className="flex justify-between rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm">
        <span className="text-stone-600">Costo de la actividad</span>
        <span className="font-semibold tabular-nums text-stone-900">
          {dinero(
            recursos.reduce((suma, r) => suma + costoFila(r, dias), 0),
            cronograma.obra.moneda,
          )}
        </span>
      </div>
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
              <IconoBasura tamano={18} />
              Borrar
            </Boton>
          ))}
      </div>
    </form>
  );
}

// --- Mano de obra y materiales de la actividad ---

interface FilaRecurso {
  clave: string;
  tipo: TipoRecurso;
  descripcion: string;
  unidad: string;
  cantidad: string;
  precio_unitario: string;
  por_dia: boolean;
}

let siguienteClave = 0;
const nuevaClave = () => `r${++siguienteClave}`;

function aFila(r: Recurso): FilaRecurso {
  return {
    clave: nuevaClave(),
    tipo: r.tipo,
    descripcion: r.descripcion,
    unidad: r.unidad,
    cantidad: String(r.cantidad),
    precio_unitario: String(r.precio_unitario),
    por_dia: r.por_dia,
  };
}

function filaVacia(tipo: TipoRecurso): FilaRecurso {
  const base = { clave: nuevaClave(), tipo, descripcion: "", unidad: "", precio_unitario: "" };
  // La mano de obra arranca con 1 persona pagada por día (jornal), lo más común en obra.
  return tipo === "mano_obra" ? { ...base, cantidad: "1", por_dia: true } : { ...base, cantidad: "", por_dia: false };
}

/** Lo mismo que calcula el servidor, para mostrar el subtotal mientras se escribe. */
function costoFila(r: FilaRecurso, dias: number): number {
  const cantidad = Number(leerMonto(r.cantidad) ?? 0) || 0;
  const precio = Number(leerMonto(r.precio_unitario) ?? 0) || 0;
  const costo = cantidad * precio * (r.tipo === "mano_obra" && r.por_dia ? dias : 1);
  return Math.round(costo * 100) / 100;
}

function SeccionRecursos({
  tipo,
  filas,
  cambiar,
  dias,
  moneda,
}: {
  tipo: TipoRecurso;
  filas: FilaRecurso[];
  cambiar: (filas: FilaRecurso[]) => void;
  dias: number;
  moneda: string;
}) {
  const propias = filas.filter((f) => f.tipo === tipo);
  const esManoObra = tipo === "mano_obra";
  const actualizar = (clave: string, cambios: Partial<FilaRecurso>) =>
    cambiar(filas.map((f) => (f.clave === clave ? { ...f, ...cambios } : f)));
  const subtotal = propias.reduce((suma, f) => suma + costoFila(f, dias), 0);

  return (
    <fieldset className="space-y-2">
      <legend className="mb-1 flex w-full justify-between text-sm font-medium text-stone-800">
        <span>{esManoObra ? "Mano de obra" : "Materiales"}</span>
        {propias.length > 0 && <span className="tabular-nums text-stone-600">{dinero(subtotal, moneda)}</span>}
      </legend>
      {propias.map((f) => (
        <div key={f.clave} className="space-y-2 rounded-xl border border-stone-200 bg-white p-2">
          <div className="flex gap-2">
            <Entrada
              value={f.descripcion}
              onChange={(e) => actualizar(f.clave, { descripcion: e.target.value })}
              placeholder={esManoObra ? "Cargo (ej. Albañil)" : "Material (ej. Cemento)"}
              aria-label={esManoObra ? "Cargo" : "Material"}
              required
            />
            <BotonIcono titulo="Quitar" onClick={() => cambiar(filas.filter((x) => x.clave !== f.clave))} className="h-12 w-12">
              <IconoCerrar />
            </BotonIcono>
          </div>
          {esManoObra ? (
            <div className="grid grid-cols-2 gap-2">
              <Campo etiqueta="Personas">
                <Entrada
                  type="number"
                  inputMode="numeric"
                  min={1}
                  step={1}
                  value={f.cantidad}
                  onChange={(e) => actualizar(f.clave, { cantidad: e.target.value })}
                  required
                />
              </Campo>
              <Campo etiqueta="Costo por persona">
                <Entrada
                  inputMode="decimal"
                  value={f.precio_unitario}
                  onChange={(e) => actualizar(f.clave, { precio_unitario: e.target.value })}
                  placeholder="0,00"
                  required
                />
              </Campo>
              <Campo etiqueta="Se paga (jornal o destajo)">
                <Selector
                  value={f.por_dia ? "dia" : "total"}
                  onChange={(e) => actualizar(f.clave, { por_dia: e.target.value === "dia" })}
                >
                  <option value="dia">Por día</option>
                  <option value="total">Por la actividad</option>
                </Selector>
              </Campo>
              <Subtotal valor={costoFila(f, dias)} moneda={moneda} detalle={f.por_dia ? `× ${dias} día(s)` : undefined} />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <Campo etiqueta="Cantidad">
                <Entrada
                  inputMode="decimal"
                  value={f.cantidad}
                  onChange={(e) => actualizar(f.clave, { cantidad: e.target.value })}
                  placeholder="0"
                  required
                />
              </Campo>
              <Campo etiqueta="Unidad">
                <Entrada
                  value={f.unidad}
                  onChange={(e) => actualizar(f.clave, { unidad: e.target.value })}
                  placeholder="bolsa, m³…"
                />
              </Campo>
              <Campo etiqueta="Precio unitario">
                <Entrada
                  inputMode="decimal"
                  value={f.precio_unitario}
                  onChange={(e) => actualizar(f.clave, { precio_unitario: e.target.value })}
                  placeholder="0,00"
                  required
                />
              </Campo>
              <Subtotal valor={costoFila(f, dias)} moneda={moneda} />
            </div>
          )}
        </div>
      ))}
      <Boton type="button" variante="secundario" className="w-full" onClick={() => cambiar([...filas, filaVacia(tipo)])}>
        <IconoMas tamano={18} />
        {esManoObra ? "Agregar mano de obra" : "Agregar material"}
      </Boton>
    </fieldset>
  );
}

function Subtotal({ valor, moneda, detalle }: { valor: number; moneda: string; detalle?: string }) {
  return (
    <div className="flex flex-col justify-end text-right">
      <span className="text-xs text-stone-600">Subtotal{detalle && ` ${detalle}`}</span>
      <span className="flex min-h-12 items-center justify-end font-semibold tabular-nums text-stone-900">{dinero(valor, moneda)}</span>
    </div>
  );
}
