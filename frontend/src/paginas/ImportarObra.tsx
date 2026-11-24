import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { descargar, subirArchivo } from "../api";
import { dinero, fecha } from "../formato";
import type { ObraImportada, ProblemaImportacion, VistaPrevia } from "../tipos";
import { Marco } from "../componentes/Marco";
import { Boton, MensajeError, Metrica, Pildora, Tarjeta, avisar } from "../componentes/ui";

/** Kit TCM: descargar la plantilla, subirla llena, revisar los errores fila por fila y confirmar. */
export function ImportarObra() {
  const navegar = useNavigate();
  const cliente = useQueryClient();
  const entrada = useRef<HTMLInputElement>(null);
  const [archivo, setArchivo] = useState<File | null>(null);

  const revisar = useMutation({
    mutationFn: (a: File) => subirArchivo<VistaPrevia>("/api/kit/importar/previa", a),
  });
  const confirmar = useMutation({
    mutationFn: (a: File) => subirArchivo<ObraImportada>("/api/kit/importar", a),
    onSuccess: (r) => {
      cliente.invalidateQueries({ queryKey: ["obras"] });
      avisar("Obra importada");
      navegar(`/obras/${r.obra.id}?vista=estimado`);
    },
  });
  const descarga = useMutation({
    mutationFn: () => descargar("/api/kit/plantilla.xlsx", "plantilla-kit-tcm.xlsx"),
  });

  function elegir(lista: FileList | null) {
    const a = lista?.[0];
    if (!a) return;
    setArchivo(a);
    confirmar.reset();
    revisar.mutate(a);
    if (entrada.current) entrada.current.value = "";
  }

  const previa = revisar.data;
  const r = previa?.resumen;

  return (
    <Marco titulo="Importar obra desde Excel" volver="/obras">
      <Tarjeta className="space-y-3">
        <h2 className="font-semibold text-stone-900">1. Descarga la plantilla del kit</h2>
        <p className="text-sm text-stone-600">
          Tiene hojas para los datos de la obra, la clasificación del estimado, las actividades, los insumos de cada
          APU y la base del estimado. Llena solo las celdas amarillas.
        </p>
        <Boton variante="secundario" onClick={() => descarga.mutate()} disabled={descarga.isPending}>
          {descarga.isPending ? "Descargando…" : "Descargar plantilla .xlsx"}
        </Boton>
        <MensajeError error={descarga.error} />
      </Tarjeta>

      <Tarjeta className="space-y-3">
        <h2 className="font-semibold text-stone-900">2. Sube la plantilla llena</h2>
        <p className="text-sm text-stone-600">Primero se revisa: no se graba nada hasta que confirmes.</p>
        <input
          ref={entrada}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="hidden"
          onChange={(e) => elegir(e.target.files)}
        />
        <Boton variante={previa?.valida ? "secundario" : "primario"} onClick={() => entrada.current?.click()} disabled={revisar.isPending}>
          {revisar.isPending ? "Revisando…" : archivo ? "Elegir otro archivo" : "Elegir archivo"}
        </Boton>
        {archivo && <p className="text-sm text-stone-600">Archivo: {archivo.name}</p>}
        <MensajeError error={revisar.error} />
      </Tarjeta>

      {previa && (
        <Tarjeta className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold text-stone-900">3. Revisión</h2>
            {previa.valida ? (
              <Pildora tono="bien">Sin errores</Pildora>
            ) : (
              <Pildora tono="problema">{previa.errores.length} error(es)</Pildora>
            )}
          </div>

          {r && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Metrica etiqueta="Obra" valor={<span className="text-base">{r.nombre || "—"}</span>} detalle={`Inicio ${fecha(r.fecha_inicio)}`} />
              <Metrica etiqueta="Total estimado" valor={dinero(r.total_estimado, r.moneda)} />
              <Metrica
                etiqueta="Clase del estimado"
                valor={`Clase ${r.clase}`}
                detalle={`${r.porcentaje_definicion.toLocaleString("es-BO")} % de definición`}
              />
              <Metrica etiqueta="Fases" valor={r.fases} />
              <Metrica etiqueta="Actividades" valor={r.actividades} />
              <Metrica etiqueta="Insumos" valor={r.insumos} />
            </div>
          )}

          {previa.errores.length > 0 && (
            <TablaProblemas titulo="Errores: corrígelos en el Excel y vuelve a subirlo" lista={previa.errores} tono="problema" />
          )}
          {previa.advertencias.length > 0 && (
            <TablaProblemas titulo="Advertencias (no impiden importar)" lista={previa.advertencias} tono="atencion" />
          )}

          {previa.valida && archivo && (
            <>
              <Boton grande className="w-full" onClick={() => confirmar.mutate(archivo)} disabled={confirmar.isPending}>
                {confirmar.isPending ? "Creando la obra…" : "Confirmar e importar"}
              </Boton>
              <MensajeError error={confirmar.error} />
            </>
          )}
        </Tarjeta>
      )}
    </Marco>
  );
}

function TablaProblemas({
  titulo,
  lista,
  tono,
}: {
  titulo: string;
  lista: ProblemaImportacion[];
  tono: "problema" | "atencion";
}) {
  return (
    <div>
      <h3 className={`mb-2 text-sm font-semibold ${tono === "problema" ? "text-red-700" : "text-amber-800"}`}>{titulo}</h3>
      <div className="overflow-x-auto rounded-xl border border-stone-200">
        <table className="w-full text-sm">
          <thead className="bg-stone-50 text-left text-xs font-medium uppercase tracking-wider text-stone-500">
            <tr>
              <th className="px-3 py-2">Hoja</th>
              <th className="px-3 py-2 text-right">Fila</th>
              <th className="px-3 py-2">Columna</th>
              <th className="px-3 py-2">Problema</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {lista.map((p, i) => (
              <tr key={i}>
                <td className="whitespace-nowrap px-3 py-2 text-stone-700">{p.hoja || "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums text-stone-700">{p.fila ?? "—"}</td>
                <td className="whitespace-nowrap px-3 py-2 text-stone-700">{p.columna || "—"}</td>
                <td className="px-3 py-2 text-stone-900">{p.mensaje}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
