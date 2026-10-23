import {
  useEffect,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { Link } from "react-router-dom";
import type { Semaforo } from "../tipos";
import { IconoCheck } from "./iconos";

// Reglas de diseño: ver guia-diseno-frontend.md (un solo botón naranja por pantalla, cifras con
// tabular-nums, el color siempre acompañado de texto, controles de 48 px o más).

const FOCO = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marca-500 focus-visible:ring-offset-2";

export function Tarjeta({
  children,
  className = "",
  tocable = false,
}: {
  children: ReactNode;
  className?: string;
  tocable?: boolean;
}) {
  const extra = tocable ? "transition hover:border-stone-300 hover:shadow active:scale-[0.99]" : "";
  return (
    <div className={`rounded-2xl border border-stone-200 bg-white p-4 shadow-sm ${extra} ${className}`}>{children}</div>
  );
}

type Variante = "primario" | "secundario" | "peligro" | "fantasma";
const ESTILOS: Record<Variante, string> = {
  primario: "bg-marca-600 text-white shadow-sm hover:bg-marca-700 disabled:bg-stone-300 disabled:shadow-none",
  secundario:
    "border border-stone-300 bg-white text-stone-800 shadow-sm hover:bg-stone-50 disabled:text-stone-400 disabled:shadow-none",
  peligro: "bg-red-700 text-white shadow-sm hover:bg-red-800 disabled:bg-stone-300",
  fantasma: "text-stone-700 hover:bg-stone-100 disabled:text-stone-400",
};

function claseBoton(variante: Variante, grande: boolean, className: string) {
  const tamano = grande ? "min-h-14 px-5 text-lg" : "min-h-12 px-4";
  return `inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition active:scale-[0.98] disabled:active:scale-100 ${FOCO} ${tamano} ${ESTILOS[variante]} ${className}`;
}

export function Boton({
  variante = "primario",
  grande = false,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: Variante; grande?: boolean }) {
  return <button className={claseBoton(variante, grande, className)} {...props} />;
}

export function BotonEnlace({
  a,
  children,
  variante = "primario",
  grande = false,
  className = "",
}: {
  a: string;
  children: ReactNode;
  variante?: Variante;
  grande?: boolean;
  className?: string;
}) {
  return (
    <Link to={a} className={claseBoton(variante, grande, className)}>
      {children}
    </Link>
  );
}

/** Botón cuadrado solo con ícono; el título se lee en voz alta y aparece al pasar el mouse. */
export function BotonIcono({
  titulo,
  children,
  className = "",
  ...props
}: { titulo: string; children: ReactNode } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      title={titulo}
      aria-label={titulo}
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-stone-600 transition hover:bg-stone-100 hover:text-stone-900 active:scale-95 disabled:opacity-30 ${FOCO} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Campo({ etiqueta, ayuda, children }: { etiqueta: string; ayuda?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-stone-800">{etiqueta}</span>
      {children}
      {ayuda && <span className="mt-1 block text-xs text-stone-600">{ayuda}</span>}
    </label>
  );
}

const ESTILO_ENTRADA =
  "block w-full min-h-12 rounded-xl border border-stone-300 bg-white px-3 py-2 text-base text-stone-900 placeholder:text-stone-400 focus:border-marca-500 focus:outline-none focus:ring-2 focus:ring-marca-500/30 disabled:bg-stone-100 disabled:text-stone-500";

export function Entrada({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${ESTILO_ENTRADA} ${className}`} {...props} />;
}

export function Selector({ className = "", ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${ESTILO_ENTRADA} ${className}`} {...props} />;
}

export function AreaTexto({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${ESTILO_ENTRADA} ${className}`} rows={2} {...props} />;
}

/** Interruptor sí/no grande, cómodo para el dedo. */
export function Interruptor({
  etiqueta,
  activo,
  cambiar,
}: {
  etiqueta: string;
  activo: boolean;
  cambiar: (valor: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={activo}
      onClick={() => cambiar(!activo)}
      className={`flex min-h-12 w-full items-center justify-between gap-3 rounded-xl border border-stone-300 bg-white px-3 text-left text-base ${FOCO}`}
    >
      <span className="text-stone-800">{etiqueta}</span>
      <span className={`relative h-7 w-12 shrink-0 rounded-full transition ${activo ? "bg-emerald-600" : "bg-stone-300"}`}>
        <span
          className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all ${activo ? "left-[22px]" : "left-0.5"}`}
        />
      </span>
    </button>
  );
}

/** Botón grande para elegir entre pocas opciones (en vez de una lista desplegable). */
export function OpcionGrande({
  activo,
  onClick,
  children,
}: {
  activo: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={activo}
      onClick={onClick}
      className={`flex min-h-14 items-center justify-center rounded-xl border px-3 text-center text-sm font-semibold transition active:scale-[0.98] ${FOCO} ${
        activo
          ? "border-marca-600 bg-marca-50 text-marca-700 ring-1 ring-marca-600"
          : "border-stone-300 bg-white text-stone-800 hover:bg-stone-50"
      }`}
    >
      {children}
    </button>
  );
}

export function MensajeError({ error, reintentar }: { error: unknown; reintentar?: () => void }) {
  if (!error) return null;
  const texto = error instanceof Error ? error.message : String(error);
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      <span>{texto}</span>
      {reintentar && (
        <button type="button" onClick={reintentar} className="shrink-0 font-semibold underline">
          Reintentar
        </button>
      )}
    </div>
  );
}

