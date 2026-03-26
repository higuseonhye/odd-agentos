/** AgentOS Flask API — see agentos_product_brief CURSOR-04. */

const configured = import.meta.env.VITE_API_BASE
const raw =
  typeof configured === 'string' ? configured.replace(/\/$/, '') : undefined

/**
 * Empty string = same-origin `/api` (nginx + SPA) or Vite proxy in dev.
 * When unset in dev, use '' so requests go to `/api` on the Vite origin (proxied to 8080).
 */
export const API_BASE =
  raw !== undefined && raw !== ''
    ? raw
    : import.meta.env.DEV
      ? ''
      : ''

export function apiUrl(path: string): string {
  if (path.startsWith('http')) return path
  const p = path.startsWith('/') ? path : `/${path}`
  if (API_BASE === '') return p
  return `${API_BASE}${p}`
}

export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  return fetch(apiUrl(path), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
}
