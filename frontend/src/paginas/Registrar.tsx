import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { registrar } from "../cola";
import { bs, hoyISO, leerMonto } from "../formato";
import { comprimirFoto } from "../fotos";
import { TIPOS_GASTO, type Partida, type TipoGasto } from "../tipos";
import { Marco } from "../componentes/Marco";
import { IconoCamara, IconoCerrar, IconoLadrillos } from "../componentes/iconos";
import {
  AreaTexto,
  avisar,
  Boton,
  BotonEnlace,
  Campo,
  Cargando,
  Entrada,
  EstadoVacio,
  Interruptor,
  MensajeError,
  OpcionGrande,
  Selector,
  Tarjeta,
} from "../componentes/ui";

function usePartidas(obraId: string | undefined) {
  return useQuery({
    queryKey: ["partidas", obraId],
    queryFn: () => api<Partida[]>(`/api/obras/${obraId}/partidas`),
  });
}

// La última partida usada viene marcada: en obra se suele registrar varias veces en la misma.
const clavePartida = (obraId: string) => `vc_partida_${obraId}`;

function ultimaPartida(obraId: string): number | null {
  try {
    const valor = localStorage.getItem(clavePartida(obraId));
    return valor ? Number(valor) : null;
  } catch {
    return null;
  }
}

function recordarPartida(obraId: string, partidaId: number) {
  try {
    localStorage.setItem(clavePartida(obraId), String(partidaId));
  } catch {
    /* sin memoria del celular: solo no se recuerda */
  }
}

/** Botón de foto a todo el ancho, con vista previa y opción de quitarla. */
function CampoFoto({ foto, cambiar, texto }: { foto: string | null; cambiar: (f: string | null) => void; texto: string }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<unknown>(null);

  async function elegir(archivo: File | undefined) {
    if (!archivo) return;
    setError(null);
    try {
      cambiar(await comprimirFoto(archivo));
    } catch (e) {
      setError(e);
    }
  }

  return (
    <div className="space-y-2">
      <input
        ref={entrada}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => elegir(e.target.files?.[0])}
      />
      {foto ? (
        <div className="flex items-center gap-3 rounded-xl border border-stone-300 bg-white p-2">
          <img src={foto} alt="Foto adjunta" className="h-16 w-16 rounded-lg object-cover" />
          <span className="flex-1 text-sm text-stone-700">Foto adjunta</span>
          <Boton type="button" variante="fantasma" onClick={() => cambiar(null)}>
            <IconoCerrar tamano={18} />
            Quitar
          </Boton>
        </div>
      ) : (
        <Boton type="button" variante="secundario" className="w-full" onClick={() => entrada.current?.click()}>
          <IconoCamara />
          {texto}
        </Boton>
      )}
      <MensajeError error={error} />
    </div>
  );
}

/** Barra fija sobre el menú inferior con el botón de guardar. */
function BarraGuardar({ children }: { children: ReactNode }) {
  return <div className="sticky bottom-[4.5rem] z-10 -mx-4 bg-stone-50/95 px-4 pb-1 pt-3 backdrop-blur">{children}</div>;
}

const ORDEN_TIPOS: TipoGasto[] = ["material", "mano_obra", "subcontrato", "caja_chica", "transporte"];

