import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { bs, diaSemana, fecha, hoyISO, sumarDias } from "../formato";
import { useSesion } from "../sesion";
import { TIPOS_GASTO, type Dia, type Obra } from "../tipos";
import { Marco } from "../componentes/Marco";
import { IconoAdelante, IconoAtras, IconoBillete, IconoCierre, IconoLadrillos, IconoRecibo } from "../componentes/iconos";
import {
  avisar,
  Boton,
  BotonEnlace,
  BotonIcono,
  Cargando,
  EstadoVacio,
  MensajeError,
  Metrica,
  Pildora,
  Tarjeta,
  type Tono,
} from "../componentes/ui";

export function useObra(obraId: string | undefined) {
  return useQuery({ queryKey: ["obra", obraId], queryFn: () => api<Obra>(`/api/obras/${obraId}`) });
}

function consultaDia(obraId: string | undefined, dia: string) {
  return { queryKey: ["dia", obraId, dia], queryFn: () => api<Dia>(`/api/obras/${obraId}/dia?fecha=${dia}`) };
}

export function useDia(obraId: string | undefined, dia: string) {
  return useQuery(consultaDia(obraId, dia));
}

/** Pantalla principal del encargado: total de hoy y botones grandes. */
export function Hoy() {
  const { obraId } = useParams();
  const { usuario } = useSesion();
  const obra = useObra(obraId);
  const dia = useDia(obraId, hoyISO());
  const volver = usuario?.rol === "dueno" ? `/obras/${obraId}` : undefined;

  return (
    <Marco titulo={obra.data?.nombre ?? "Obra"} volver={volver}>
      {dia.isLoading && <Cargando filas={1} />}
      <MensajeError error={dia.error} reintentar={() => dia.refetch()} />
      {dia.data && (
        <Tarjeta className="space-y-3">
          <div className="flex items-start justify-between gap-3">
            <Metrica
              etiqueta={`Gastado hoy · ${fecha(hoyISO())}`}
              valor={bs(dia.data.total_dia)}
              detalle={`Acumulado de la obra: ${bs(dia.data.acumulado)}`}
              grande
            />
            <EstadoDia cerrado={dia.data.cerrado} />
          </div>
        </Tarjeta>
      )}

      <div className="grid grid-cols-2 gap-4">
        <BotonEnlace a={`/obras/${obraId}/gasto`} grande className="h-28 flex-col">
          <IconoBillete tamano={30} />
          Gasto
        </BotonEnlace>
        <BotonEnlace a={`/obras/${obraId}/avance`} variante="secundario" grande className="h-28 flex-col border-2 border-stone-800">
          <IconoLadrillos tamano={30} />
          Avance
        </BotonEnlace>
      </div>
      <BotonEnlace a={`/obras/${obraId}/cierre`} variante="secundario" className="w-full">
        <IconoCierre />
        Cierre del día
      </BotonEnlace>

      {dia.data && (
        <Tarjeta>
          <h2 className="mb-1 font-semibold text-stone-900">Gastos de hoy</h2>
          {dia.data.gastos.length === 0 ? (
            <EstadoVacio icono={<IconoRecibo tamano={28} />} texto="Todavía no hay gastos hoy." />
          ) : (
            <ListaGastosDia dia={dia.data} />
          )}
        </Tarjeta>
      )}
    </Marco>
  );
}

function EstadoDia({ cerrado }: { cerrado: boolean }) {
  return cerrado ? <Pildora tono="bien">Día cerrado</Pildora> : <Pildora tono="neutro">Día abierto</Pildora>;
}

function ListaGastosDia({ dia }: { dia: Dia }) {
  return (
    <ul className="divide-y divide-stone-100">
      {dia.gastos.map((g) => (
        <li key={g.id} className="flex items-center justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <div className="truncate font-medium text-stone-900">{g.descripcion || TIPOS_GASTO[g.tipo]}</div>
            <div className="text-sm text-stone-600">
              {TIPOS_GASTO[g.tipo]} · {g.partida_nombre}
              {!g.con_factura && " · sin factura"}
              {g.foto && (
                <>
                  {" · "}
                  <a href={`/api/fotos/${g.foto}`} target="_blank" rel="noreferrer" className="font-medium text-stone-900 underline">
                    foto
                  </a>
                </>
              )}
            </div>
          </div>
          <div className="shrink-0 font-semibold tabular-nums text-stone-900">{bs(g.monto)}</div>
        </li>
      ))}
    </ul>
  );
}

const TONO_DIA: Record<"cerrado" | "abierto" | "vacio", Tono> = { cerrado: "bien", abierto: "atencion", vacio: "neutro" };
const COLOR_PUNTO: Record<Tono, string> = {
  bien: "bg-emerald-600",
  atencion: "bg-amber-500",
  problema: "bg-red-600",
  neutro: "bg-stone-300",
};

