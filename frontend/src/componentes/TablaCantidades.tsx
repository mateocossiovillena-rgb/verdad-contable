import type { CantidadObra, OrigenCantidad } from "../tipos";
import { BotonIcono, Pildora, type Tono } from "./ui";

const ORIGEN: Record<OrigenCantidad, { texto: string; tono: Tono; ayuda: string }> = {
  plano: { texto: "Del plano", tono: "bien", ayuda: "Medido en el archivo" },
  formulario: { texto: "Tu dato", tono: "neutro", ayuda: "Sale de lo que respondiste" },
  proporcion: { texto: "Típico", tono: "atencion", ayuda: "Valor típico por m²: revísalo" },
  editada: { texto: "Editada", tono: "neutro", ayuda: "Corregida a mano" },
};

const numero = new Intl.NumberFormat("es-BO", { maximumFractionDigits: 2 });

export function textoCantidad(valor: number): string {
  return numero.format(valor);
}

/** "12,5" o "12.5" a número; null si no es un número válido. */
export function leerCantidad(texto: string): number | null {
  const limpio = texto.replace(/\s/g, "").replace(",", ".");
  if (!limpio) return null;
  const valor = Number(limpio);
  return Number.isFinite(valor) && valor >= 0 ? valor : null;
}

/**
 * Cantidades por rubro, editables. `valores` guarda lo que el usuario escribió (por clave), empezando por
 * lo que ya había corregido; una fila sin valor muestra lo calculado.
 */
export function TablaCantidades({
  cantidades,
  valores,
  cambiar,
  soloLectura = false,
}: {
  cantidades: CantidadObra[];
  valores: Record<string, string>;
  cambiar: (clave: string, valor: string | null) => void;
  soloLectura?: boolean;
}) {
  const grupos = new Map<string, CantidadObra[]>();
  for (const c of cantidades) {
    const grupo = c.piso ?? "Toda la obra";
    grupos.set(grupo, [...(grupos.get(grupo) ?? []), c]);
  }
  return (
    <div className="space-y-4">
      {[...grupos].map(([grupo, filas]) => (
        <section key={grupo} className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
          <h3 className="border-b border-stone-200 bg-stone-50 px-4 py-2 text-xs font-medium uppercase tracking-wider text-stone-600">
            {grupo}
          </h3>
          <ul className="divide-y divide-stone-100">
            {filas.map((c) => {
              const calculada = c.cantidad_original ?? c.cantidad;
              const escrito = valores[c.clave];
              const valor = escrito === undefined ? null : leerCantidad(escrito);
              const editada = escrito !== undefined && valor !== calculada;
              const origen = ORIGEN[editada ? "editada" : (c.origen_original ?? c.origen)];
              const invalida = escrito !== undefined && valor === null;
              return (
                <li key={c.clave} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
                  <div className="min-w-0 flex-1 basis-56">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-stone-900">{c.nombre}</span>
                      <span title={origen.ayuda}>
                        <Pildora tono={origen.tono}>{origen.texto}</Pildora>
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm text-stone-600">
                      {editada ? `Calculado: ${textoCantidad(calculada)} ${c.unidad} · ${c.detalle}` : c.detalle}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    {soloLectura ? (
                      <span className="font-semibold tabular-nums text-stone-900">
                        {textoCantidad(valor ?? calculada)}
                      </span>
                    ) : (
                      <input
                        inputMode="decimal"
                        aria-label={`Cantidad de ${c.nombre}${c.piso ? `, ${c.piso}` : ""}`}
                        aria-invalid={invalida}
                        value={escrito ?? textoCantidad(calculada)}
                        onChange={(e) => cambiar(c.clave, e.target.value)}
                        className={`min-h-12 w-28 rounded-xl border bg-white px-3 text-right text-base font-semibold tabular-nums text-stone-900 focus:outline-none focus:ring-2 ${
                          invalida
                            ? "border-red-400 focus:ring-red-500/30"
                            : "border-stone-300 focus:border-marca-500 focus:ring-marca-500/30"
                        }`}
                      />
                    )}
                    <span className="w-8 text-sm text-stone-600">{c.unidad}</span>
                    {!soloLectura && editada && (
                      <BotonIcono titulo="Volver a lo calculado" onClick={() => cambiar(c.clave, null)}>
                        <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                          <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
                          <path d="M3 3v5h5" />
                        </svg>
                      </BotonIcono>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
