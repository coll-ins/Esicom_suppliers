// Talks to Django at /ledger-api (Vite proxy locally, Vercel rewrite in production).
const BASE = '/ledger-api'

function cookie(name) {
  const match = document.cookie.split('; ').find((c) => c.startsWith(name + '='))
  return match ? decodeURIComponent(match.split('=')[1]) : ''
}

let csrfReady = null
export function ensureCsrf() {
  if (!csrfReady) csrfReady = fetch(`${BASE}/auth/csrf/`, { credentials: 'same-origin' })
  return csrfReady
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

let onLoggedOut = () => {}
export function setLoggedOutHandler(fn) {
  onLoggedOut = fn
}

export async function api(path, { method = 'GET', body, raw = false, headers = {} } = {}) {
  if (method !== 'GET') await ensureCsrf()
  let res
  try {
    res = await fetch(BASE + path, {
      method,
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(method !== 'GET' ? { 'X-CSRFToken': cookie('csrftoken') } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('No connection to the server. Check the internet and try again.', 0)
  }
  if (raw && res.ok) return res
  const type = res.headers.get('Content-Type') || ''
  const data = type.includes('application/json') ? await res.json().catch(() => ({})) : {}
  if (!res.ok) {
    if (res.status === 403 && /log in|credentials/i.test(data.detail || '') && !path.startsWith('/auth/login')) {
      onLoggedOut()
    }
    const message =
      data.detail ||
      (res.status >= 500 ? 'The server had a problem. Try again in a minute.' : `Request failed (${res.status}).`)
    throw new ApiError(message, res.status)
  }
  return data
}

export const get = (path) => api(path)
export const post = (path, body = {}, headers) => api(path, { method: 'POST', body, headers })

// One key per form: if a save is retried after a lost reply, the server returns the first result.
export const newKey = () => crypto.randomUUID()
export const patch = (path, body) => api(path, { method: 'PATCH', body })
export const put = (path, body) => api(path, { method: 'PUT', body })

export const pdfUrl = (id) => `${BASE}/documents/${id}/pdf/`
export const qrUrl = () => `${BASE}/qr.png`
export const uploadUrl = (id, kind) => `${BASE}/uploads/${id}/${kind}/`

// POST that returns a PDF (statements); opens it in a new tab.
export async function postForPdf(path, body) {
  await ensureCsrf()
  const res = await fetch(BASE + path, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken') },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new ApiError(data.detail || 'Could not make the PDF.', res.status)
  }
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}
