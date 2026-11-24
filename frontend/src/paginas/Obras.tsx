import { useQuery } from "@tanstack/react-query";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api";
import { bs, dinero, fecha, indice, pct } from "../formato";
import { useSesion } from "../sesion";
import type { ObraResumen } from "../tipos";
import { Marco } from "../componentes/Marco";
import { IconoAdelante, IconoCampana, IconoMas, IconoObras } from "../componentes/iconos";
import {
  BarraAvance,
  BotonEnlace,
  Cargando,
  EstadoVacio,
  MensajeError,
  Metrica,
  PildoraSemaforo,
  Tarjeta,
} from "../componentes/ui";

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
      <MensajeError error={obras.error} reintentar={() => obras.refetch()} />
      {obras.data?.length === 0 && (
        <Tarjeta>
          {esDueno ? (
            <EstadoVacio
              icono={<IconoObras tamano={32} />}
              texto="Todavía no tienes obras. Crea la primera para empezar."
              accion={
                <div className="flex flex-col gap-2 sm:flex-row">
                  <BotonEnlace a="/obras/nueva">
                    <IconoMas />
                    Nueva obra
                  </BotonEnlace>
                  <BotonEnlace a="/obras/importar" variante="secundario">
                    Importar desde Excel
                  </BotonEnlace>
                </div>
              }
            />
          ) : (
            <EstadoVacio icono={<IconoObras tamano={32} />} texto="No tienes obras asignadas. Pide al dueño que te asigne una." />
          )}
        </Tarjeta>
      )}
      {obras.data?.map((o) =>
        esDueno ? <TarjetaObraDueno key={o.id} obra={o} /> : <TarjetaObraEncargado key={o.id} obra={o} />,
      )}
      {esDueno && obras.data && obras.data.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          <BotonEnlace a="/obras/nueva" variante="secundario" className="w-full">
            <IconoMas />
            Nueva obra
          </BotonEnlace>
          <BotonEnlace a="/obras/importar" variante="secundario" className="w-full">
            Importar desde Excel (Kit TCM)
          </BotonEnlace>
        </div>
      )}
    </Marco>
  );
}

function TarjetaObraDueno({ obra }: { obra: ObraResumen }) {
  const presupuesto = obra.presupuesto ?? obra.presupuesto_total;
  return (
    <Link to={`/obras/${obra.id}`} className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marca-500">
      <Tarjeta tocable className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold tracking-tight text-stone-900">{obra.nombre}</h2>
            <p className="text-sm text-stone-600">
              {obra.cliente && `${obra.cliente} · `}
              {obra.ubicacion && `${obra.ubicacion} · `}
              <span className="tabular-nums">
                {fecha(obra.fecha_inicio)} – {fecha(obra.fecha_fin)}
              </span>
            </p>
          </div>
          <PildoraSemaforo valor={obra.semaforo} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Metrica
            etiqueta="Gastado"
            valor={dinero(obra.gastado, obra.moneda)}
            detalle={presupuesto ? `de ${dinero(presupuesto, obra.moneda)}` : "Sin presupuesto"}
          />
          <Metrica etiqueta="Hoy" valor={dinero(obra.gastado_hoy, obra.moneda)} />
        </div>

        <div>
          <div className="mb-1.5 flex justify-between text-sm tabular-nums text-stone-700">
            <span>Avance real {pct(obra.avance_real)}</span>
            <span className="text-stone-600">Debería {pct(obra.avance_planificado)}</span>
          </div>
          <BarraAvance real={obra.avance_real ?? 0} plan={obra.avance_planificado} semaforo={obra.semaforo} />
        </div>

        <div className="flex items-center gap-4 border-t border-stone-100 pt-3 text-sm tabular-nums text-stone-600">
          <span title="Índice de cronograma: menos de 1 = atrasado">SPI {indice(obra.spi)}</span>
          <span title="Índice de costo: menos de 1 = gastando más de lo que avanza">CPI {indice(obra.cpi)}</span>
          {obra.alertas > 0 && (
            <span className="inline-flex items-center gap-1 font-medium text-red-700">
              <IconoCampana tamano={16} />
              {obra.alertas} alerta(s)
            </span>
          )}
          <IconoAdelante tamano={18} className="ml-auto text-stone-400" />
        </div>
      </Tarjeta>
    </Link>
  );
}

function TarjetaObraEncargado({ obra }: { obra: ObraResumen }) {
  return (
    <Link to={`/obras/${obra.id}/hoy`} className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marca-500">
      <Tarjeta tocable className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold tracking-tight text-stone-900">{obra.nombre}</h2>
          <p className="truncate text-sm text-stone-600">{obra.ubicacion}</p>
        </div>
        <div className="text-right">
          <div className="text-sm text-stone-600">Hoy</div>
          <div className="font-semibold tabular-nums text-stone-900">{bs(obra.gastado_hoy)}</div>
        </div>
      </Tarjeta>
    </Link>
  );
}