/** Esqueleto con la forma de las tarjetas: la pantalla no salta cuando llegan los datos. */
export function Cargando({ filas = 2 }: { filas?: number }) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Cargando">
      {Array.from({ length: filas }, (_, i) => (
        <div key={i} className="animate-pulse rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
          <div className="h-4 w-1/3 rounded bg-stone-200" />
          <div className="mt-3 h-8 w-1/2 rounded bg-stone-200" />
          <div className="mt-3 h-3 w-2/3 rounded bg-stone-100" />
        </div>
      ))}
    </div>
  );
}

export function EstadoVacio({ icono, texto, accion }: { icono?: ReactNode; texto: string; accion?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 py-6 text-center">
      {icono && <div className="text-stone-400">{icono}</div>}
      <p className="text-stone-600">{texto}</p>
      {accion}
    </div>
  );
}

// --- Estados y semáforo ---

export type Tono = "bien" | "atencion" | "problema" | "neutro";

const TONOS: Record<Tono, string> = {
  bien: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  atencion: "bg-amber-50 text-amber-800 ring-amber-600/25",
  problema: "bg-red-50 text-red-700 ring-red-600/15",
  neutro: "bg-stone-100 text-stone-700 ring-stone-500/15",
};

const PUNTOS: Record<Tono, string> = {
  bien: "bg-emerald-600",
  atencion: "bg-amber-500",
  problema: "bg-red-600",
  neutro: "bg-stone-400",
};

