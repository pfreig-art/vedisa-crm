import { useEffect, useRef, useCallback } from 'react'

export type SSEEvent = {
  type: string
  ts?: string
  payload?: unknown
}

export function useSSE(
  url: string,
  onMessage: (event: SSEEvent) => void,
  enabled = true,
) {
  const esRef = useRef<EventSource | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (!enabled) return
    if (esRef.current) {
      esRef.current.close()
    }
    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const data: SSEEvent = JSON.parse(e.data)
        onMessageRef.current(data)
      } catch {
        // keepalive o malformado, ignorar
      }
    }

    es.onerror = () => {
      es.close()
      setTimeout(connect, 3000)
    }
  }, [url, enabled])

  useEffect(() => {
    connect()
    return () => {
      esRef.current?.close()
    }
  }, [connect])
}
