import { useState, type ReactNode } from "react";
import { fecha, fechaCorta } from "../formato";
import type { Actividad, Cronograma } from "../tipos";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const ANCHO_ETIQUETA = 144; // px, columna fija con los nombres
const ALTO_FILA = 36;

/** Días desde 1970 de una fecha ISO, sin líos de zona horaria. */
function dia(iso: string): number {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return Date.UTC(a, m - 1, d) / 86_400_000;
}

function iso(dias: number): string {
  return new Date(dias * 86_400_000).toISOString().slice(0, 10);
}

// Estado de cada actividad según la fecha de hoy (el avance físico se registra por partida, no por actividad).
type EstadoActividad = "terminada" | "en_curso" | "pendiente";
const COLOR_ESTADO: Record<EstadoActividad, string> = {
  terminada: "bg-stone-400",
  en_curso: "bg-stone-800",
  pendiente: "bg-stone-200 ring-1 ring-inset ring-stone-300",
};
// La ruta crítica va en rojo: si una de esas actividades se atrasa, se atrasa la entrega.
const COLOR_CRITICA: Record<EstadoActividad, string> = {
  terminada: "bg-red-300",
  en_curso: "bg-red-700",
  pendiente: "bg-red-50 ring-1 ring-inset ring-red-400",
};
const TEXTO_ESTADO: Record<EstadoActividad, string> = {
  terminada: "Ya debió terminar",
  en_curso: "En curso",
  pendiente: "Por empezar",
};

function estadoPorFecha(a: Actividad, hoy: number): EstadoActividad {
  if (dia(a.fecha_fin) < hoy) return "terminada";
  if (dia(a.fecha_inicio) <= hoy) return "en_curso";
  return "pendiente";
}

/** Píxeles por día según lo largo de la obra, para que entre en pantalla sin quedar diminuto. */
function anchoDia(totalDias: number): number {
  if (totalDias <= 21) return 32;
  if (totalDias <= 60) return 18;
  if (totalDias <= 150) return 10;
  return 6;
}

function textoHolgura(dias: number): string {
  if (dias === 0) return "Ruta crítica: si se atrasa, se atrasa la entrega";
  return `Puede atrasarse ${dias} ${dias === 1 ? "día" : "días"} sin mover la entrega`;
}

/**
 * Línea de tiempo: una barra por actividad, agrupadas por fase, con la marca de hoy, la ruta crítica en
 * rojo y la holgura como un tramo punteado después de cada barra. `vistaPrevia` es para un cronograma que
 * todavía no existe (sin marca de hoy ni estados).
 */
