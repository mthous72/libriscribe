import { useEffect, useRef, useCallback } from 'react'
import { useGenerationStore } from '../store/generationSlice'

export function useWebSocket(projectName: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<number | null>(null)
  const disposed = useRef(false)
  const {
    addLog, appendStreamChunk, clearStreamBuffer, setStageStatus, setPendingReview, setJobStatus,
  } = useGenerationStore()

  const connect = useCallback(() => {
    if (!projectName) return

    // Never leave a previous socket alive: a duplicated connection makes every
    // stream_chunk append twice and turns the live preview into interleaved garbage.
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onmessage = null
      wsRef.current.close()
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${projectName}`)
    wsRef.current = ws

    ws.onopen = () => {
      console.log(`WS connected for ${projectName}`)
    }

    ws.onmessage = (event) => {
      if (wsRef.current !== ws) return // stale socket — drop its events
      try {
        const msg = JSON.parse(event.data)
        const { type, payload } = msg

        switch (type) {
          case 'connected':
            setJobStatus(payload.current_status || 'idle')
            break
          case 'stage_started':
            if (payload.stage === 'chapters') clearStreamBuffer()
            setStageStatus(payload.stage, 'in_progress')
            addLog(`[${payload.stage}] ${payload.message}`)
            break
          case 'stage_complete':
            setStageStatus(payload.stage, 'complete')
            addLog(`[${payload.stage}] ${payload.message}`)
            break
          case 'log':
            addLog(`[${payload.agent || ''}] ${payload.message}`)
            break
          case 'stream_chunk':
            appendStreamChunk(payload.text || '', payload.chapter, payload.scene)
            break
          case 'stream_complete':
            addLog(`Scene ${payload.scene} complete (${payload.word_count} words)`)
            break
          case 'chapter_complete':
            addLog(`Chapter ${payload.chapter} complete (${payload.word_count} words)`)
            break
          case 'human_review_required':
            setPendingReview(payload)
            setJobStatus('paused_for_review')
            break
          case 'cost_update':
            addLog(`Cost: $${payload.cost?.toFixed(4)} (session total: $${payload.session_total_cost?.toFixed(4)})`)
            break
          case 'error':
            addLog(`ERROR [${payload.stage}]: ${payload.message}`)
            if (payload.stage === 'pipeline') setJobStatus('failed')
            break
          case 'stage_awaiting_approval':
            // Step mode (B30): one stage finished; the pipeline stopped for the author's review.
            setJobStatus('completed')
            addLog(payload.message || `Stage ${payload.stage} finished — awaiting your review.`)
            break
          case 'generation_complete':
            setJobStatus('completed')
            addLog('Generation complete!')
            break
        }
      } catch (e) {
        console.error('WS parse error:', e)
      }
    }

    ws.onclose = () => {
      console.log(`WS disconnected for ${projectName}`)
      // Reconnect only if this is still the active socket and the hook is still mounted —
      // otherwise every unmount/server-restart left a zombie timer opening extra sockets.
      if (disposed.current || wsRef.current !== ws) return
      reconnectTimer.current = window.setTimeout(() => connect(), 3000)
    }
  }, [projectName, addLog, appendStreamChunk, clearStreamBuffer, setStageStatus, setPendingReview, setJobStatus])

  useEffect(() => {
    disposed.current = false
    connect()
    return () => {
      disposed.current = true
      if (reconnectTimer.current !== null) {
        window.clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.onmessage = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { sendMessage }
}
