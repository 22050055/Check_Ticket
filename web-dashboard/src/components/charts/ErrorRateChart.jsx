import React from 'react'

const CHANNEL_LABEL = { QR:'QR', QR_FACE:'QR+Face', ID:'CCCD', BOOKING:'Booking', MANUAL:'Thủ công' }

export default function ErrorRateChart({ data = [] }) {
  if (!data.length) return (
    <div style={{ padding:'20px 0', textAlign:'center', color:'var(--text-3)', fontFamily:'var(--font-mono)', fontSize:12 }}>
      Chưa có dữ liệu lỗi
    </div>
  )

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
      {data.map((ch) => {
        const rate = ch.error_rate || 0
        const color = rate > 20 ? 'var(--red)' : rate > 10 ? 'var(--amber)' : 'var(--green)'
        return (
          <div key={ch.channel} style={{ display:'flex', alignItems:'center', gap:12 }}>
            <div style={{ width:80, color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)', flexShrink:0 }}>
              {CHANNEL_LABEL[ch.channel] || ch.channel}
            </div>
            <div style={{ flex:1, height:8, background:'var(--bg-hover)', borderRadius:4 }}>
              <div style={{ width:`${Math.min(rate, 100)}%`, height:'100%', background:color, borderRadius:4, transition:'width 0.5s' }}/>
            </div>
            <div style={{ width:50, textAlign:'right', color, fontSize:12, fontFamily:'var(--font-mono)' }}>
              {rate.toFixed(1)}%
            </div>
            <div style={{ width:60, color:'var(--text-3)', fontSize:11, fontFamily:'var(--font-mono)' }}>
              {ch.failed}/{ch.total}
            </div>
          </div>
        )
      })}
    </div>
  )
}
