import { bs, fechaCorta } from "../formato";
import type { Hito, PuntoCurva } from "../tipos";

const ANCHO = 640;
const ALTO = 260;
const M = { arriba: 16, derecha: 16, abajo: 32, izquierda: 64 };

/** Curva acumulada: planificado (PV), ganado (EV) y gastado (AC). */
export function Curva({ puntos, hitos, corte }: { puntos: PuntoCurva[]; hitos: Hito[]; corte: string }) {
  if (puntos.length < 2) return <p className="text-sm text-stone-500">Faltan datos para dibujar la curva.</p>;

  const tiempo = (iso: string) => new Date(iso + "T00:00:00").getTime();
  const t0 = tiempo(puntos[0].fecha);
  const t1 = tiempo(puntos[puntos.length - 1].fecha);
  const maximo = Math.max(1, ...puntos.flatMap((p) => [p.pv, p.ev ?? 0, p.ac ?? 0])) * 1.08;
  const x = (iso: string) => M.izquierda + ((tiempo(iso) - t0) / Math.max(1, t1 - t0)) * (ANCHO - M.izquierda - M.derecha);
  const y = (v: number) => ALTO - M.abajo - (v / maximo) * (ALTO - M.arriba - M.abajo);

  const linea = (clave: "pv" | "ev" | "ac") =>
    puntos
      .filter((p) => p[clave] !== null)
      .map((p, i) => `${i === 0 ? "M" : "L"}${x(p.fecha).toFixed(1)},${y(p[clave] as number).toFixed(1)}`)
      .join(" ");

  const marcas = [0, 0.25, 0.5, 0.75, 1].map((f) => (maximo / 1.08) * f);
  const etiquetasX = puntos.filter((_, i) => i % Math.ceil(puntos.length / 6) === 0);

  return (
    <div>
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="h-auto w-full" role="img" aria-label="Curva de avance y gasto">
        {marcas.map((v) => (
          <g key={v}>
            <line x1={M.izquierda} x2={ANCHO - M.derecha} y1={y(v)} y2={y(v)} className="stroke-stone-200" />
            <text x={M.izquierda - 6} y={y(v) + 4} textAnchor="end" className="fill-stone-500 text-[11px]">
              {Math.round(v / 1000)}k
            </text>
          </g>
        ))}
        {etiquetasX.map((p) => (
          <text key={p.fecha} x={x(p.fecha)} y={ALTO - 10} textAnchor="middle" className="fill-stone-500 text-[11px]">
            {fechaCorta(p.fecha)}
          </text>
        ))}
        {hitos.map((h) =>
          tiempo(h.fecha_prevista) >= t0 && tiempo(h.fecha_prevista) <= t1 ? (
            <g key={h.id}>
              <line
                x1={x(h.fecha_prevista)}
                x2={x(h.fecha_prevista)}
                y1={M.arriba}
                y2={ALTO - M.abajo}
                className="stroke-sky-300"
                strokeDasharray="2 4"
              />
              <title>{h.nombre}</title>
            </g>
          ) : null,
        )}
        <line
          x1={x(corte)}
          x2={x(corte)}
          y1={M.arriba}
          y2={ALTO - M.abajo}
          className="stroke-stone-400"
          strokeDasharray="4 4"
        />
        <path d={linea("pv")} fill="none" className="stroke-stone-500" strokeWidth={2} strokeDasharray="6 4" />
        <path d={linea("ev")} fill="none" className="stroke-green-600" strokeWidth={3} />
        <path d={linea("ac")} fill="none" className="stroke-red-600" strokeWidth={3} />
      </svg>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-600">
        <span>
          <span className="mr-1 inline-block w-4 border-t-2 border-dashed border-stone-500 align-middle" />
          Debería (plan): {bs(puntos.find((p) => p.fecha === corte)?.pv)}
        </span>
        <span>
          <span className="mr-1 inline-block w-4 border-t-[3px] border-green-600 align-middle" />
          Avanzado (valor ganado)
        </span>
        <span>
          <span className="mr-1 inline-block w-4 border-t-[3px] border-red-600 align-middle" />
          Gastado
        </span>
        {hitos.length > 0 && (
          <span>
            <span className="mr-1 inline-block w-4 border-t-2 border-dotted border-sky-400 align-middle" />
            Hitos
          </span>
        )}
      </div>
    </div>
  );
}
