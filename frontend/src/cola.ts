/**
 * Cola de registros hechos sin señal. Se guardan en el celular y se envían
 * cuando vuelve la conexión. Cada registro lleva un id_cliente para que el
 * servidor no lo duplique si se envía dos veces.
 */
import { api, ErrorApi, SinConexion } from "./api";

const CLAVE = "vc_pendientes";

export interface Pendiente {
  id: string;
  ruta: string;
  cuerpo: Record<string, unknown>;
  descripcion: string;
  creado: string;
  error?: string;
}

type Oyente = (pendientes: Pendiente[]) => void;
const oyentes = new Set<Oyente>();

export function leerPendientes(): Pendiente[] {
  try {
    return JSON.parse(localStorage.getItem(CLAVE) ?? "[]");
  } catch {
    return [];
  }
}

function guardar(pendientes: Pendiente[]) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(pendientes));
  } catch {
    // Memoria llena (fotos grandes): se guarda sin fotos antes que perder el registro.
    localStorage.setItem(
      CLAVE,
      JSON.stringify(pendientes.map((p) => ({ ...p, cuerpo: { ...p.cuerpo, foto_base64: null } }))),
    );
  }
  oyentes.forEach((o) => o(pendientes));
}

export function escucharPendientes(oyente: Oyente): () => void {
  oyentes.add(oyente);
  return () => oyentes.delete(oyente);
}

export function nuevoId(): string {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Intenta enviar; si no hay señal lo deja en la cola. */
export async function registrar(
  ruta: string,
  cuerpo: Record<string, unknown>,
  descripcion: string,
): Promise<"enviado" | "en_cola"> {
  const conId = { ...cuerpo, id_cliente: nuevoId() };
  try {
    await api(ruta, "POST", conId);
    return "enviado";
  } catch (e) {
    if (!(e instanceof SinConexion)) throw e;
    const pendiente: Pendiente = {
      id: conId.id_cliente as string,
      ruta,
      cuerpo: conId,
      descripcion,
      creado: new Date().toISOString(),
    };
    guardar([...leerPendientes(), pendiente]);
    return "en_cola";
  }
}

let enviando = false;

/** Envía lo que esté en la cola. Devuelve cuántos se enviaron. */
export async function enviarPendientes(): Promise<number> {
  if (enviando) return 0;
  enviando = true;
  let enviados = 0;
  try {
    for (const p of leerPendientes()) {
      if (p.error) continue;
      try {
        await api(p.ruta, "POST", p.cuerpo);
        guardar(leerPendientes().filter((x) => x.id !== p.id));
        enviados++;
      } catch (e) {
        if (e instanceof SinConexion) break;
        // El servidor lo rechazó (ej. día cerrado): se marca para que el usuario decida.
        const mensaje = e instanceof ErrorApi ? e.message : "No se pudo enviar";
        guardar(leerPendientes().map((x) => (x.id === p.id ? { ...x, error: mensaje } : x)));
      }
    }
  } finally {
    enviando = false;
  }
  return enviados;
}

export function descartarPendiente(id: string) {
  guardar(leerPendientes().filter((p) => p.id !== id));
}

export function reintentarPendiente(id: string) {
  guardar(leerPendientes().map((p) => (p.id === id ? { ...p, error: undefined } : p)));
  return enviarPendientes();
}
