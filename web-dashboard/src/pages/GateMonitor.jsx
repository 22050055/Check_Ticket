import React, { useEffect, useState } from 'react'
import { Select } from 'antd'
import useWebSocket  from '../hooks/useWebSocket'
import useGateStore  from '../store/gateStore'
import RealtimeTable from '../components/RealtimeTable'
import GateStatusCard from '../components/GateStatusCard'
import { gateApi } from '../services/api'

const Label = ({ children }) => (
  <div style={{ color:'var(--text-2)', fontSize:11, letterSpacing:'0.12em', marginBottom:14, fontFamily:'var(--font-mono)' }}>
    {children}
  </div>
)

const Panel = ({ children, style }) => (
  <div style={{
    background:'var(--bg-card)', border:'1px solid var(--border-dim)',
    borderRadius:'var(--radius-md)', padding:20, ...style,
  }}>{children}</div>
)

export default function GateMonitor() {
  useWebSocket()
  const { recentEvents, gatesStatus, setGatesStatus } = useGateStore()
  const [selectedGate, setSelectedGate] = useState(null)
  const [gateEvents, setGateEvents]     = useState([])
  const [loading, setLoading]           = useState(false)
  const [gates, setGates]               = useState([])

  useEffect(() => {
    gateApi.list().then(r => {
      setGates(r.data)
      setGatesStatus(r.data.map(g => ({ gate_id: g.gate_id, gate_code: g.gate_code, name: g.name, last_event: null })))
      if (r.data.length > 0) setSelectedGate(r.data[0].gate_id)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedGate) return
    setLoading(true)
    gateApi.events(selectedGate, 50)
      .then(r => setGateEvents(r.data.events || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [selectedGate])

  const selectedGateInfo = gates.find(g => g.gate_id === selectedGate)

  return (
    <div className="fade-in">
      <div style={{ marginBottom:24 }}>
        <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--text-1)', marginBottom:4 }}>
          Giám sát cổng
        </h2>
        <p style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
          Realtime · Check-in/out theo từng cổng
        </p>
      </div>

      <div style={{ display:'flex', gap:14, flexWrap:'wrap', marginBottom:20 }}>
        {/* Gate selector */}
        <Panel style={{ flex:'0 0 220px' }}>
          <Label>CHỌN CỔNG</Label>
          <Select
            style={{ width:'100%' }}
            value={selectedGate}
            onChange={setSelectedGate}
            options={gates.map(g => ({ value: g.gate_id, label: g.gate_code + ' — ' + g.name }))}
            placeholder="Chọn cổng..."
          />
          {selectedGateInfo && (
            <div style={{ marginTop:14 }}>
              <div style={{ color:'var(--text-1)', fontSize:14, fontFamily:'var(--font-display)', fontWeight:700, marginBottom:4 }}>
                {selectedGateInfo.gate_code}
              </div>
              <div style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
                {selectedGateInfo.name}
              </div>
              <div style={{
                marginTop:12, padding:'8px 10px',
                background: selectedGateInfo.is_active ? 'var(--green-dim)' : 'var(--red-dim)',
                borderRadius:'var(--radius-sm)', fontSize:11, fontFamily:'var(--font-mono)',
                color: selectedGateInfo.is_active ? 'var(--green)' : 'var(--red)',
                display:'inline-block',
              }}>
                {selectedGateInfo.is_active ? '● ACTIVE' : '○ INACTIVE'}
              </div>
            </div>
          )}
        </Panel>

        {/* Gate statuses */}
        <Panel style={{ flex:1, minWidth:240 }}>
          <Label>TRẠNG THÁI TẤT CẢ CỔNG</Label>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {gatesStatus.length === 0 && (
              <div style={{ color:'var(--text-3)', fontSize:12, fontFamily:'var(--font-mono)' }}>Chưa có dữ liệu</div>
            )}
            {gatesStatus.map(g => <GateStatusCard key={g.gate_id} gate={g} />)}
          </div>
        </Panel>
      </div>

      {/* Events table */}
      <Panel>
        <Label>SỰ KIỆN CHECK-IN/OUT — {selectedGateInfo?.gate_code || '...'}</Label>
        <RealtimeTable events={gateEvents.length > 0 ? gateEvents : recentEvents} />
      </Panel>
    </div>
  )
}
