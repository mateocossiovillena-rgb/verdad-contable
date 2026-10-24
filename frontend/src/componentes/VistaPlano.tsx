import type { PlantaDibujada, Segmento } from "../tipos";

const COLOR_VENTANA = "#0369a1"; // sky-700
const COLOR_PUERTA = "#57534e"; // stone-600

/**
 * Dibujo simple de una planta para confirmar qué se leyó del plano. Las coordenadas vienen en metros con el
 * origen abajo a la izquierda (como en el CAD); el SVG tiene el origen arriba, por eso se invierte y.
 */
export function VistaPlano({
  ancho,
  alto,
  muros,
  planta,
  className = "",
}: {
  ancho: number;
  alto: number;
  muros: Segmento[];
  planta?: PlantaDibujada;
  className?: string;
}) {
  const margen = Math.max(ancho, alto) * 0.04;
  const y = (v: number) => alto - v;
  const letra = Math.max(Math.min(ancho, alto) / 22, 0.18);
  return (
    <svg
      viewBox={`${-margen} ${-margen} ${ancho + 2 * margen} ${alto + 2 * margen}`}
      className={`w-full rounded-xl border border-stone-200 bg-stone-50 ${className}`}
      role="img"
      aria-label={planta ? `Plano de ${planta.nombre}` : "Vista de la zona del plano"}
    >
      {planta?.ambientes.map((a, i) => (
        <polygon
          key={`a${i}`}
          points={a.puntos.map(([px, py]) => `${px},${y(py)}`).join(" ")}
          fill="#e7e5e4"
          stroke="none"
        />
      ))}
      <g stroke="#292524" strokeWidth={1.25} vectorEffect="non-scaling-stroke" strokeLinecap="round">
        {muros.map(([x1, y1, x2, y2], i) => (
          <line key={i} x1={x1} y1={y(y1)} x2={x2} y2={y(y2)} vectorEffect="non-scaling-stroke" />
        ))}
      </g>
      {planta?.aberturas.map((a, i) => (
        <line
          key={`b${i}`}
          x1={a.x}
          y1={y(a.y)}
          x2={a.x2}
          y2={y(a.y2)}
          stroke={a.tipo === "ventana" ? COLOR_VENTANA : COLOR_PUERTA}
          strokeWidth={4}
          strokeDasharray={a.tipo === "puerta" ? "3 2" : undefined}
          vectorEffect="non-scaling-stroke"
        />
      ))}
      {planta?.ambientes.map((a, i) => {
        const cx = a.puntos.reduce((s, p) => s + p[0], 0) / a.puntos.length;
        const cy = a.puntos.reduce((s, p) => s + p[1], 0) / a.puntos.length;
        return (
          <text key={`t${i}`} x={cx} y={y(cy)} fontSize={letra} textAnchor="middle" fill="#44403c">
            <tspan x={cx}>{a.nombre}</tspan>
            <tspan x={cx} dy={letra * 1.2} fill="#78716c">
              {a.area.toLocaleString("es-BO", { maximumFractionDigits: 1 })} m²
            </tspan>
          </text>
        );
      })}
    </svg>
  );
}

export function LeyendaPlano() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-600">
      <span className="inline-flex items-center gap-1.5">
        <span className="h-0.5 w-4 bg-stone-800" /> Muros
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-1 w-4" style={{ background: COLOR_VENTANA }} /> Ventanas
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-1 w-4 border-t-4 border-dashed" style={{ borderColor: COLOR_PUERTA }} /> Puertas
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-3 w-4 rounded-sm bg-stone-200" /> Ambientes
      </span>
    </div>
  );
}
