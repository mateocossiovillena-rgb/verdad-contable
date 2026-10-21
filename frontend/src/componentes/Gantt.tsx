import type { ReactNode } from "react";
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

/** Píxeles por día según lo largo de la obra, para que entre en pantalla sin quedar diminuto. */
function anchoDia(totalDias: number): number {
  if (totalDias <= 21) return 32;
  if (totalDias <= 60) return 18;
  if (totalDias <= 150) return 10;
  return 6;
}

/** Línea de tiempo: una barra por actividad, agrupadas por fase, con la marca de hoy. */
export function Gantt({ cronograma }: { cronograma: Cronograma }) {
  const actividades = cronograma.fases.flatMap((f) => f.actividades);
  if (actividades.length === 0) {
    return <p className="text-sm text-stone-500">Agrega actividades para ver la línea de tiempo.</p>;
  }

  const hoy = dia(cronograma.hoy);
  let inicio = dia(cronograma.fecha_inicio);
  let fin = Math.max(dia(cronograma.fecha_fin), inicio);
  // Si hoy cae cerca del cronograma, se estira el eje para mostrarlo.
  if (hoy < inicio && inicio - hoy <= 14) inicio = hoy;
  if (hoy > fin && hoy - fin <= 14) fin = hoy;
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

          {cronograma.fases.map((fase) => {
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
                      <span className="block truncate pl-3 text-stone-700" title={a.nombre}>
                        {a.nombre}
                      </span>
                    }
                    anchoEje={anchoEje}
                  >
                    <Barra actividad={a} izquierda={x(dia(a.fecha_inicio))} ancho={a.duracion_dias * w} nombres={nombres} />
                  </Fila>
                ))}
              </div>
            );
          })}

          {hoyVisible && (
            <div
              className="pointer-events-none absolute bottom-0 top-0 z-10 w-0.5 bg-red-600"
              style={{ left: ANCHO_ETIQUETA + x(hoy) + w / 2 }}
            >
              <span className="absolute left-1 top-1 rounded bg-red-600 px-1 text-[10px] font-semibold text-white">
                Hoy
              </span>
            </div>
          )}
        </div>
      </div>
      <p className="mt-2 text-xs text-stone-500">
        {fecha(cronograma.fecha_inicio)} – {fecha(cronograma.fecha_fin)}
        {!hoyVisible && ` · Hoy (${fecha(cronograma.hoy)}) está fuera de las fechas de la obra`}
      </p>
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
}: {
  actividad: Actividad;
  izquierda: number;
  ancho: number;
  nombres: Map<number, string>;
}) {
  const despues = a.predecesoras.map((p) => nombres.get(p)).filter(Boolean);
  const detalle =
    `${a.nombre}: ${fecha(a.fecha_inicio)} – ${fecha(a.fecha_fin)} (${a.duracion_dias} d)` +
    (despues.length ? `\nDespués de: ${despues.join(", ")}` : "");
  return (
    <div
      className="absolute top-1/2 flex h-5 -translate-y-1/2 items-center overflow-hidden rounded bg-marca-500 px-1 text-[11px] font-medium text-white"
      style={{ left: izquierda, width: Math.max(ancho, 4) }}
      title={detalle}
    >
      {ancho >= 32 && `${a.duracion_dias} d`}
    </div>
  );
}