export function Gantt({
  cronograma,
  vistaPrevia = false,
}: {
  cronograma: Pick<Cronograma, "fases" | "hoy" | "fecha_inicio" | "fecha_fin">;
  vistaPrevia?: boolean;
}) {
  const [soloCriticas, setSoloCriticas] = useState(false);
  const todas = cronograma.fases.flatMap((f) => f.actividades);
  if (todas.length === 0) {
    return <p className="text-sm text-stone-500">Agrega actividades para ver la línea de tiempo.</p>;
  }
  const fases = cronograma.fases
    .map((f) => ({ ...f, actividades: soloCriticas ? f.actividades.filter((a) => a.critica) : f.actividades }))
    .filter((f) => !soloCriticas || f.actividades.length > 0);
  const actividades = todas;
  const criticas = todas.filter((a) => a.critica).length;

  const hoy = vistaPrevia ? Number.NEGATIVE_INFINITY : dia(cronograma.hoy);
  let inicio = dia(cronograma.fecha_inicio);
  let fin = Math.max(dia(cronograma.fecha_fin), inicio);
  // Si hoy cae cerca del cronograma, se estira el eje para mostrarlo.
  if (!vistaPrevia && hoy < inicio && inicio - hoy <= 14) inicio = hoy;
  if (!vistaPrevia && hoy > fin && hoy - fin <= 14) fin = hoy;
  fin += 1; // un día de aire al final

  const total = fin - inicio + 1;
  const w = anchoDia(total);
  const anchoEje = total * w;
  const x = (d: number) => (d - inicio) * w;
  const hoyVisible = hoy >= inicio && hoy <= fin;
  const nombres = new Map(actividades.map((a) => [a.id, a.nombre]));

  // Marcas del eje: cada lunes si hay espacio, si no el primer día de cada mes.
  const marcas: { d: number; texto: string; mes: boolean }[] = [];
  for (let d = inicio; d <= fin; d++) {
    const f = new Date(d * 86_400_000);
    const esMes = f.getUTCDate() === 1;
    if (esMes) marcas.push({ d, texto: `${MESES[f.getUTCMonth()]} ${f.getUTCFullYear() % 100}`, mes: true });
    else if (w >= 10 && f.getUTCDay() === 1) marcas.push({ d, texto: fechaCorta(iso(d)), mes: false });
  }

  return (
    <div>
      {criticas > 0 && (
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-stone-600">
            <span className="font-semibold tabular-nums text-red-700">{criticas}</span> de{" "}
            <span className="tabular-nums">{todas.length}</span> actividades están en la ruta crítica.
          </p>
          <button
            type="button"
            aria-pressed={soloCriticas}
            onClick={() => setSoloCriticas(!soloCriticas)}
            className={`min-h-10 rounded-lg border px-3 text-sm font-medium transition active:scale-[0.98] ${
              soloCriticas ? "border-red-300 bg-red-50 text-red-800" : "border-stone-300 bg-white text-stone-700 hover:bg-stone-50"
            }`}
          >
            {soloCriticas ? "Ver todas" : "Solo ruta crítica"}
          </button>
        </div>
      )}
      <div
        className="overflow-x-auto rounded-xl ring-1 ring-stone-200"
        ref={(el) => {
          // Al abrir, se desplaza para que hoy quede a la vista (solo la primera vez).
          if (el && hoyVisible && !el.dataset.desplazado) {
            el.scrollLeft = Math.max(0, x(hoy) - 3 * w);
            el.dataset.desplazado = "1";
          }
        }}
      >
        <div className="relative" style={{ width: ANCHO_ETIQUETA + anchoEje }}>
          {/* Eje de fechas */}
          <div className="sticky top-0 flex h-8 border-b border-stone-200 bg-stone-50 text-[11px] text-stone-500">
            <div className="sticky left-0 z-20 shrink-0 bg-stone-50" style={{ width: ANCHO_ETIQUETA }} />
            <div className="relative" style={{ width: anchoEje }}>
              {marcas.map((m) => (
                <span
                  key={m.d}
                  className={`absolute top-0 h-full border-l pl-1 leading-8 ${m.mes ? "border-stone-400 font-semibold text-stone-700" : "border-stone-200"}`}
                  style={{ left: x(m.d) }}
                >
                  {m.texto}
                </span>
              ))}
            </div>
          </div>

          {fases.map((fase) => {
            const desde = fase.actividades.length ? Math.min(...fase.actividades.map((a) => dia(a.fecha_inicio))) : null;
            const hasta = fase.actividades.length ? Math.max(...fase.actividades.map((a) => dia(a.fecha_fin))) : null;
            return (
              <div key={fase.id}>
                <Fila etiqueta={<span className="font-semibold text-stone-800">{fase.nombre}</span>} fondo="bg-stone-100" anchoEje={anchoEje}>
                  {desde !== null && hasta !== null && (
                    <div
                      className="absolute top-1/2 h-2 -translate-y-1/2 rounded-sm bg-stone-500"
                      style={{ left: x(desde), width: (hasta - desde + 1) * w }}
                      title={`${fase.nombre}: ${fecha(iso(desde))} – ${fecha(iso(hasta))}`}
                    />
                  )}
                </Fila>
                {fase.actividades.map((a) => (
                  <Fila
                    key={a.id}
                    etiqueta={
                      <span
                        className={`block truncate pl-3 ${a.critica ? "font-medium text-red-800" : "text-stone-700"}`}
                        title={a.nombre}
                      >
                        {a.nombre}
                      </span>
                    }
                    anchoEje={anchoEje}
                  >
                    <Barra
                      actividad={a}
                      izquierda={x(dia(a.fecha_inicio))}
                      ancho={a.duracion_dias * w}
                      nombres={nombres}
                      hoy={hoy}
                      anchoDia={w}
                    />
                  </Fila>
                ))}
              </div>
            );
          })}

          {hoyVisible && (
            <div
              className="pointer-events-none absolute bottom-0 top-0 z-10 w-0.5 bg-marca-600"
              style={{ left: ANCHO_ETIQUETA + x(hoy) + w / 2 }}
            >
              <span className="absolute left-1 top-1 rounded bg-marca-600 px-1 text-[11px] font-semibold text-white">
                Hoy
              </span>
            </div>
          )}
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-stone-600">
        <span className="tabular-nums">
          {fecha(cronograma.fecha_inicio)} – {fecha(cronograma.fecha_fin)}
          {!vistaPrevia && !hoyVisible && ` · Hoy (${fecha(cronograma.hoy)}) está fuera de las fechas de la obra`}
        </span>
        {!vistaPrevia &&
          (["terminada", "en_curso", "pendiente"] as const).map((e) => (
            <span key={e} className="inline-flex items-center gap-1.5">
              <span className={`h-2.5 w-4 rounded-sm ${COLOR_ESTADO[e]}`} />
              {TEXTO_ESTADO[e]}
            </span>
          ))}
        {criticas > 0 && (
          <span className="inline-flex items-center gap-1.5">
            <span className={`h-2.5 w-4 rounded-sm ${vistaPrevia ? COLOR_CRITICA.pendiente : COLOR_CRITICA.en_curso}`} />
            Ruta crítica
          </span>
        )}
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-4 border-y border-r border-dashed border-stone-400" />
          Holgura
        </span>
      </div>
    </div>
  );
}

