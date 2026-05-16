/**
 * Cliente del endpoint /meta/schema.
 *
 * Cachea en memoria + sessionStorage durante 1h para no martillear el
 * endpoint cada vez que se abre el drawer. En sandbox / fallo de red
 * devuelve string vacio (graceful degradation) — el drawer sigue
 * funcionando sin resumen del schema.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true,
})

const TTL_MS = 60 * 60 * 1000 // 1h
const STORAGE_KEY = 'vedisa.schema_summary.v1'

let memoryCache: { value: string; expiresAt: number } | null = null

function readSession(): { value: string; expiresAt: number } | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (
      typeof parsed?.value !== 'string' ||
      typeof parsed?.expiresAt !== 'number'
    ) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

function writeSession(value: string, expiresAt: number) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ value, expiresAt }))
  } catch {
    /* sessionStorage no disponible, ok */
  }
}

/**
 * Construye un resumen textual breve del schema a partir del JSON crudo
 * de /meta/schema. Inlina la lista de entidades con su descripcion y los
 * primeros 5 campos clave; añade las reglas BR-* serializadas. Es
 * client-side para no exponer otro endpoint dedicado: el modelo lo recibe
 * en el system prompt del chat libre.
 */
function summarizeSchema(schema: any): string {
  if (!schema || typeof schema !== 'object') return ''
  const lines: string[] = []
  lines.push('=== Entidades CRM Vedisa ===')
  for (const ent of schema.entities ?? []) {
    const head = `- ${ent.name}: ${ent.description ?? ''}`.trim()
    lines.push(head)
    const fields: string[] = (ent.fields ?? [])
      .slice(0, 8)
      .map((f: any) => f.name)
    if (fields.length) lines.push(`    Campos: ${fields.join(', ')}`)
  }
  lines.push('')
  lines.push('=== Reglas criticas ===')
  for (const r of schema.business_rules ?? []) {
    lines.push(`- ${r.id}: ${r.description}`)
  }
  return lines.join('\n').slice(0, 6000)
}


export async function getSchemaSummary(): Promise<string> {
  const now = Date.now()

  if (memoryCache && memoryCache.expiresAt > now) {
    return memoryCache.value
  }

  const stored = readSession()
  if (stored && stored.expiresAt > now) {
    memoryCache = stored
    return stored.value
  }

  try {
    const { data } = await api.get('/meta/schema')
    const value = summarizeSchema(data)
    const expiresAt = now + TTL_MS
    memoryCache = { value, expiresAt }
    writeSession(value, expiresAt)
    return value
  } catch {
    // Graceful: si /meta/schema falla, devolver string vacio.
    return ''
  }
}
