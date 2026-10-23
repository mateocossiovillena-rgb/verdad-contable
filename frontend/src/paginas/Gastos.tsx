import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { api, descargar } from "../api";
import { dinero, fecha } from "../formato";
import { TIPOS_GASTO, type Gasto, type TipoGasto } from "../tipos";
import { Marco } from "../componentes/Marco";
import { IconoDescargar, IconoRecibo } from "../componentes/iconos";
import {
  avisar,
  Boton,
  BotonIcono,
  Campo,
  Cargando,
  Entrada,
  EstadoVacio,
  Interruptor,
  MensajeError,
  Metrica,
  Pildora,
  Selector,
  Tarjeta,
} from "../componentes/ui";
import { useObra } from "./Hoy";

interface Filtros {
  desde: string;
  hasta: string;
  tipo: TipoGasto | "";
  sin_factura: boolean;
}

function consulta(f: Filtros): string {
  const p = new URLSearchParams();
  if (f.desde) p.set("desde", f.desde);
  if (f.hasta) p.set("hasta", f.hasta);
  if (f.tipo) p.set("tipo", f.tipo);
  if (f.sin_factura) p.set("sin_factura", "true");
  const texto = p.toString();
  return texto ? `?${texto}` : "";
}

/** Todos los gastos de la obra (dueño): filtros, total, exportar a Excel y anular. */
export function Gastos() {
  const { obraId } = useParams();
  const obra = useObra(obraId);
  const [filtros, setFiltros] = useState<Filtros>({ desde: "", hasta: "", tipo: "", sin_factura: false });
  const [anulando, setAnulando] = useState<number | null>(null);
  const gastos = useQuery({
    queryKey: ["gastos", obraId, filtros],
    queryFn: () => api<Gasto[]>(`/api/obras/${obraId}/gastos${consulta(filtros)}`),
  });
  const [exportando, setExportando] = useState(false);
  const [errorExportar, setErrorExportar] = useState<unknown>(null);
  const moneda = obra.data?.moneda ?? "Bs";
  const lista = gastos.data ?? [];
  const total = lista.reduce((suma, g) => suma + g.monto, 0);
  const sinFactura = lista.filter((g) => !g.con_factura).reduce((suma, g) => suma + g.monto, 0);

  async function exportar() {
    setExportando(true);
    setErrorExportar(null);
    try {
      await descargar(`/api/obras/${obraId}/gastos.xlsx${consulta(filtros)}`, `gastos-${obra.data?.nombre ?? obraId}.xlsx`);
    } catch (e) {
      setErrorExportar(e);
    } finally {
      setExportando(false);
    }
  }

  return (
    <Marco
      titulo={`Gastos · ${obra.data?.nombre ?? ""}`}
      volver={`/obras/${obraId}`}
      ancho
      accion={
        <BotonIcono titulo="Descargar Excel" onClick={exportar} disabled={exportando}>
          <IconoDescargar />
        </BotonIcono>
      }
    >
      <Tarjeta className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Campo etiqueta="Desde">
          <Entrada type="date" value={filtros.desde} onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })} />
        </Campo>
        <Campo etiqueta="Hasta">
          <Entrada type="date" value={filtros.hasta} onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })} />
        </Campo>
        <Campo etiqueta="Tipo">
          <Selector value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value as TipoGasto | "" })}>
            <option value="">Todos</option>
            {Object.entries(TIPOS_GASTO).map(([valor, texto]) => (
              <option key={valor} value={valor}>
                {texto}
              </option>
            ))}
          </Selector>
        </Campo>
        <div className="flex items-end">
          <Interruptor
            etiqueta="Solo sin factura"
            activo={filtros.sin_factura}
            cambiar={(v) => setFiltros({ ...filtros, sin_factura: v })}
          />
        </div>
      </Tarjeta>

      <MensajeError error={errorExportar} />
      {gastos.isLoading && <Cargando />}
      <MensajeError error={gastos.error} reintentar={() => gastos.refetch()} />

      {gastos.data && (
        <Tarjeta className="grid grid-cols-2 gap-4">
          <Metrica etiqueta={`Total (${lista.length} gasto${lista.length === 1 ? "" : "s"})`} valor={dinero(total, moneda)} />
          <Metrica etiqueta="Sin factura" valor={dinero(sinFactura, moneda)} />
        </Tarjeta>
      )}

      {gastos.data && lista.length === 0 && (
        <Tarjeta>
          <EstadoVacio icono={<IconoRecibo tamano={28} />} texto="No hay gastos con estos filtros." />
        </Tarjeta>
      )}

      {lista.length > 0 && (
        <>
          {/* Celular: lista con la cifra a la derecha */}
          <Tarjeta className="p-0 sm:hidden">
            <ul className="divide-y divide-stone-100">
              {lista.map((g) => (
                <li key={g.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-stone-900">{g.descripcion || TIPOS_GASTO[g.tipo]}</div>
                      <div className="text-sm text-stone-600">
                        <span className="tabular-nums">{fecha(g.fecha)}</span> · {TIPOS_GASTO[g.tipo]} · {g.partida_nombre}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-stone-600">
                        {!g.con_factura && <Pildora tono="neutro">Sin factura</Pildora>}
                        {g.foto && <EnlaceFoto foto={g.foto} />}
                        <span>{g.usuario_nombre}</span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-semibold tabular-nums text-stone-900">{dinero(g.monto, moneda)}</div>
                      <button className="mt-1 min-h-8 text-sm font-medium text-stone-600 underline" onClick={() => setAnulando(g.id)}>
                        Anular
                      </button>
                    </div>
                  </div>
                  {anulando === g.id && <FormAnular gasto={g} cerrar={() => setAnulando(null)} />}
                </li>
              ))}
            </ul>
          </Tarjeta>

          {/* Tablet y escritorio: tabla con montos alineados a la derecha */}
          <Tarjeta className="hidden overflow-x-auto p-0 sm:block">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-left text-xs font-medium uppercase tracking-wider text-stone-600">
                <tr>
                  <th className="px-4 py-2.5">Fecha</th>
                  <th className="px-3 py-2.5">Descripción</th>
                  <th className="px-3 py-2.5">Tipo</th>
                  <th className="px-3 py-2.5">Partida</th>
                  <th className="px-3 py-2.5">Factura</th>
                  <th className="px-3 py-2.5 text-right">Monto</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {lista.map((g) => (
                  <FilaGasto key={g.id} gasto={g} moneda={moneda} abierto={anulando === g.id} alternar={setAnulando} />
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-stone-200 font-semibold text-stone-900">
                  <td className="px-4 py-3" colSpan={5}>
                    Total
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums">{dinero(total, moneda)}</td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </Tarjeta>
        </>
      )}
    </Marco>
  );
}

function EnlaceFoto({ foto }: { foto: string }) {
  return (
    <a href={`/api/fotos/${foto}`} target="_blank" rel="noreferrer" className="font-medium text-stone-900 underline">
      foto
    </a>
  );
}

function FilaGasto({
  gasto: g,
  moneda,
  abierto,
  alternar,
}: {
  gasto: Gasto;
  moneda: string;
  abierto: boolean;
  alternar: (id: number | null) => void;
}) {
  return (
    <>
      <tr className="text-stone-800">
        <td className="whitespace-nowrap px-4 py-2.5 tabular-nums">{fecha(g.fecha)}</td>
        <td className="max-w-xs px-3 py-2.5">
          <div className="truncate">{g.descripcion || "—"}</div>
          <div className="text-xs text-stone-600">
            {g.usuario_nombre}
            {g.foto && (
              <>
                {" · "}
                <EnlaceFoto foto={g.foto} />
              </>
            )}
          </div>
        </td>
        <td className="whitespace-nowrap px-3 py-2.5">{TIPOS_GASTO[g.tipo]}</td>
        <td className="px-3 py-2.5">{g.partida_nombre}</td>
        <td className="px-3 py-2.5">{g.con_factura ? "Sí" : <Pildora tono="neutro">No</Pildora>}</td>
        <td className="whitespace-nowrap px-3 py-2.5 text-right font-medium tabular-nums text-stone-900">{dinero(g.monto, moneda)}</td>
        <td className="px-4 py-2.5 text-right">
          <button className="font-medium text-stone-600 underline hover:text-stone-900" onClick={() => alternar(abierto ? null : g.id)}>
            Anular
          </button>
        </td>
      </tr>
      {abierto && (
        <tr>
          <td colSpan={7} className="px-4 pb-3">
            <FormAnular gasto={g} cerrar={() => alternar(null)} />
          </td>
        </tr>
      )}
    </>
  );
}

function FormAnular({ gasto, cerrar }: { gasto: Gasto; cerrar: () => void }) {
  const [motivo, setMotivo] = useState("");
  const cliente = useQueryClient();
  const anular = useMutation({
    mutationFn: () => api<Gasto>(`/api/gastos/${gasto.id}/anular`, "POST", { motivo }),
    onSuccess: () => {
      cliente.invalidateQueries();
      avisar("Gasto anulado");
      cerrar();
    },
  });

  function enviar(e: FormEvent) {
    e.preventDefault();
    anular.mutate();
  }

  return (
    <form onSubmit={enviar} className="mt-3 space-y-3 rounded-xl border border-red-200 bg-red-50 p-3">
      <Campo etiqueta="¿Por qué se anula este gasto?">
        <Entrada value={motivo} onChange={(e) => setMotivo(e.target.value)} minLength={3} required autoFocus placeholder="Registrado dos veces" />
      </Campo>
      <MensajeError error={anular.error} />
      <div className="flex gap-2">
        <Boton type="submit" variante="peligro" disabled={anular.isPending}>
          {anular.isPending ? "Anulando…" : "Anular gasto"}
        </Boton>
        <Boton type="button" variante="secundario" onClick={cerrar}>
          Cancelar
        </Boton>
      </div>
    </form>
  );
}
