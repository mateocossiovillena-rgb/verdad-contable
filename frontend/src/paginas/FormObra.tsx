import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { hoyISO } from "../formato";
import type { Moneda, Obra } from "../tipos";
import { Marco } from "../componentes/Marco";
import { Boton, Campo, Cargando, Entrada, MensajeError, Selector, Tarjeta } from "../componentes/ui";

interface Formulario {
  nombre: string;
  ubicacion: string;
  cliente: string;
  fecha_inicio: string;
  moneda: Moneda;
  presupuesto_total: string;
}

const VACIO: Formulario = {
  nombre: "",
  ubicacion: "",
  cliente: "",
  fecha_inicio: hoyISO(),
  moneda: "Bs",
  presupuesto_total: "",
};

/** Acepta "85.000,50", "85000.50" o "85000". */
function leerMonto(texto: string): string | null {
  const limpio = texto.replace(/\s/g, "");
  if (!limpio) return null;
  return limpio.includes(",") ? limpio.replace(/\./g, "").replace(",", ".") : limpio;
}

/** Crear o editar una obra. Sin :obraId crea una nueva. */
export function FormObra() {
  const { obraId } = useParams();
  const editando = obraId !== undefined;
  const obra = useQuery({
    queryKey: ["obra", obraId],
    queryFn: () => api<Obra>(`/api/obras/${obraId}`),
    enabled: editando,
  });
  const navegar = useNavigate();
  const cliente = useQueryClient();
  const [datos, setDatos] = useState<Formulario>(VACIO);

  useEffect(() => {
    if (!obra.data) return;
    const o = obra.data;
    setDatos({
      nombre: o.nombre,
      ubicacion: o.ubicacion,
      cliente: o.cliente,
      fecha_inicio: o.fecha_inicio,
      moneda: o.moneda,
      presupuesto_total: o.presupuesto_total === null ? "" : String(o.presupuesto_total),
    });
  }, [obra.data]);

  const guardar = useMutation({
    mutationFn: () => {
      const cuerpo = {
        ...datos,
        presupuesto_total: leerMonto(datos.presupuesto_total),
        // Al editar se conservan los umbrales de alerta que ya tenía la obra.
        ...(obra.data && { umbral_amarillo: obra.data.umbral_amarillo, umbral_rojo: obra.data.umbral_rojo }),
      };
      return editando ? api<Obra>(`/api/obras/${obraId}`, "PUT", cuerpo) : api<Obra>("/api/obras", "POST", cuerpo);
    },
    onSuccess: (o) => {
      cliente.invalidateQueries();
      navegar(`/obras/${o.id}`, { replace: true });
    },
  });

  const cambiar = (campo: keyof Formulario) => (e: { target: { value: string } }) =>
    setDatos({ ...datos, [campo]: e.target.value });

  function enviar(e: FormEvent) {
    e.preventDefault();
    guardar.mutate();
  }

  if (editando && obra.isLoading) return <Cargando />;

  return (
    <Marco titulo={editando ? "Editar obra" : "Nueva obra"} volver={editando ? `/obras/${obraId}` : "/obras"}>
      <Tarjeta>
        <form onSubmit={enviar} className="space-y-4">
          <Campo etiqueta="Nombre de la obra">
            <Entrada value={datos.nombre} onChange={cambiar("nombre")} placeholder="Casa Mamani" required minLength={2} />
          </Campo>
          <Campo etiqueta="Cliente">
            <Entrada value={datos.cliente} onChange={cambiar("cliente")} placeholder="Familia Mamani" />
          </Campo>
          <Campo etiqueta="Ubicación">
            <Entrada value={datos.ubicacion} onChange={cambiar("ubicacion")} placeholder="El Alto, zona Villa Adela" />
          </Campo>
          <div className="grid grid-cols-2 gap-3">
            <Campo etiqueta="Fecha de inicio">
              <Entrada type="date" value={datos.fecha_inicio} onChange={cambiar("fecha_inicio")} required />
            </Campo>
            <Campo etiqueta="Moneda">
              <Selector value={datos.moneda} onChange={cambiar("moneda")}>
                <option value="Bs">Bs (bolivianos)</option>
                <option value="USD">USD (dólares)</option>
              </Selector>
            </Campo>
          </div>
          <Campo etiqueta="Presupuesto total (opcional)" ayuda="Lo que costará la obra completa según tu presupuesto.">
            <Entrada
              inputMode="decimal"
              value={datos.presupuesto_total}
              onChange={cambiar("presupuesto_total")}
              placeholder="0,00"
            />
          </Campo>
          <p className="text-xs text-stone-500">
            La fecha de fin se calcula sola con las actividades del cronograma.
          </p>
          <MensajeError error={guardar.error ?? obra.error} />
          <Boton type="submit" grande className="w-full" disabled={guardar.isPending}>
            {guardar.isPending ? "Guardando…" : editando ? "Guardar cambios" : "Crear obra"}
          </Boton>
        </form>
      </Tarjeta>
    </Marco>
  );
}
