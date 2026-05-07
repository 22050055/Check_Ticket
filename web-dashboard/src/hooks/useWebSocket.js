import { useEffect } from 'react'
import { connectWS, disconnectWS, onStats, onGateEvent } from '../services/websocket'
import useReportStore from '../store/reportStore'
import useGateStore   from '../store/gateStore'

/**
 * Hook: kết nối WS khi mount, disconnect khi unmount.
 * Tự cập nhật reportStore và gateStore khi nhận message.
 */
export default function useWebSocket() {
  const setRealtimeStats = useReportStore(s => s.setRealtimeStats)
  const setRecentEvents  = useGateStore(s => s.setRecentEvents)
  const addEvent         = useGateStore(s => s.addEvent)

  useEffect(() => {
    connectWS()

    const offStats = onStats(msg => {
      setRealtimeStats(msg)
      // Khởi tạo bảng sự kiện nếu nó đang trống
      if (msg.recent_events) {
        setRecentEvents(msg.recent_events)
      }
    })

    const offEvent = onGateEvent(event => {
      addEvent({
        event_id:    event.event_id || Date.now(),
        gate_id:     event.gate_id,
        direction:   event.direction,
        channel:     event.channel,
        result:      event.result,
        ticket_type: event.ticket_type,
        message:     event.message,
        created_at:  new Date().toISOString(),
      })
    })

    return () => {
      offStats()
      offEvent()
      disconnectWS()
    }
  }, [])
}
 