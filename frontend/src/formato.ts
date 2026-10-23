const numeroBs = new Intl.NumberFormat("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function bs(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return `Bs ${numeroBs.format(valor)}`;
}

/** Fracción (0.45) a porcentaje ("45 %"). */
export function pct(fraccion: number | null | undefined): string {
  if (fraccion === null || fraccion === undefined) return "—";
  return `${Math.round(fraccion * 100)} %`;
}

export function indice(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor.toFixed(2).replace(".", ",");
}

/** "2026-10-21" a "21/10/2026". */
export function fecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export function fechaCorta(iso: string): string {
  const [, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}`;
}

/** Fecha de hoy según el celular, en formato ISO. */
export function hoyISO(): string {
  const ahora = new Date();
  const local = new Date(ahora.getTime() - ahora.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

/** Monto en la moneda de la obra (Bs o USD). */
export function dinero(valor: number | null | undefined, moneda: string): string {
  if (valor === null || valor === undefined) return "—";
  return `${moneda === "USD" ? "$us" : "Bs"} ${numeroBs.format(valor)}`;
}

/** Acepta "85.000,50", "85000.50" o "85000". Devuelve el texto listo para la API, o null si está vacío. */
export function leerMonto(texto: string): string | null {
  const limpio = texto.replace(/\s/g, "");
  if (!limpio) return null;
  return limpio.includes(",") ? limpio.replace(/\./g, "").replace(",", ".") : limpio;
}

/** Suma (o resta) días a una fecha ISO. */
export function sumarDias(iso: string, dias: number): string {
  const d = new Date(iso.slice(0, 10) + "T12:00:00");
  d.setDate(d.getDate() + dias);
  return d.toISOString().slice(0, 10);
}

const DIAS_SEMANA = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

/** "2026-10-23" a "vie". */
export function diaSemana(iso: string): string {
  return DIAS_SEMANA[new Date(iso.slice(0, 10) + "T12:00:00").getDay()];
}
