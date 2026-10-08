// empty locally, so the vite dev proxy handles /api. Set VITE_API_URL when the
// frontend is deployed separately from the backend.
const BASE = import.meta.env.VITE_API_URL || ''

const TOKEN_KEY = 'healthsync_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function req(path, options = {}) {
  const token = getToken()
  const headers = { ...options.headers }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json()
}

function json(method, body) {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

export const getHealth = () => req('/api/health')

export const login = (username, password) =>
  req('/api/auth/login', json('POST', { username, password }))

export const register = (details) => req('/api/auth/register', json('POST', details))

export const logout = () => req('/api/auth/logout', { method: 'POST' })

export const getPortfolio = () => req('/api/portfolio')

export const saveProfile = (profile) => req('/api/portfolio/profile', json('PUT', profile))

export const saveConditions = (conditions) =>
  req('/api/portfolio/conditions', json('PUT', conditions))

export const saveAllergies = (allergies) => req('/api/portfolio/allergies', json('PUT', allergies))

export const getEmergencyCard = (patientId) => req(`/api/emergency/${patientId}`)

export const sendChat = (message, history) => req('/api/chat', json('POST', { message, history }))

export const getPrompts = () => req('/api/prompts')

export const getChatContext = () => req('/api/chat/context')

export const importBrowserNote = (id, note, llmMs, model) =>
  req(
    `/api/encounters/${id}/note/import?llm_ms=${llmMs}&model=${encodeURIComponent(model)}`,
    json('POST', note),
  )

export const listEncounters = () => req('/api/encounters')

export const getEncounter = (id) => req(`/api/encounters/${id}`)

export const deleteEncounter = (id) => req(`/api/encounters/${id}`, { method: 'DELETE' })

export const loadSample = () => req('/api/audio/sample', { method: 'POST' })

export const importBrowserTranscript = (transcript) =>
  req('/api/audio/browser', json('POST', transcript))

export const transcribeEncounter = (id) =>
  req(`/api/encounters/${id}/transcribe`, { method: 'POST' })

export const generateNote = (id, model) =>
  req(`/api/encounters/${id}/note${model ? `?model=${encodeURIComponent(model)}` : ''}`, {
    method: 'POST',
  })

export const saveNote = (id, note) => req(`/api/encounters/${id}/note`, json('PUT', note))

export const editSegments = (id, edits) => req(`/api/encounters/${id}/segments`, json('PATCH', edits))

export function uploadAudio(file, source, patientLabel) {
  const form = new FormData()
  form.append('file', file)
  form.append('source', source)
  if (patientLabel) form.append('patient_label', patientLabel)
  return req('/api/audio/upload', { method: 'POST', body: form })
}
