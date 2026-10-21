import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { bs, fecha, hoyISO } from "../formato";
import { useSesion } from "../sesion";
import { TIPOS_GASTO, type Dia, type Obra } from "../tipos";
import { Marco } from "../componentes/Marco";
import { Boton, BotonEnlace, Cargando, MensajeError, Tarjeta } from "../componentes/ui";

export function useObra(obraId: string | undefined) {
  return useQuery({ queryKey: ["obra", obraId], queryFn: () => api<Obra>(`/api/obras/${obraId}`) });
}

export function useDia(obraId: string | undefined, dia: string) {
  return useQuery({ queryKey: ["dia", obraId, dia], queryFn: () => api<Dia>(`/api/obras/${obraId}/dia?fecha=${dia}`) });
}

/** Pantalla principal del encargado: total de hoy y botones grandes. */
export function Hoy() {
  const { obraId } = useParams();
  const { usuario } = useSesion();
  const obra = useObra(obraId);
  const dia = useDia(obraId, hoyISO());
  const volver = usuario?.rol === "dueno" ? `/obras/${obraId}` : "/";

  return (
    <Marco titulo={obra.data?.nombre ?? "Obra"} volver={volver}>
      <Tarjeta className="text-center">
        <div className="text-sm text-stone-500">Gastado hoy · {fecha(hoyISO())}</div>
        <div className="my-1 text-4xl font-bold">{dia.data ? bs(dia.data.total_dia) : "…"}</div>
        <div className="text-sm text-stone-500">Acumulado de la obra: {dia.data ? bs(dia.data.acumulado) : "…"}</div>
        {dia.data?.cerrado && (
          <div className="mt-2 inline-block rounded-full bg-green-100 px-3 py-1 text-sm text-green-800">
            ✔ Día cerrado
          </div>
        )}
      </Tarjeta>

      <div className="grid grid-cols-2 gap-3">
        <BotonEnlace a={`/obras/${obraId}/gasto`} grande className="h-28 flex-col text-xl">
          <span className="text-3xl">💸</span>+ Gasto
        </BotonEnlace>
        <BotonEnlace a={`/obras/${obraId}/avance`} grande className="h-28 flex-col text-xl">
          <span className="text-3xl">🧱</span>+ Avance
        </BotonEnlace>
      </div>
      <BotonEnlace a={`/obras/${obraId}/cierre`} variante="secundario" grande className="w-full">
        📋 Cierre del día
      </BotonEnlace>

      {dia.data && dia.data.gastos.length > 0 && (
        <Tarjeta>
          <h2 className="mb-2 font-semibold">Gastos de hoy</h2>
          <ListaGastosDia dia={dia.data} />
        </Tarjeta>
      )}
    </Marco>
  );
}

function ListaGastosDia({ dia }: { dia: Dia }) {
  return (
    <ul className="divide-y divide-stone-100">
      {dia.gastos.map((g) => (
        <li key={g.id} className="flex items-center justify-between gap-2 py-2">
          <div className="min-w-0">
            <div className="truncate font-medium">{g.descripcion || TIPOS_GASTO[g.tipo]}</div>
            <div className="text-xs text-stone-500">
              {TIPOS_GASTO[g.tipo]} · {g.partida_nombre}
              {!g.con_factura && " · sin factura"}
              {g.foto && (
                <>
                  {" · "}
                  <a href={`/api/fotos/${g.foto}`} target="_blank" rel="noreferrer" className="text-marca-600 underline">
                    foto
                  </a>
                </>
              )}
            </div>
          </div>
          <div className="shrink-0 font-semibold">{bs(g.monto)}</div>
        </li>
      ))}
    </ul>
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
    onSuccess: () => cliente.invalidateQueries(),
  });
  const reabrir = useMutation({
    mutationFn: () => api(`/api/obras/${obraId}/cierres/${dia}`, "DELETE"),
    onSuccess: () => cliente.invalidateQueries(),
  });

  const cambiarDia = (dias: number) => {
    const d = new Date(dia + "T12:00:00");
    d.setDate(d.getDate() + dias);
    setDia(d.toISOString().slice(0, 10));
  };

  return (
    <Marco titulo={`Cierre · ${obra.data?.nombre ?? ""}`} volver={`/obras/${obraId}/hoy`}>
      <div className="flex items-center justify-between">
        <Boton variante="secundario" onClick={() => cambiarDia(-1)} aria-label="Día anterior">
          ‹
        </Boton>
        <div className="font-semibold">{fecha(dia)}</div>
        <Boton variante="secundario" onClick={() => cambiarDia(1)} disabled={dia >= hoyISO()} aria-label="Día siguiente">
          ›
        </Boton>
      </div>
      {datos.isLoading && <Cargando />}
      <MensajeError error={datos.error} />
      {datos.data && (
        <>
          <Tarjeta className="grid grid-cols-2 gap-2 text-center">
            <div>
              <div className="text-sm text-stone-500">Total del día</div>
              <div className="text-2xl font-bold">{bs(datos.data.total_dia)}</div>
            </div>
            <div>
              <div className="text-sm text-stone-500">Acumulado obra</div>
              <div className="text-2xl font-bold">{bs(datos.data.acumulado)}</div>
            </div>
          </Tarjeta>
          <Tarjeta>
            {datos.data.gastos.length === 0 ? (
              <p className="text-stone-500">No hay gastos registrados este día.</p>
            ) : (
              <ListaGastosDia dia={datos.data} />
            )}
          </Tarjeta>
          <MensajeError error={cerrar.error ?? reabrir.error} />
          {datos.data.cerrado ? (
            <div className="space-y-3 text-center">
              <p className="rounded-xl bg-green-100 p-3 text-green-800">
                ✔ Día cerrado{datos.data.cerrado_por && ` por ${datos.data.cerrado_por}`}
              </p>
              {usuario?.rol === "dueno" && (
                <Boton variante="secundario" onClick={() => reabrir.mutate()} disabled={reabrir.isPending}>
                  Reabrir día
                </Boton>
              )}
            </div>
          ) : (
            <Boton grande className="w-full" onClick={() => cerrar.mutate()} disabled={cerrar.isPending}>
              {cerrar.isPending ? "Cerrando…" : `Cerrar el día con ${bs(datos.data.total_dia)}`}
            </Boton>
          )}
          <p className="text-center text-xs text-stone-500">
            Al cerrar el día ya no se pueden agregar gastos con esa fecha.{" "}
            <Link to={`/obras/${obraId}/gasto`} className="underline">
              ¿Falta algún gasto?
            </Link>
          </p>
        </>
      )}
    </Marco>
  );
}
