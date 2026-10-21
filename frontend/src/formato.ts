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
