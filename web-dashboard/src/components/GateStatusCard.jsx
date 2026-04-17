import React from 'react'
import dayjs from 'dayjs'

export default function GateStatusCard({ gate }) {
  const isSuccess = gate.last_event === 'SUCCESS'
  const isFail    = gate.last_event === 'FAIL'
  const hasEvent  = gate.last_event !== null && gate.last_event !== undefined

  const dotColor = isSuccess ? 'var(--green)' : isFail ? 'var(--red)' : 'var(--text-3)'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '12px 14px',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-dim)',
      borderLeft: `3px solid ${dotColor}`,
      borderRadius: 'var(--radius-sm)',
      transition: 'border-color 0.3s',
    }}>
      {/* Dot */}
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: dotColor, flexShrink: 0,
        boxShadow: hasEvent ? `0 0 6px ${dotColor}` : 'none',
      }}/>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 13,
          color: 'var(--text-1)', fontWeight: 500,
        }}>
          {gate.gate_code}
        </div>
        <div style={{ color: 'var(--text-2)', fontSize: 11, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {gate.name}
        </div>
      </div>

      {/* Status */}
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        {isSuccess && (
          <div style={{ color: 'var(--green)', fontSize: 10, letterSpacing: '0.1em', fontFamily: 'var(--font-mono)' }}>✓ OK</div>
        )}
        {isFail && (
          <div style={{ color: 'var(--red)', fontSize: 10, letterSpacing: '0.1em', fontFamily: 'var(--font-mono)' }}>✗ FAIL</div>
        )}
        {!hasEvent && (
          <div style={{ color: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>—</div>
        )}
        {gate.last_time && (
          <div style={{ color: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {dayjs(gate.last_time).format('HH:mm:ss')}
          </div>
        )}
      </div>
    </div>
  )
}
 