export function Pildora({ tono, children, punto = true }: { tono: Tono; children: ReactNode; punto?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${TONOS[tono]}`}
    >
      {punto && <span className={`h-1.5 w-1.5 rounded-full ${PUNTOS[tono]}`} aria-hidden />}
      {children}
    </span>
  );
}

export const TONO_SEMAFORO: Record<Semaforo, Tono> = {
  verde: "bien",
  amarillo: "atencion",
  rojo: "problema",
  sin_dato: "neutro",
};

const TEXTO_SEMAFORO: Record<Semaforo, string> = {
  verde: "Bien",
  amarillo: "Atención",
  rojo: "Problema",
  sin_dato: "Sin datos",
};

/** El semáforo siempre lleva texto: al sol, o para quien no distingue colores, el punto solo no basta. */
export function PildoraSemaforo({ valor }: { valor: Semaforo | null }) {
  const v = valor ?? "sin_dato";
  return <Pildora tono={TONO_SEMAFORO[v]}>{TEXTO_SEMAFORO[v]}</Pildora>;
}

const RELLENO: Record<Tono, string> = {
  bien: "bg-emerald-600",
  atencion: "bg-amber-500",
  problema: "bg-red-600",
  neutro: "bg-stone-500",
};

/** Avance real (relleno) contra dónde debería estar (marca vertical). */
export function BarraAvance({
  real,
  plan,
  semaforo,
}: {
  real: number;
  plan?: number | null;
  semaforo?: Semaforo | null;
}) {
  const tono = TONO_SEMAFORO[semaforo ?? "sin_dato"];
  return (
    <div className="relative h-2.5 w-full rounded-full bg-stone-200">
      <div className={`h-full rounded-full ${RELLENO[tono]}`} style={{ width: `${Math.min(100, real * 100)}%` }} />
      {plan !== null && plan !== undefined && (
        <div
          className="absolute -top-1 h-[18px] w-0.5 rounded bg-stone-900"
          style={{ left: `${Math.min(100, plan * 100)}%` }}
          title={`Debería: ${Math.round(plan * 100)} %`}
        />
      )}
    </div>
  );
}

/** Etiqueta, cifra protagonista y detalle opcional. */
export function Metrica({
  etiqueta,
  valor,
  detalle,
  grande = false,
}: {
  etiqueta: string;
  valor: ReactNode;
  detalle?: ReactNode;
  grande?: boolean;
}) {
  return (
    <div className="min-w-0">
      <p className="text-sm text-stone-600">{etiqueta}</p>
      <p
        className={`mt-0.5 font-semibold tracking-tight tabular-nums text-stone-900 ${grande ? "text-4xl" : "text-xl"}`}
      >
        {valor}
      </p>
      {detalle && <div className="mt-1 text-xs text-stone-600 tabular-nums">{detalle}</div>}
    </div>
  );
}

/** Pestañas simples, del ancho de la pantalla en el celular. */
export function Pestanas<T extends string>({
  opciones,
  activa,
  cambiar,
}: {
  opciones: { valor: T; texto: string }[];
  activa: T;
  cambiar: (valor: T) => void;
}) {
  return (
    <div className="flex rounded-xl bg-stone-200/70 p-1" role="tablist">
      {opciones.map((o) => (
        <button
          key={o.valor}
          type="button"
          role="tab"
          aria-selected={activa === o.valor}
          onClick={() => cambiar(o.valor)}
          className={`min-h-10 flex-1 rounded-lg px-3 text-sm font-semibold transition ${FOCO} ${
            activa === o.valor ? "bg-white text-stone-900 shadow-sm" : "text-stone-600 hover:text-stone-900"
          }`}
        >
          {o.texto}
        </button>
      ))}
    </div>
  );
}

// --- Avisos breves (confirmaciones que no bloquean la pantalla) ---

type OyenteAviso = (texto: string | null) => void;
const oyentesAviso = new Set<OyenteAviso>();
let temporizador: number | undefined;

export function avisar(texto: string) {
  window.clearTimeout(temporizador);
  oyentesAviso.forEach((o) => o(texto));
  temporizador = window.setTimeout(() => oyentesAviso.forEach((o) => o(null)), 3500);
}

export function Avisos() {
  const [texto, setTexto] = useState<string | null>(null);
  useEffect(() => {
    oyentesAviso.add(setTexto);
    return () => {
      oyentesAviso.delete(setTexto);
    };
  }, []);
  if (!texto) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-20 z-30 flex justify-center px-4 pb-[env(safe-area-inset-bottom)]">
      <div
        role="status"
        className="pointer-events-auto flex items-center gap-2 rounded-xl bg-stone-900 px-4 py-3 text-sm font-medium text-white shadow-lg"
      >
        <IconoCheck tamano={18} className="text-emerald-400" />
        {texto}
      </div>
    </div>
  );
}
