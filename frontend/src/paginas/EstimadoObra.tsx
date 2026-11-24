import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, descargar } from "../api";
import { dinero, fecha, fechaCorta, hoyISO, leerMonto } from "../formato";
import type { ActividadEstimada, BaseEstimado, EstadoEntregable, EstimadoObra, ParametrosApu, SemanaPv } from "../tipos";
import {
  AreaTexto,
  Boton,
  Campo,
  Cargando,
  Entrada,
  MensajeError,
  Metrica,
  Pildora,
  Selector,
  Tarjeta,
  avisar,
} from "../componentes/ui";

// Kit TCM (AACE): estimado con APU y clase (17R-97 / 56R-08), base del estimado (34R-05) y línea base.

export function useEstimado(obraId: string) {
  return useQuery({
    queryKey: ["estimado", obraId],
    queryFn: () => api<EstimadoObra>(`/api/obras/${obraId}/estimado`),
  });
}

function useGuardar(obraId: string) {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ ruta, metodo, cuerpo }: { ruta: string; metodo: string; cuerpo: unknown }) =>
      api<EstimadoObra>(ruta, metodo, cuerpo),
    onSuccess: (e) => {
      cliente.setQueryData(["estimado", obraId], e);
      // El presupuesto de las partidas y los indicadores pueden cambiar.
      cliente.invalidateQueries({ queryKey: ["cronograma", obraId] });
      cliente.invalidateQueries({ queryKey: ["indicadores", obraId] });
      cliente.invalidateQueries({ queryKey: ["obras"] });
    },
  });
}

function BotonExportar({ obraId }: { obraId: string }) {
  const exportar = useMutation({
    mutationFn: () => descargar(`/api/obras/${obraId}/estimado.xlsx`, `estimado-obra-${obraId}.xlsx`),
  });
  return (
    <>
      <Boton variante="secundario" onClick={() => exportar.mutate()} disabled={exportar.isPending}>
        {exportar.isPending ? "Exportando…" : "Exportar a Excel"}
      </Boton>
      <MensajeError error={exportar.error} />
    </>
  );
}

function Contenedor({ obraId, children }: { obraId: string; children: (e: EstimadoObra) => ReactNode }) {
  const estimado = useEstimado(obraId);
  if (estimado.isLoading) return <Cargando filas={3} />;
  if (!estimado.data) return <MensajeError error={estimado.error} reintentar={() => estimado.refetch()} />;
  return <>{children(estimado.data)}</>;
}

const ESTADOS: { valor: EstadoEntregable; texto: string }[] = [
  { valor: "no", texto: "No hay" },
  { valor: "parcial", texto: "Parcial" },
  { valor: "completo", texto: "Completo" },
];

function rango(c: { exactitud_baja: number[]; exactitud_alta: number[] }): string {
  return `${c.exactitud_baja[0]} % a ${c.exactitud_baja[1]} % / +${c.exactitud_alta[0]} % a +${c.exactitud_alta[1]} %`;
}

// --- Pestaña Estimado ---

export function VistaEstimado({ obraId }: { obraId: string }) {
  return <Contenedor obraId={obraId}>{(e) => <Estimado obraId={obraId} e={e} />}</Contenedor>;
}

