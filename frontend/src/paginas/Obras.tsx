import { useQuery } from "@tanstack/react-query";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api";
import { bs, fecha, indice, pct } from "../formato";
import { useSesion } from "../sesion";
import type { ObraResumen } from "../tipos";
import { Marco } from "../componentes/Marco";
import { BarraAvance, BotonEnlace, Cargando, MensajeError, PuntoSemaforo, Tarjeta } from "../componentes/ui";

export function useObras() {
  return useQuery({ queryKey: ["obras"], queryFn: () => api<ObraResumen[]>("/api/obras") });
}

/** Pantalla inicial: el dueño ve sus obras; el encargado va directo a la suya. */
export function Inicio() {
  const { usuario } = useSesion();
  const obras = useObras();
  if (usuario?.rol === "dueno") return <Navigate to="/obras" replace />;
  if (obras.data?.length === 1) return <Navigate to={`/obras/${obras.data[0].id}/hoy`} replace />;
  return <MisObras />;
}

export function MisObras() {
  const { usuario } = useSesion();
  const obras = useObras();
  const esDueno = usuario?.rol === "dueno";

  return (
    <Marco titulo={esDueno ? "Mis obras" : "Elige la obra"}>
      {obras.isLoading && <Cargando />}
      <MensajeError error={obras.error} />
      {obras.data?.length === 0 &&
        (esDueno ? (
          <Tarjeta className="text-center">
            <p className="mb-4 text-stone-600">Todavía no tienes obras. Crea la primera para empezar.</p>
            <BotonEnlace a="/obras/nueva" grande>
              + Nueva obra
            </BotonEnlace>
          </Tarjeta>
        ) : (
          <Tarjeta>No tienes obras asignadas. Pide al dueño que te asigne una.</Tarjeta>
        ))}
      {obras.data?.map((o) =>
        esDueno ? <TarjetaObraDueno key={o.id} obra={o} /> : <TarjetaObraEncargado key={o.id} obra={o} />,
      )}
      {esDueno && obras.data && obras.data.length > 0 && (
        <BotonEnlace a="/obras/nueva" variante="secundario" className="w-full">
          + Nueva obra
        </BotonEnlace>
      )}
    </Marco>
  );
}

function TarjetaObraDueno({ obra }: { obra: ObraResumen }) {
  return (
    <Link to={`/obras/${obra.id}`} className="block">
      <Tarjeta className="space-y-3 transition hover:ring-marca-500">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">{obra.nombre}</h2>
            <p className="text-sm text-stone-500">
              {obra.ubicacion && `${obra.ubicacion} · `}
              {fecha(obra.fecha_inicio)} – {fecha(obra.fecha_fin)}
            </p>
          </div>
          <PuntoSemaforo valor={obra.semaforo} conTexto />
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <div className="text-stone-500">Gastado</div>
            <div className="font-semibold">{bs(obra.gastado)}</div>
            <div className="text-xs text-stone-500">de {bs(obra.presupuesto)}</div>
          </div>
          <div>
            <div className="text-stone-500">Hoy</div>
            <div className="font-semibold">{bs(obra.gastado_hoy)}</div>
          </div>
        </div>
        <div>
          <div className="mb-1 flex justify-between text-xs text-stone-600">
            <span>Avance real {pct(obra.avance_real)}</span>
            <span>Debería {pct(obra.avance_planificado)}</span>
          </div>
          <BarraAvance real={obra.avance_real ?? 0} plan={obra.avance_planificado} />
        </div>
        <div className="flex gap-4 text-xs text-stone-600">
          <span>SPI {indice(obra.spi)}</span>
          <span>CPI {indice(obra.cpi)}</span>
          {obra.alertas > 0 && <span className="font-semibold text-red-700">🔔 {obra.alertas} alerta(s)</span>}
        </div>
      </Tarjeta>
    </Link>
  );
}

function TarjetaObraEncargado({ obra }: { obra: ObraResumen }) {
  return (
    <Link to={`/obras/${obra.id}/hoy`} className="block">
      <Tarjeta className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">{obra.nombre}</h2>
          <p className="text-sm text-stone-500">{obra.ubicacion}</p>
        </div>
        <div className="text-right">
          <div className="text-xs text-stone-500">Hoy</div>
          <div className="font-semibold">{bs(obra.gastado_hoy)}</div>
        </div>
      </Tarjeta>
    </Link>
  );
}
