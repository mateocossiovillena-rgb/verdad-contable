import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Alerta } from "../tipos";
import { Marco } from "../componentes/Marco";
import { IconoAdelante, IconoCheck } from "../componentes/iconos";
import { Cargando, EstadoVacio, MensajeError, Pildora, Tarjeta } from "../componentes/ui";

/** A dónde lleva cada alerta: donde se resuelve. */
function destino(a: Alerta): string {
  if (a.mensaje.startsWith("No se cerró el día")) return `/obras/${a.obra_id}/cierre`;
  if (a.partida_id !== null) return `/obras/${a.obra_id}/partidas`;
  return `/obras/${a.obra_id}`;
}

function etiqueta(a: Alerta): string {
  if (a.mensaje.startsWith("No se cerró el día")) return "Día sin cerrar";
  return a.nivel === "rojo" ? "Problema" : "Atención";
}

export function Alertas() {
  const alertas = useQuery({ queryKey: ["alertas"], queryFn: () => api<Alerta[]>("/api/alertas") });
  const lista = alertas.data ?? [];

  return (
    <Marco titulo="Alertas">
      {alertas.isLoading && <Cargando />}
      <MensajeError error={alertas.error} reintentar={() => alertas.refetch()} />
      {alertas.data && lista.length === 0 && (
        <Tarjeta>
          <EstadoVacio
            icono={<IconoCheck tamano={32} className="text-emerald-600" />}
            texto="Todo en orden: ninguna obra tiene alertas."
          />
        </Tarjeta>
      )}
      {lista.length > 0 && (
        <Tarjeta className="p-0">
          <ul className="divide-y divide-stone-100">
            {lista.map((a, i) => (
              <li key={i}>
                <Link
                  to={destino(a)}
                  className="flex items-center gap-3 px-4 py-3 transition hover:bg-stone-50 active:bg-stone-100"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Pildora tono={a.nivel === "rojo" ? "problema" : "atencion"}>{etiqueta(a)}</Pildora>
                      <span className="truncate text-sm font-medium text-stone-900">{a.obra_nombre}</span>
                    </div>
                    <p className="text-sm text-stone-700">{a.mensaje}</p>
                  </div>
                  <IconoAdelante tamano={18} className="shrink-0 text-stone-400" />
                </Link>
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}
    </Marco>
  );
}
