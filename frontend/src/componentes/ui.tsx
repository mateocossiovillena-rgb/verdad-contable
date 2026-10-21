import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { Link } from "react-router-dom";
import type { Semaforo } from "../tipos";

export function Tarjeta({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl bg-white p-4 shadow-sm ring-1 ring-stone-200 ${className}`}>{children}</div>;
}

type Variante = "primario" | "secundario" | "peligro";
const ESTILOS: Record<Variante, string> = {
  primario: "bg-marca-600 text-white hover:bg-marca-700 disabled:bg-stone-300",
  secundario: "bg-white text-stone-800 ring-1 ring-stone-300 hover:bg-stone-50 disabled:text-stone-400",
  peligro: "bg-red-600 text-white hover:bg-red-700 disabled:bg-stone-300",
};

export function Boton({
  variante = "primario",
  grande = false,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: Variante; grande?: boolean }) {
  const tamano = grande ? "min-h-14 px-5 text-lg" : "min-h-11 px-4";
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition ${tamano} ${ESTILOS[variante]} ${className}`}
      {...props}
    />
  );
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
  const tamano = grande ? "min-h-14 px-5 text-lg" : "min-h-11 px-4";
  return (
    <Link
      to={a}
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition ${tamano} ${ESTILOS[variante]} ${className}`}
    >
      {children}
    </Link>
  );
}

export function Campo({ etiqueta, ayuda, children }: { etiqueta: string; ayuda?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-stone-700">{etiqueta}</span>
      {children}
      {ayuda && <span className="mt-1 block text-xs text-stone-500">{ayuda}</span>}
    </label>
  );
}

const ESTILO_ENTRADA =
  "block w-full min-h-11 rounded-xl border-0 bg-white px-3 py-2 text-base ring-1 ring-stone-300 focus:ring-2 focus:ring-marca-500 focus:outline-none";

export function Entrada(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={ESTILO_ENTRADA} {...props} />;
}

export function Selector(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={ESTILO_ENTRADA} {...props} />;
}

export function MensajeError({ error }: { error: unknown }) {
  if (!error) return null;
  const texto = error instanceof Error ? error.message : String(error);
  return <p className="rounded-xl bg-red-50 p-3 text-sm text-red-800 ring-1 ring-red-200">{texto}</p>;
}

export function Cargando() {
  return <p className="py-10 text-center text-stone-500">Cargando…</p>;
}

const COLORES_SEMAFORO: Record<Semaforo, string> = {
  verde: "bg-green-500",
  amarillo: "bg-amber-400",
  rojo: "bg-red-600",
  sin_dato: "bg-stone-300",
};
const TEXTO_SEMAFORO: Record<Semaforo, string> = {
  verde: "Bien",
  amarillo: "Atención",
  rojo: "Problema",
  sin_dato: "Sin datos",
};

export function PuntoSemaforo({ valor, conTexto = false }: { valor: Semaforo | null; conTexto?: boolean }) {
  const v = valor ?? "sin_dato";
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-block h-3 w-3 rounded-full ${COLORES_SEMAFORO[v]}`} aria-hidden />
      {conTexto ? <span className="text-sm">{TEXTO_SEMAFORO[v]}</span> : <span className="sr-only">{TEXTO_SEMAFORO[v]}</span>}
    </span>
  );
}

export function BarraAvance({ real, plan }: { real: number; plan?: number | null }) {
  return (
    <div className="relative h-3 w-full overflow-hidden rounded-full bg-stone-200">
      <div className="h-full rounded-full bg-marca-500" style={{ width: `${Math.min(100, real * 100)}%` }} />
      {plan !== null && plan !== undefined && (
        <div
          className="absolute top-0 h-full w-0.5 bg-stone-800"
          style={{ left: `${Math.min(100, plan * 100)}%` }}
          title="Dónde debería estar"
        />
      )}
    </div>
  );
}