function Estimado({ obraId, e }: { obraId: string; e: EstimadoObra }) {
  const m = e.obra.moneda;
  const t = e.totales;
  const vacio = e.fases.every((f) => f.actividades.length === 0);
  return (
    <>
      <Clasificacion obraId={obraId} e={e} />

      <Tarjeta className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-stone-900">Total del estimado</h2>
            <p className="text-sm text-stone-600">Suma de los APU de todas las actividades (precio de venta).</p>
          </div>
          <BotonExportar obraId={obraId} />
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Metrica etiqueta="Total" valor={dinero(t.total, m)} grande />
          <Metrica etiqueta="Costo directo" valor={dinero(t.costo_directo, m)} />
          <Metrica etiqueta="Gastos generales" valor={dinero(t.gastos_generales, m)} />
          <Metrica etiqueta="Utilidad" valor={dinero(t.utilidad, m)} />
          <Metrica etiqueta="Impuestos (IT)" valor={dinero(t.impuestos, m)} />
        </div>
      </Tarjeta>

      <Parametros obraId={obraId} p={e.parametros} />

      <h2 className="pt-2 text-lg font-semibold tracking-tight text-stone-900">WBS → actividades → APU</h2>
      {vacio && (
        <Tarjeta>
          <p className="text-sm text-stone-600">
            Todavía no hay actividades. Cárgalas en la pestaña Cronograma o importa la obra desde la plantilla Excel del
            kit (Obras → Importar desde Excel).
          </p>
        </Tarjeta>
      )}
      {e.fases.map((f, i) =>
        f.actividades.length === 0 ? null : (
          <Tarjeta key={f.id} className="p-0">
            <div className="flex items-baseline justify-between gap-3 border-b border-stone-100 px-4 py-3">
              <h3 className="font-semibold text-stone-900">
                <span className="mr-2 tabular-nums text-stone-500">{i + 1}</span>
                {f.nombre}
              </h3>
              <span className="font-semibold tabular-nums text-stone-900">{dinero(f.total, m)}</span>
            </div>
            <ul className="divide-y divide-stone-100">
              {f.actividades.map((a) => (
                <FilaActividad key={a.id} a={a} moneda={m} />
              ))}
            </ul>
          </Tarjeta>
        ),
      )}
    </>
  );
}