export function NuevoGasto() {
  const { obraId } = useParams();
  const navegar = useNavigate();
  const cliente = useQueryClient();
  const partidas = usePartidas(obraId);
  const [monto, setMonto] = useState("");
  const [tipo, setTipo] = useState<TipoGasto>("material");
  const [partidaId, setPartidaId] = useState<number | null>(() => ultimaPartida(obraId!));
  const [descripcion, setDescripcion] = useState("");
  const [conFactura, setConFactura] = useState(false);
  const [foto, setFoto] = useState<string | null>(null);
  const [dia, setDia] = useState(hoyISO());
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  const valor = Number(leerMonto(monto) ?? 0) || 0;
  const lista = partidas.data ?? [];
  // Si la partida recordada ya no existe se registra en gastos generales.
  const partidaValida = lista.some((p) => p.id === partidaId) ? partidaId : null;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (valor <= 0) {
      setError(new Error("Escribe el monto del gasto"));
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      const cuerpo = {
        fecha: dia,
        monto: leerMonto(monto),
        tipo,
        partida_id: partidaValida,
        descripcion,
        con_factura: conFactura,
        foto_base64: foto,
      };
      const texto = `${TIPOS_GASTO[tipo]} ${bs(valor)}${descripcion ? ` · ${descripcion}` : ""}`;
      const resultado = await registrar(`/api/obras/${obraId}/gastos`, cuerpo, texto);
      if (partidaValida !== null) recordarPartida(obraId!, partidaValida);
      cliente.invalidateQueries({ queryKey: ["dia", obraId] });
      cliente.invalidateQueries({ queryKey: ["obras"] });
      avisar(resultado === "enviado" ? `Gasto guardado · ${bs(valor)}` : "Guardado en el celular · se enviará con señal");
      navegar(`/obras/${obraId}/hoy`);
    } catch (err) {
      setError(err);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Nuevo gasto" volver={`/obras/${obraId}/hoy`}>
      <form onSubmit={enviar} className="space-y-4">
        <Tarjeta className="space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-stone-800">Monto</span>
            <div className="flex items-center rounded-xl border border-stone-300 bg-white focus-within:border-marca-500 focus-within:ring-2 focus-within:ring-marca-500/30">
              <span className="pl-4 text-2xl font-semibold text-stone-500">Bs</span>
              <input
                inputMode="decimal"
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
                placeholder="0,00"
                autoFocus
                className="min-h-16 w-full rounded-xl bg-transparent px-3 text-3xl font-semibold tabular-nums text-stone-900 placeholder:text-stone-300 focus:outline-none"
                aria-label="Monto en bolivianos"
              />
            </div>
          </label>

          <fieldset>
            <legend className="mb-1.5 text-sm font-medium text-stone-800">Tipo de gasto</legend>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {ORDEN_TIPOS.map((t) => (
                <OpcionGrande key={t} activo={tipo === t} onClick={() => setTipo(t)}>
                  {TIPOS_GASTO[t]}
                </OpcionGrande>
              ))}
            </div>
          </fieldset>

          <Campo etiqueta="Partida">
            {partidas.isLoading ? (
              <div className="h-12 animate-pulse rounded-xl bg-stone-100" />
            ) : (
              <Selector
                value={partidaValida ?? ""}
                onChange={(e) => setPartidaId(e.target.value ? Number(e.target.value) : null)}
              >
                {!lista.some((p) => p.es_generales) && <option value="">Gastos generales</option>}
                {lista.map((p) => (
                  <option key={p.id} value={p.es_generales ? "" : p.id}>
                    {p.codigo ? `${p.codigo} · ` : ""}
                    {p.nombre}
                  </option>
                ))}
              </Selector>
            )}
          </Campo>
        </Tarjeta>

        <Tarjeta className="space-y-4">
          <Campo etiqueta="Descripción (opcional)">
            <AreaTexto value={descripcion} onChange={(e) => setDescripcion(e.target.value)} placeholder="Cemento, 10 bolsas" />
          </Campo>
          <Interruptor etiqueta="Tiene factura" activo={conFactura} cambiar={setConFactura} />
          <CampoFoto foto={foto} cambiar={setFoto} texto="Foto del comprobante" />
          <Campo etiqueta="Fecha">
            <Entrada type="date" value={dia} max={hoyISO()} onChange={(e) => setDia(e.target.value || hoyISO())} />
          </Campo>
        </Tarjeta>

        <MensajeError error={error} />
        <BarraGuardar>
          <Boton type="submit" grande className="w-full" disabled={enviando}>
            {enviando ? "Guardando…" : valor > 0 ? `Guardar ${bs(valor)}` : "Guardar gasto"}
          </Boton>
        </BarraGuardar>
      </form>
    </Marco>
  );
}