function Fila({
  etiqueta,
  fondo = "bg-white",
  anchoEje,
  children,
}: {
  etiqueta: ReactNode;
  fondo?: string;
  anchoEje: number;
  children: ReactNode;
}) {
  return (
    <div className={`flex border-b border-stone-100 text-sm ${fondo}`} style={{ height: ALTO_FILA }}>
      <div
        className={`sticky left-0 z-20 flex shrink-0 items-center border-r border-stone-200 px-2 ${fondo}`}
        style={{ width: ANCHO_ETIQUETA }}
      >
        {etiqueta}
      </div>
      <div className="relative" style={{ width: anchoEje }}>
        {children}
      </div>
    </div>
  );
}

function Barra({
  actividad: a,
  izquierda,
  ancho,
  nombres,
  hoy,
  anchoDia,
}: {
  actividad: Actividad;
  izquierda: number;
  ancho: number;
  nombres: Map<number, string>;
  hoy: number;
  anchoDia: number;
}) {
  const despues = a.predecesoras.map((p) => nombres.get(p)).filter(Boolean);
  const estado = estadoPorFecha(a, hoy);
  const colores = a.critica ? COLOR_CRITICA : COLOR_ESTADO;
  const textoPendiente = a.critica ? "text-red-800" : "text-stone-700";
  const detalle =
    `${a.nombre}: ${fecha(a.fecha_inicio)} – ${fecha(a.fecha_fin)} (${a.duracion_dias} d)` +
    (hoy === Number.NEGATIVE_INFINITY ? "" : ` · ${TEXTO_ESTADO[estado]}`) +
    `\n${textoHolgura(a.holgura_dias)}` +
    (despues.length ? `\nDespués de: ${despues.join(", ")}` : "");
  return (
    <>
      <div
        className={`absolute top-1/2 flex h-5 -translate-y-1/2 items-center overflow-hidden rounded px-1 text-[11px] font-medium ${colores[estado]} ${estado === "pendiente" ? textoPendiente : "text-white"}`}
        style={{ left: izquierda, width: Math.max(ancho, 4) }}
        title={detalle}
      >
        {ancho >= 32 && `${a.duracion_dias} d`}
      </div>
      {a.holgura_dias > 0 && (
        <div
          className="absolute top-1/2 h-2 -translate-y-1/2 rounded-r-sm border-y border-r border-dashed border-stone-400"
          style={{ left: izquierda + Math.max(ancho, 4), width: a.holgura_dias * anchoDia }}
          title={textoHolgura(a.holgura_dias)}
        />
      )}
    </>
  );
}
