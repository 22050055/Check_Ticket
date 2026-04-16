import React from 'react'
import dayjs from 'dayjs'

const CHANNEL_LABEL = { QR:'QR', QR_FACE:'QR+Face', ID:'CCCD', BOOKING:'Booking', MANUAL:'Thủ công' }
const CHANNEL_COLOR = { QR:'var(--cyan)', QR_FACE:'var(--amber)', ID:'var(--text-2)', BOOKING:'var(--text-2)', MANUAL:'var(--text-3)' }
const DIR_COLOR     = { IN: 'var(--green)', OUT: 'var(--amber)' }

export default function RealtimeTable({ events = [] }) {
  if (!events.length) return (
    <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-3)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
      Đang chờ sự kiện...
    </div>
  )

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        <thead>
          <tr>
            {['THỜI GIAN','HƯỚNG','KÊNH','LOẠI VÉ','KẾT QUẢ'].map(h => (
              <th key={h} style={{
                padding: '8px 10px', textAlign: 'left',
                color: 'var(--text-3)', fontSize: 10, letterSpacing: '0.1em',
                borderBottom: '1px solid var(--border-dim)', fontWeight: 400,
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {events.slice(0, 15).map((ev, i) => (
            <tr key={ev.event_id || i} style={{ borderBottom: '1px solid var(--border-dim)' }}>
              <td style={{ padding: '9px 10px', color: 'var(--text-2)' }}>
                {ev.created_at ? dayjs(ev.created_at).format('HH:mm:ss') : '—'}
              </td>
              <td style={{ padding: '9px 10px', color: DIR_COLOR[ev.direction] || 'var(--text-2)', fontWeight: 500 }}>
                {ev.direction === 'IN' ? '→ VÀO' : '← RA'}
              </td>
              <td style={{ padding: '9px 10px' }}>
                <span style={{
                  color: CHANNEL_COLOR[ev.channel] || 'var(--text-2)',
                  background: 'var(--bg-surface)',
                  padding: '2px 7px', borderRadius: 3,
                  fontSize: 10, letterSpacing: '0.05em',
                }}>
                  {CHANNEL_LABEL[ev.channel] || ev.channel}
                </span>
              </td>
              <td style={{ padding: '9px 10px', color: 'var(--text-2)' }}>
                {ev.ticket_type || '—'}
              </td>
              <td style={{ padding: '9px 10px' }}>
                {ev.result === 'SUCCESS'
                  ? <span style={{ color:'var(--green)', fontSize:11 }}>✓ OK</span>
                  : <span style={{ color:'var(--red)', fontSize:11 }}>✗ FAIL</span>
                }
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