export function NuevoAvance() {
  const { obraId } = useParams();
  const navegar = useNavigate();
  const cliente = useQueryClient();
  const partidas = usePartidas(obraId);
  const [partidaId, setPartidaId] = useState<number | null>(null);
  const [porcentaje, setPorcentaje] = useState(0);
  const [nota, setNota] = useState("");
  const [foto, setFoto] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  const lista = (partidas.data ?? []).filter((p) => !p.es_generales);
  const elegida = lista.find((p) => p.id === partidaId);

  function elegir(p: Partida) {
    setPartidaId(p.id);
    setPorcentaje(Math.round(p.porcentaje_avance));
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!elegida) return;
    setEnviando(true);
    setError(null);
    try {
      const resultado = await registrar(
        `/api/partidas/${elegida.id}/avances`,
        { porcentaje, nota, foto_base64: foto },
        `Avance ${elegida.nombre}: ${porcentaje} %`,
      );
      cliente.invalidateQueries({ queryKey: ["partidas", obraId] });
      cliente.invalidateQueries({ queryKey: ["obras"] });
      avisar(resultado === "enviado" ? `Avance guardado · ${elegida.nombre} ${porcentaje} %` : "Guardado en el celular · se enviará con señal");
      navegar(`/obras/${obraId}/hoy`);
    } catch (err) {
      setError(err);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Nuevo avance" volver={`/obras/${obraId}/hoy`}>
      {partidas.isLoading && <Cargando />}
      <MensajeError error={partidas.error} reintentar={() => partidas.refetch()} />
      {partidas.data && lista.length === 0 && (
        <Tarjeta>
          <EstadoVacio
            icono={<IconoLadrillos tamano={28} />}
            texto="Esta obra todavía no tiene partidas para registrar avance."
            accion={
              <BotonEnlace a={`/obras/${obraId}/hoy`} variante="secundario">
                Volver
              </BotonEnlace>
            }
          />
        </Tarjeta>
      )}
      {lista.length > 0 && (
        <form onSubmit={enviar} className="space-y-4">
          <Tarjeta className="space-y-2">
            <h2 className="text-sm font-medium text-stone-800">¿Qué partida avanzó?</h2>
            <div className="space-y-2">
              {lista.map((p) => {
                const activo = p.id === partidaId;
                return (
                  <button
                    key={p.id}
                    type="button"
                    aria-pressed={activo}
                    onClick={() => elegir(p)}
                    className={`flex min-h-14 w-full items-center justify-between gap-3 rounded-xl border px-3 text-left transition active:scale-[0.99] ${
                      activo ? "border-marca-600 bg-marca-50 ring-1 ring-marca-600" : "border-stone-300 bg-white hover:bg-stone-50"
                    }`}
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-medium text-stone-900">{p.nombre}</span>
                      {p.fase && <span className="block truncate text-sm text-stone-600">{p.fase}</span>}
                    </span>
                    <span className="shrink-0 text-sm font-semibold tabular-nums text-stone-700">
                      {Math.round(p.porcentaje_avance)} %
                    </span>
                  </button>
                );
              })}
            </div>
          </Tarjeta>

          {elegida && (
            <Tarjeta className="space-y-4">
              <div className="text-center">
                <p className="text-sm text-stone-600">{elegida.nombre}</p>
                <p className="text-5xl font-semibold tracking-tight tabular-nums text-stone-900">{porcentaje} %</p>
                <p className="mt-1 text-sm tabular-nums text-stone-600">
                  Antes: {Math.round(elegida.porcentaje_avance)} % → Ahora: {porcentaje} %
                </p>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={porcentaje}
                onChange={(e) => setPorcentaje(Number(e.target.value))}
                aria-label="Porcentaje de avance"
              />
              <div className="grid grid-cols-4 gap-2">
                {[25, 50, 75, 100].map((v) => (
                  <OpcionGrande key={v} activo={porcentaje === v} onClick={() => setPorcentaje(v)}>
                    {v} %
                  </OpcionGrande>
                ))}
              </div>
              <Campo etiqueta="Nota (opcional)">
                <AreaTexto value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Muro del 2do piso" />
              </Campo>
              <CampoFoto foto={foto} cambiar={setFoto} texto="Foto del avance" />
            </Tarjeta>
          )}

          <MensajeError error={error} />
          <BarraGuardar>
            <Boton type="submit" grande className="w-full" disabled={!elegida || enviando}>
              {enviando ? "Guardando…" : elegida ? `Guardar avance ${porcentaje} %` : "Elige una partida"}
            </Boton>
          </BarraGuardar>
        </form>
      )}
    </Marco>
  );
}
