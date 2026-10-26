export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map((error: { loc?: (string | number)[]; msg?: string }) => `${error.loc?.filter(part => part !== 'body').map(part => typeof part === 'number' ? part + 1 : part.replaceAll('_', ' ')).join(' > ') || 'Input'}: ${error.msg ?? 'Check this value'}`).join('; ') : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return data as T;
}
export const formatNumber = (n: number | undefined) => n === undefined ? '—' : new Intl.NumberFormat('en-US').format(n);
export const fixed = (n: number | null | undefined, digits = 3) => n == null ? '—' : n.toFixed(digits);
export function recallRows(payload: any): any[] {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== 'object') return [];
  for (const key of ['results', 'data', 'recalls', 'items']) { if (Array.isArray(payload[key])) return payload[key]; }
  return [];
}