/** Últimos 7 días con un punto por día: cerrado, con gastos sin cerrar o sin registro. */
function SemanaDias({ obraId, dia, elegir }: { obraId: string; dia: string; elegir: (d: string) => void }) {
  const hoy = hoyISO();
  const fin = sumarDias(dia, 3) > hoy ? hoy : sumarDias(dia, 3);
  const dias = Array.from({ length: 7 }, (_, i) => sumarDias(fin, i - 6));
  const consultas = useQueries({ queries: dias.map((d) => consultaDia(obraId, d)) });

  return (
    <div>
      <div className="grid grid-cols-7 gap-1">
        {dias.map((d, i) => {
          const datos = consultas[i].data;
          const estado = !datos ? "vacio" : datos.cerrado ? "cerrado" : datos.gastos.length > 0 ? "abierto" : "vacio";
          const activo = d === dia;
          return (
            <button
              key={d}
              type="button"
              onClick={() => elegir(d)}
              aria-pressed={activo}
              className={`flex min-h-16 flex-col items-center justify-center gap-1 rounded-xl text-xs transition ${
                activo ? "bg-stone-900 text-white" : "bg-white text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50"
              }`}
            >
              <span className={activo ? "text-stone-300" : "text-stone-500"}>{diaSemana(d)}</span>
              <span className="text-base font-semibold tabular-nums">{Number(d.slice(8, 10))}</span>
              <span className={`h-1.5 w-1.5 rounded-full ${COLOR_PUNTO[TONO_DIA[estado]]}`} aria-hidden />
            </button>
          );
        })}
      </div>
      <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-stone-600">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" /> Cerrado
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Con gastos sin cerrar
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-stone-300" /> Sin registro
        </span>
      </div>
    </div>
  );
}

export function CierreDia() {
  const { obraId } = useParams();
  const { usuario } = useSesion();
  const [dia, setDia] = useState(hoyISO());
  const obra = useObra(obraId);
  const datos = useDia(obraId, dia);
  const cliente = useQueryClient();

  const cerrar = useMutation({
    mutationFn: () => api<Dia>(`/api/obras/${obraId}/cierres`, "POST", { fecha: dia }),
    onSuccess: () => {
      cliente.invalidateQueries();
      avisar(`Día ${fecha(dia)} cerrado`);
    },
  });
  const reabrir = useMutation({
    mutationFn: () => api(`/api/obras/${obraId}/cierres/${dia}`, "DELETE"),
    onSuccess: () => {
      cliente.invalidateQueries();
      avisar(`Día ${fecha(dia)} reabierto`);
    },
  });

  return (
    <Marco titulo={`Cierre · ${obra.data?.nombre ?? ""}`} volver={`/obras/${obraId}/hoy`}>
      <div className="flex items-center justify-between gap-2">
        <BotonIcono titulo="Día anterior" onClick={() => setDia(sumarDias(dia, -1))}>
          <IconoAtras tamano={22} />
        </BotonIcono>
        <div className="font-semibold tabular-nums text-stone-900">
          {diaSemana(dia)} {fecha(dia)}
        </div>
        <BotonIcono titulo="Día siguiente" onClick={() => setDia(sumarDias(dia, 1))} disabled={dia >= hoyISO()}>
          <IconoAdelante tamano={22} />
        </BotonIcono>
      </div>
      <SemanaDias obraId={obraId!} dia={dia} elegir={setDia} />

      {datos.isLoading && <Cargando filas={1} />}
      <MensajeError error={datos.error} reintentar={() => datos.refetch()} />
      {datos.data && (
        <>
          <Tarjeta className="grid grid-cols-2 gap-4">
            <Metrica etiqueta="Total del día" valor={bs(datos.data.total_dia)} />
            <Metrica etiqueta="Acumulado obra" valor={bs(datos.data.acumulado)} />
          </Tarjeta>
          <Tarjeta>
            {datos.data.gastos.length === 0 ? (
              <EstadoVacio icono={<IconoRecibo tamano={28} />} texto="No hay gastos registrados este día." />
            ) : (
              <ListaGastosDia dia={datos.data} />
            )}
          </Tarjeta>
          <MensajeError error={cerrar.error ?? reabrir.error} />
          {datos.data.cerrado ? (
            <div className="space-y-3 text-center">
              <div className="flex items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-emerald-800">
                Día cerrado{datos.data.cerrado_por && ` por ${datos.data.cerrado_por}`}
              </div>
              {usuario?.rol === "dueno" && (
                <Boton variante="secundario" onClick={() => reabrir.mutate()} disabled={reabrir.isPending}>
                  {reabrir.isPending ? "Reabriendo…" : "Reabrir día"}
                </Boton>
              )}
            </div>
          ) : (
            <Boton grande className="w-full" onClick={() => cerrar.mutate()} disabled={cerrar.isPending}>
              {cerrar.isPending ? "Cerrando…" : `Cerrar el día con ${bs(datos.data.total_dia)}`}
            </Boton>
          )}
          <p className="text-center text-sm text-stone-600">
            Al cerrar el día ya no se pueden agregar gastos con esa fecha.{" "}
            <Link to={`/obras/${obraId}/gasto`} className="font-medium text-stone-900 underline">
              ¿Falta algún gasto?
            </Link>
          </p>
        </>
      )}
    </Marco>
  );
}
