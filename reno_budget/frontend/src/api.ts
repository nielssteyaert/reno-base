// Thin fetch wrapper. Paths are relative ("api/..."), never "/api/...": under Home Assistant
// ingress the app lives at /api/hassio_ingress/<token>/ and an absolute path would hit HA itself.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

type Query = Record<string, unknown>

export function queryString(params: Query = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') continue
    if (Array.isArray(value)) value.forEach((v) => search.append(key, String(v)))
    else search.append(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d: { loc?: string[]; msg: string }) => `${d.loc?.slice(1).join('.') ?? ''} ${d.msg}`.trim())
        .join('; ')
    }
  } catch {
    // not JSON
  }
  return `${response.status} ${response.statusText}`
}

async function request<T>(method: string, path: string, body?: unknown, query?: Query): Promise<T> {
  const init: RequestInit = { method, headers: {} }
  if (body instanceof FormData) {
    init.body = body
  } else if (body !== undefined) {
    init.body = JSON.stringify(body)
    ;(init.headers as Record<string, string>)['Content-Type'] = 'application/json'
  }
  const response = await fetch(`api/${path}${queryString(query)}`, init)
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, undefined, query),
  post: <T>(path: string, body?: unknown, query?: Query) => request<T>('POST', path, body ?? {}, query),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  del: (path: string) => request<void>('DELETE', path),
  upload: <T>(path: string, form: FormData) => request<T>('POST', path, form),
}

export function apiUrl(path: string, query?: Query): string {
  return `api/${path}${queryString(query)}`
}

function filenameFrom(response: Response, fallback: string): string {
  const header = response.headers.get('content-disposition') ?? ''
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (star?.[1]) return decodeURIComponent(star[1])
  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain?.[1] ?? fallback
}

/** Download a file from the API (GET, or POST with a JSON body) and hand it to the browser. */
export async function download(path: string, options: { query?: Query; body?: unknown; fallback?: string } = {}) {
  const init: RequestInit =
    options.body === undefined
      ? { method: 'GET' }
      : { method: 'POST', body: JSON.stringify(options.body), headers: { 'Content-Type': 'application/json' } }
  const response = await fetch(apiUrl(path, options.query), init)
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filenameFrom(response, options.fallback ?? 'download')
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
