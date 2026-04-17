/**
 * websocket.js — Kết nối WS /ws/realtime
 * Tự động reconnect khi mất kết nối.
 * Server gửi 2 loại message:
 *   { type: "stats",      ... }  — mỗi 5 giây
 *   { type: "gate_event", ... }  — ngay sau mỗi check-in/out
 */

const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/realtime`
const RECONNECT_DELAY_MS = 3000

let _ws       = null
let _handlers = { stats: [], gate_event: [] }
let _reconnectTimer = null

export function connectWS() {
  if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) return

  _ws = new WebSocket(WS_URL)

  _ws.onopen = () => {
    console.log('[WS] Connected')
    if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
    // Keepalive ping mỗi 25 giây
    _ws._ping = setInterval(() => _ws.readyState === WebSocket.OPEN && _ws.send('ping'), 25000)
  }

  _ws.onmessage = ({ data }) => {
    if (data === 'pong') return
    try {
      const msg = JSON.parse(data)
      const type = msg.type || 'stats'
      ;(_handlers[type] || []).forEach(fn => fn(msg))
    } catch (e) {
      console.warn('[WS] Parse error', e)
    }
  }

  _ws.onclose = () => {
    console.log('[WS] Disconnected — reconnecting in', RECONNECT_DELAY_MS, 'ms')
    if (_ws._ping) clearInterval(_ws._ping)
    _reconnectTimer = setTimeout(connectWS, RECONNECT_DELAY_MS)
  }

  _ws.onerror = (e) => console.error('[WS] Error', e)
}

export function disconnectWS() {
  if (_reconnectTimer) clearTimeout(_reconnectTimer)
  if (_ws) { _ws.onclose = null; _ws.close() }
  _ws = null
}

export function onStats(fn)     { _handlers.stats.push(fn);      return () => { _handlers.stats      = _handlers.stats.filter(h => h !== fn) } }
export function onGateEvent(fn) { _handlers.gate_event.push(fn); return () => { _handlers.gate_event = _handlers.gate_event.filter(h => h !== fn) } }
 