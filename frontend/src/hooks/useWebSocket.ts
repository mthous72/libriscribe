import { useEffect, useRef, useCallback } from 'react'
import { useGenerationStore } from '../store/generationSlice'

export function useWebSocket(projectName: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null)
  const { addLog, setStreamBuffer, setStageStatus, setPendingReview, setJobStatus } = useGenerationStore()

  const connect = useCallback(() => {
    if (!projectName) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${projectName}`)

    ws.onopen = () => {
      console.log(`WS connected for ${projectName}`)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const { type, payload } = msg

        switch (type) {
          case 'connected':
            setJobStatus(payload.current_status || 'idle')
            break
          case 'stage_started':
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
            setStreamBuffer(prev => prev + (payload.text || ''))
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
      // Auto-reconnect after 3s
      setTimeout(() => connect(), 3000)
    }

    wsRef.current = ws
  }, [projectName, addLog, setStreamBuffer, setStageStatus, setPendingReview, setJobStatus])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { sendMessage }
}
