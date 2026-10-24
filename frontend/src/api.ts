const CLAVE_TOKEN = "vc_token";

export class ErrorApi extends Error {
  constructor(
    mensaje: string,
    public estado: number,
  ) {
    super(mensaje);
  }
}

/** Error de red (sin señal): el registro puede ir a la cola. */
export class SinConexion extends Error {}

export const token = {
  leer: () => localStorage.getItem(CLAVE_TOKEN),
  guardar: (t: string) => localStorage.setItem(CLAVE_TOKEN, t),
  borrar: () => localStorage.removeItem(CLAVE_TOKEN),
};

const CAMPOS: Record<string, string> = {
  monto: "monto",
  porcentaje: "porcentaje",
  correo: "correo",
  clave: "clave",
  pin: "PIN",
  telefono: "teléfono",
  nombre: "nombre",
  fecha_inicio: "fecha de inicio",
  fecha_fin: "fecha de fin",
  presupuesto: "presupuesto",
  tipo: "tipo",
};

function mensajeDeError(detalle: unknown): string {
  if (typeof detalle === "string") return detalle;
  if (Array.isArray(detalle) && detalle.length > 0) {
    const primero = detalle[0] as { loc?: unknown[]; msg?: string };
    const msg = primero.msg ?? "";
    if (msg.startsWith("Value error, ")) return msg.slice("Value error, ".length);
    const campo = String(primero.loc?.[primero.loc.length - 1] ?? "");
    return `Revisa el dato: ${CAMPOS[campo] ?? campo}`;
  }
  return "Algo salió mal. Intenta de nuevo.";
}

async function pedir(ruta: string, opciones: RequestInit = {}): Promise<Response> {
  const cabeceras = new Headers(opciones.headers);
  const t = token.leer();
  if (t) cabeceras.set("Authorization", `Bearer ${t}`);
  if (opciones.body && !cabeceras.has("Content-Type")) cabeceras.set("Content-Type", "application/json");
  let respuesta: Response;
  try {
    respuesta = await fetch(ruta, { ...opciones, headers: cabeceras });
  } catch {
    throw new SinConexion("Sin conexión");
  }
  if (respuesta.status === 401 && !ruta.startsWith("/api/sesion/")) {
    token.borrar();
    window.location.assign("/ingresar");
  }
  if (!respuesta.ok) {
    let detalle: unknown = null;
    try {
      detalle = (await respuesta.json()).detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new ErrorApi(mensajeDeError(detalle), respuesta.status);
  }
  return respuesta;
}

export async function api<T>(ruta: string, metodo = "GET", cuerpo?: unknown): Promise<T> {
  const respuesta = await pedir(ruta, {
    method: metodo,
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
  if (respuesta.status === 204) return undefined as T;
  return respuesta.json() as Promise<T>;
}

/** Descarga un archivo protegido (ej. Excel) y lo entrega al navegador. */
export async function descargar(ruta: string, nombre: string): Promise<void> {
  const respuesta = await pedir(ruta);
  const url = URL.createObjectURL(await respuesta.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(url);
}

/** Sube un archivo tal cual (sin base64): sirve para planos de varios MB. */
export async function subirArchivo<T>(ruta: string, archivo: File): Promise<T> {
  const respuesta = await pedir(ruta, {
    method: "POST",
    body: archivo,
    headers: { "Content-Type": "application/octet-stream" },
  });
  return respuesta.json() as Promise<T>;
}