function Clasificacion({ obraId, e }: { obraId: string; e: EstimadoObra }) {
  const guardar = useGuardar(obraId);
  const c = e.clasificacion;
  const m = e.obra.moneda;
  const [verTabla, setVerTabla] = useState(false);

  function cambiar(clave: string, estado: EstadoEntregable) {
    guardar.mutate({
      ruta: `/api/obras/${obraId}/estimado/clasificacion`,
      metodo: "PUT",
      cuerpo: { entregables: { [clave]: estado } },
    });
  }

  return (
    <Tarjeta className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-stone-900">Clasificación del estimado</h2>
          <p className="text-sm text-stone-600">AACE 56R-08 (edificación), marco 17R-97. Marca qué entregables tienes.</p>
        </div>
        <Pildora tono="neutro" punto={false}>
          Clase {c.clase.clase}
        </Pildora>
      </div>

      <ul className="divide-y divide-stone-100">
        {c.entregables.map((en) => (
          <li key={en.clave} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span className="min-w-0 flex-1 basis-48 text-sm text-stone-800">
              {en.nombre} <span className="tabular-nums text-stone-500">· {en.peso} %</span>
            </span>
            <Selector
              aria-label={en.nombre}
              className="w-36"
              value={en.estado}
              disabled={guardar.isPending}
              onChange={(ev) => cambiar(en.clave, ev.target.value as EstadoEntregable)}
            >
              {ESTADOS.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.texto}
                </option>
              ))}
            </Selector>
          </li>
        ))}
      </ul>
      <MensajeError error={guardar.error} />

      <div className="grid grid-cols-2 gap-4 rounded-xl bg-stone-50 p-3 sm:grid-cols-4">
        <Metrica etiqueta="Definición" valor={`${c.porcentaje_definicion.toLocaleString("es-BO")} %`} />
        <Metrica etiqueta="Clase" valor={c.clase.clase} detalle={`Norma: ${c.clase.definicion_norma}`} />
        <Metrica etiqueta="Mínimo probable" valor={dinero(c.minimo, m)} />
        <Metrica etiqueta="Máximo probable" valor={dinero(c.maximo, m)} />
      </div>
      <dl className="grid gap-2 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-stone-600">Uso típico</dt>
          <dd className="text-stone-900">{c.clase.uso}</dd>
        </div>
        <div>
          <dt className="text-stone-600">Metodología típica</dt>
          <dd className="text-stone-900">{c.clase.metodologia}</dd>
        </div>
        <div>
          <dt className="text-stone-600">Exactitud</dt>
          <dd className="tabular-nums text-stone-900">{rango(c.clase)}</dd>
        </div>
      </dl>

      <button
        type="button"
        className="min-h-10 text-sm font-medium text-stone-700 underline-offset-2 hover:underline"
        onClick={() => setVerTabla(!verTabla)}
      >
        {verTabla ? "Ocultar tabla de clases" : "Ver tabla de clases"}
      </button>
      {verTabla && (
        <div className="overflow-x-auto rounded-xl border border-stone-200">
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-left text-xs font-medium uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-3 py-2">Clase</th>
                <th className="px-3 py-2">Definición</th>
                <th className="px-3 py-2">Uso</th>
                <th className="px-3 py-2">Exactitud</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {c.clases.map((k) => (
                <tr key={k.clase} className={k.clase === c.clase.clase ? "bg-marca-50/60 font-medium" : ""}>
                  <td className="px-3 py-2 tabular-nums">{k.clase}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{k.definicion_norma}</td>
                  <td className="px-3 py-2">{k.uso}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{rango(k)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-3 py-2 text-xs text-stone-600">
            Valores editables en el archivo de configuración del kit (clases_estimado.toml).
          </p>
        </div>
      )}
    </Tarjeta>
  );
}

const CAMPOS_APU: { clave: keyof ParametrosApu; texto: string }[] = [
  { clave: "cargas_sociales", texto: "Cargas sociales (% m. de obra)" },
  { clave: "iva_mano_obra", texto: "IVA de la mano de obra (%)" },
  { clave: "herramientas", texto: "Herramientas menores (% m. de obra)" },
  { clave: "gastos_generales", texto: "Gastos generales (%)" },
  { clave: "utilidad", texto: "Utilidad (%)" },
  { clave: "impuestos", texto: "Impuestos IT (%)" },
];

function aTexto(n: number): string {
  return String(n).replace(".", ",");
}

function Parametros({ obraId, p }: { obraId: string; p: ParametrosApu }) {
  const guardar = useGuardar(obraId);
  const [valores, setValores] = useState<Record<keyof ParametrosApu, string>>(
    () => Object.fromEntries(CAMPOS_APU.map((c) => [c.clave, aTexto(p[c.clave])])) as Record<keyof ParametrosApu, string>,
  );
  useEffect(() => {
    setValores(Object.fromEntries(CAMPOS_APU.map((c) => [c.clave, aTexto(p[c.clave])])) as Record<keyof ParametrosApu, string>);
  }, [p]);

  function enviar(ev: FormEvent) {
    ev.preventDefault();
    const cuerpo = Object.fromEntries(CAMPOS_APU.map((c) => [c.clave, leerMonto(valores[c.clave]) ?? "0"]));
    guardar.mutate(
      { ruta: `/api/obras/${obraId}/estimado/parametros`, metodo: "PUT", cuerpo },
      { onSuccess: () => avisar("Porcentajes guardados: presupuesto recalculado") },
    );
  }

  return (
    <Tarjeta>
      <form onSubmit={enviar} className="space-y-4">
        <div>
          <h2 className="font-semibold text-stone-900">Porcentajes del APU de esta obra</h2>
          <p className="text-sm text-stone-600">
            Se aplican a todas las actividades. Cambiarlos recalcula el presupuesto del plan, no la línea base aprobada.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {CAMPOS_APU.map((c) => (
            <Campo key={c.clave} etiqueta={c.texto}>
              <Entrada
                inputMode="decimal"
                className="text-right tabular-nums"
                value={valores[c.clave]}
                onChange={(ev) => setValores({ ...valores, [c.clave]: ev.target.value })}
              />
            </Campo>
          ))}
        </div>
        <Boton type="submit" variante="secundario" disabled={guardar.isPending}>
          {guardar.isPending ? "Guardando…" : "Guardar porcentajes"}
        </Boton>
        <MensajeError error={guardar.error} />
      </form>
    </Tarjeta>
  );
}

const NOMBRE_TIPO = { material: "Material", mano_obra: "Mano de obra", equipo: "Equipo" } as const;

function FilaActividad({ a, moneda }: { a: ActividadEstimada; moneda: string }) {
  const [abierta, setAbierta] = useState(false);
  const p = a.apu;
  const lineas: [string, number][] = [
    ["Materiales", p.materiales],
    ["Mano de obra", p.mano_obra],
    ["Cargas sociales", p.cargas_sociales],
    ["IVA de la mano de obra", p.iva_mano_obra],
    ["Equipo", p.equipo],
    ["Herramientas menores", p.herramientas],
    ["Costo directo", p.costo_directo],
    ["Gastos generales", p.gastos_generales],
    ["Utilidad", p.utilidad],
    ["Impuestos (IT)", p.impuestos],
  ];
  return (
    <li>
      <button
        type="button"
        onClick={() => setAbierta(!abierta)}
        aria-expanded={abierta}
        className="flex min-h-12 w-full items-center gap-3 px-4 py-2.5 text-left transition hover:bg-stone-50"
      >
        <span className="w-10 shrink-0 font-mono text-xs text-stone-500">{a.codigo}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm text-stone-900">{a.nombre}</span>
          <span className="block text-xs tabular-nums text-stone-600">
            {a.computo !== null ? `${a.computo.toLocaleString("es-BO")} ${a.unidad}` : "Sin cómputo"}
            {a.precio_unitario !== null && ` · P.U. ${dinero(a.precio_unitario, moneda)}`}
          </span>
        </span>
        <span className="whitespace-nowrap text-sm font-semibold tabular-nums text-stone-900">{dinero(p.total, moneda)}</span>
      </button>
      {abierta && (
        <div className="space-y-3 bg-stone-50/70 px-4 pb-4 pt-1">
          {a.insumos.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs font-medium uppercase tracking-wider text-stone-500">
                  <tr>
                    <th className="py-1.5 pr-3">Insumo</th>
                    <th className="py-1.5 pr-3 text-right">Por unidad</th>
                    <th className="py-1.5 pr-3 text-right">Cantidad</th>
                    <th className="py-1.5 pr-3 text-right">Precio</th>
                    <th className="py-1.5 text-right">Parcial</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200/70">
                  {a.insumos.map((r, i) => (
                    <tr key={i}>
                      <td className="py-1.5 pr-3">
                        {r.descripcion} <span className="text-xs text-stone-500">· {NOMBRE_TIPO[r.tipo]}</span>
                      </td>
                      <td className="whitespace-nowrap py-1.5 pr-3 text-right tabular-nums">
                        {r.rendimiento !== null ? `${r.rendimiento.toLocaleString("es-BO")} ${r.unidad}` : "—"}
                      </td>
                      <td className="whitespace-nowrap py-1.5 pr-3 text-right tabular-nums">
                        {r.cantidad.toLocaleString("es-BO")} {r.unidad}
                      </td>
                      <td className="whitespace-nowrap py-1.5 pr-3 text-right tabular-nums">{dinero(r.precio_unitario, moneda)}</td>
                      <td className="whitespace-nowrap py-1.5 text-right tabular-nums">{dinero(r.parcial, moneda)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            {lineas.map(([texto, valor]) => (
              <div key={texto} className={`flex justify-between ${texto === "Costo directo" ? "font-semibold" : ""}`}>
                <dt className="text-stone-600">{texto}</dt>
                <dd className="tabular-nums text-stone-900">{dinero(valor, moneda)}</dd>
              </div>
            ))}
            <div className="flex justify-between border-t border-stone-200 pt-1 font-semibold sm:col-span-2">
              <dt>Total de la actividad</dt>
              <dd className="tabular-nums">{dinero(p.total, moneda)}</dd>
            </div>
          </dl>
        </div>
      )}
    </li>
  );
}

// --- Pestaña Base del estimado ---

const CAMPOS_BASE: { clave: keyof BaseEstimado; texto: string; ayuda: string }[] = [
  { clave: "proposito", texto: "Propósito del estimado", ayuda: "Para qué se hizo: precio de contrato, licitación, factibilidad…" },
  { clave: "alcance", texto: "Alcance", ayuda: "Qué obra se estima: superficie, sistema constructivo, partes incluidas." },
  { clave: "metodologia", texto: "Metodología", ayuda: "Cómo se calculó: APU, costo por m², porcentajes usados." },
  { clave: "base_diseno", texto: "Base de diseño", ayuda: "Planos y documentos usados, y su grado de avance." },
  { clave: "base_planificacion", texto: "Base de planificación", ayuda: "Cómo se ejecutará: inicio, cuadrillas, jornada." },
  { clave: "fuentes_precios", texto: "Fuentes de precios", ayuda: "Ferreterías, cotizaciones, obras anteriores." },
  { clave: "supuestos", texto: "Supuestos", ayuda: "Lo que se da por cierto (suelo, accesos, precios estables)." },
  { clave: "exclusiones", texto: "Exclusiones", ayuda: "Lo que NO incluye el estimado." },
  { clave: "riesgos_oportunidades", texto: "Riesgos y oportunidades", ayuda: "Lo que podría subir o bajar el costo." },
  { clave: "contingencia_nota", texto: "Contingencia: criterio", ayuda: "Por qué ese porcentaje." },
];

export function VistaBase({ obraId }: { obraId: string }) {
  return <Contenedor obraId={obraId}>{(e) => <FormBase obraId={obraId} e={e} />}</Contenedor>;
}

function FormBase({ obraId, e }: { obraId: string; e: EstimadoObra }) {
  const guardar = useGuardar(obraId);
  const [b, setB] = useState(e.base);
  const [contingencia, setContingencia] = useState(aTexto(e.base.contingencia_porcentaje));
  useEffect(() => {
    setB(e.base);
    setContingencia(aTexto(e.base.contingencia_porcentaje));
  }, [e.base]);

  function enviar(ev: FormEvent) {
    ev.preventDefault();
    const { contingencia_monto: _monto, ...resto } = b;
    guardar.mutate(
      {
        ruta: `/api/obras/${obraId}/estimado/base`,
        metodo: "PUT",
        cuerpo: { ...resto, fecha_precios: b.fecha_precios || null, contingencia_porcentaje: leerMonto(contingencia) ?? "0" },
      },
      { onSuccess: () => avisar("Base del estimado guardada") },
    );
  }

  return (
    <form onSubmit={enviar} className="space-y-4">
      <Tarjeta className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 basis-60">
          <h2 className="font-semibold text-stone-900">Base del estimado</h2>
          <p className="text-sm text-stone-600">
            AACE 34R-05: documenta cómo se armó el estimado para que otro lo entienda y lo pueda revisar.
          </p>
        </div>
        <BotonExportar obraId={obraId} />
      </Tarjeta>
      <Tarjeta className="space-y-4">
        {CAMPOS_BASE.slice(0, 6).map((c) => (
          <Campo key={c.clave} etiqueta={c.texto} ayuda={c.ayuda}>
            <AreaTexto rows={3} value={String(b[c.clave] ?? "")} onChange={(ev) => setB({ ...b, [c.clave]: ev.target.value })} />
          </Campo>
        ))}
        <Campo etiqueta="Fecha de los precios">
          <Entrada type="date" value={b.fecha_precios ?? ""} onChange={(ev) => setB({ ...b, fecha_precios: ev.target.value || null })} />
        </Campo>
        {CAMPOS_BASE.slice(6, 9).map((c) => (
          <Campo key={c.clave} etiqueta={c.texto} ayuda={c.ayuda}>
            <AreaTexto rows={3} value={String(b[c.clave] ?? "")} onChange={(ev) => setB({ ...b, [c.clave]: ev.target.value })} />
          </Campo>
        ))}
        <div className="grid gap-3 sm:grid-cols-2">
          <Campo etiqueta="Contingencia (% del estimado)">
            <Entrada inputMode="decimal" className="text-right tabular-nums" value={contingencia} onChange={(ev) => setContingencia(ev.target.value)} />
          </Campo>
          <Metrica etiqueta="Monto de contingencia (guardado)" valor={dinero(e.base.contingencia_monto, e.obra.moneda)} />
        </div>
        <Campo etiqueta={CAMPOS_BASE[9].texto} ayuda={CAMPOS_BASE[9].ayuda}>
          <AreaTexto rows={2} value={b.contingencia_nota} onChange={(ev) => setB({ ...b, contingencia_nota: ev.target.value })} />
        </Campo>
        <Boton type="submit" grande className="w-full" disabled={guardar.isPending}>
          {guardar.isPending ? "Guardando…" : "Guardar base del estimado"}
        </Boton>
        <MensajeError error={guardar.error} />
      </Tarjeta>
    </form>
  );
}

// --- Pestaña Línea base ---

export function VistaLineaBase({ obraId }: { obraId: string }) {
  return <Contenedor obraId={obraId}>{(e) => <LineaBase obraId={obraId} e={e} />}</Contenedor>;
}

function LineaBase({ obraId, e }: { obraId: string; e: EstimadoObra }) {
  const guardar = useGuardar(obraId);
  const [motivo, setMotivo] = useState("");
  const v = e.vigente;
  const m = e.obra.moneda;
  const puedeAprobar = e.totales.total > 0;

  function aprobar(ev: FormEvent) {
    ev.preventDefault();
    guardar.mutate(
      { ruta: `/api/obras/${obraId}/lineas-base`, metodo: "POST", cuerpo: { motivo } },
      {
        onSuccess: (r) => {
          setMotivo("");
          avisar(`Línea base v${r.vigente?.version} aprobada`);
        },
      },
    );
  }

  return (
    <>
      {(!v || e.plan_distinto_de_base) && (
        <Tarjeta>
          <form onSubmit={aprobar} className="space-y-3">
            <h2 className="font-semibold text-stone-900">{v ? "El plan cambió desde la línea base" : "Aprobar línea base"}</h2>
            <p className="text-sm text-stone-600">
              {v
                ? `El presupuesto o las fechas ya no coinciden con la v${v.version}. El valor ganado sigue midiendo contra la v${v.version} hasta que apruebes una nueva versión.`
                : "Congela el presupuesto y las fechas actuales. Desde ese momento el valor ganado mide contra esta foto, aunque después edites el plan. No se puede modificar: cada cambio crea otra versión."}
            </p>
            <Campo etiqueta="Motivo">
              <Entrada value={motivo} onChange={(ev) => setMotivo(ev.target.value)} placeholder={v ? "Cambio aprobado por el cliente" : "Contrato firmado"} />
            </Campo>
            <Boton type="submit" disabled={guardar.isPending || !puedeAprobar}>
              {guardar.isPending ? "Aprobando…" : v ? `Aprobar versión ${v.version + 1}` : "Aprobar línea base"}
            </Boton>
            {!puedeAprobar && <p className="text-sm text-amber-800">Primero carga el estimado: la obra no tiene presupuesto.</p>}
            <MensajeError error={guardar.error} />
          </form>
        </Tarjeta>
      )}

      {v && (
        <>
          <Tarjeta className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold text-stone-900">Línea base vigente: versión {v.version}</h2>
                <p className="text-sm text-stone-600">
                  Aprobada el <span className="tabular-nums">{fecha(v.aprobada_en)}</span>
                  {v.aprobada_por_nombre && ` por ${v.aprobada_por_nombre}`}
                  {v.motivo && ` · ${v.motivo}`}
                </p>
              </div>
              <BotonExportar obraId={obraId} />
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Metrica etiqueta="BAC" valor={dinero(v.bac, m)} />
              <Metrica etiqueta="Inicio" valor={fecha(v.fecha_inicio)} />
              <Metrica etiqueta="Fin" valor={fecha(v.fecha_fin)} />
              <Metrica etiqueta="Clase al aprobar" valor={v.clase ?? "—"} />
            </div>
          </Tarjeta>

          <Tarjeta>
            <h2 className="mb-1 font-semibold text-stone-900">Curva S de la línea base</h2>
            <p className="mb-3 text-sm text-stone-600">Valor planificado (PV) acumulado por semana.</p>
            <CurvaPlan semanas={v.semanas} moneda={m} />
          </Tarjeta>

          <Tarjeta className="p-0">
            <h2 className="border-b border-stone-100 px-4 py-3 font-semibold text-stone-900">PV semanal</h2>
            <div className="max-h-[28rem] overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-stone-50 text-xs font-medium uppercase tracking-wider text-stone-500">
                  <tr>
                    <th className="px-4 py-2 text-left">Semana</th>
                    <th className="px-3 py-2 text-right">PV semana</th>
                    <th className="px-3 py-2 text-right">PV acumulado</th>
                    <th className="px-4 py-2 text-right">%</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {v.semanas.map((s) => (
                    <tr key={s.numero}>
                      <td className="whitespace-nowrap px-4 py-2 tabular-nums text-stone-700">
                        {s.numero} <span className="text-xs text-stone-500">· {fechaCorta(s.inicio)}–{fechaCorta(s.fin)}</span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{dinero(s.pv, m)}</td>
                      <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{dinero(s.pv_acumulado, m)}</td>
                      <td className="whitespace-nowrap px-4 py-2 text-right tabular-nums">
                        {s.porcentaje_acumulado === null ? "—" : `${s.porcentaje_acumulado.toLocaleString("es-BO")} %`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Tarjeta>
        </>
      )}

      {e.lineas_base.length > 0 && (
        <Tarjeta className="p-0">
          <h2 className="border-b border-stone-100 px-4 py-3 font-semibold text-stone-900">Versiones</h2>
          <ul className="divide-y divide-stone-100">
            {e.lineas_base.map((lb) => (
              <li key={lb.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <span className="min-w-0 flex-1">
                  <span className="font-medium text-stone-900">v{lb.version}</span>
                  <span className="tabular-nums text-stone-600"> · {fecha(lb.aprobada_en)}</span>
                  {lb.motivo && <span className="text-stone-600"> · {lb.motivo}</span>}
                </span>
                <span className="tabular-nums text-stone-900">{dinero(lb.bac, m)}</span>
                {lb.vigente ? <Pildora tono="bien">Vigente</Pildora> : <Pildora tono="neutro">Reemplazada</Pildora>}
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}
    </>
  );
}

const ANCHO = 640;
const ALTO = 240;
const M = { arriba: 12, derecha: 12, abajo: 28, izquierda: 56 };

function CurvaPlan({ semanas, moneda }: { semanas: SemanaPv[]; moneda: string }) {
  if (semanas.length === 0) return <p className="text-sm text-stone-600">La línea base no tiene partidas con fechas.</p>;
  const puntos = [{ x: 0, y: 0 }, ...semanas.map((s) => ({ x: s.numero, y: s.pv_acumulado }))];
  const maxX = semanas.length;
  const maxY = Math.max(1, semanas[semanas.length - 1].pv_acumulado) * 1.05;
  const px = (n: number) => M.izquierda + (n / maxX) * (ANCHO - M.izquierda - M.derecha);
  const py = (v: number) => ALTO - M.abajo - (v / maxY) * (ALTO - M.arriba - M.abajo);
  const camino = puntos.map((p, i) => `${i === 0 ? "M" : "L"}${px(p.x).toFixed(1)},${py(p.y).toFixed(1)}`).join(" ");
  const marcas = [0, 0.25, 0.5, 0.75, 1].map((f) => (maxY / 1.05) * f);
  const paso = Math.max(1, Math.ceil(maxX / 8));
  const hoy = hoyISO();
  const semanaHoy = semanas.find((s) => s.inicio <= hoy && hoy <= s.fin);

  return (
    <div>
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="h-auto w-full" role="img" aria-label="Curva S del valor planificado">
        {marcas.map((v) => (
          <g key={v}>
            <line x1={M.izquierda} x2={ANCHO - M.derecha} y1={py(v)} y2={py(v)} className="stroke-stone-200" />
            <text x={M.izquierda - 6} y={py(v) + 4} textAnchor="end" className="fill-stone-600 text-[11px] tabular-nums">
              {Math.round(v / 1000)}k
            </text>
          </g>
        ))}
        {semanas
          .filter((s) => s.numero % paso === 0 || s.numero === maxX)
          .map((s) => (
            <text key={s.numero} x={px(s.numero)} y={ALTO - 8} textAnchor="middle" className="fill-stone-600 text-[11px] tabular-nums">
              S{s.numero}
            </text>
          ))}
        {semanaHoy && (
          <line
            x1={px(semanaHoy.numero - 0.5)}
            x2={px(semanaHoy.numero - 0.5)}
            y1={M.arriba}
            y2={ALTO - M.abajo}
            className="stroke-stone-400"
            strokeDasharray="4 4"
          />
        )}
        <path d={camino} fill="none" className="stroke-stone-700" strokeWidth={2.5} />
        {puntos.slice(1).map((p) => (
          <circle key={p.x} cx={px(p.x)} cy={py(p.y)} r={2.5} className="fill-stone-700" />
        ))}
      </svg>
      <p className="mt-2 text-sm tabular-nums text-stone-700">
        {semanas.length} semanas · BAC distribuido {dinero(semanas[semanas.length - 1].pv_acumulado, moneda)}
      </p>
    </div>
  );
}
