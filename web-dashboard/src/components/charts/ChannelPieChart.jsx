import React from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS = ['#00E5FF','#00FF88','#FFB800','#FF3366','#7A8BA8']
const CHANNEL_LABEL = { QR:'QR', QR_FACE:'QR+Face', ID:'CCCD', BOOKING:'Booking', MANUAL:'Thủ công' }

export default function ChannelPieChart({ data = [] }) {
  const formatted = data.map(d => ({
    ...d,
    name: CHANNEL_LABEL[d.channel] || d.channel,
  }))

  if (!formatted.length) return (
    <div style={{ height:160, display:'flex', alignItems:'center', justifyContent:'center', color:'var(--text-3)', fontSize:12, fontFamily:'var(--font-mono)' }}>
      Chưa có dữ liệu
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart>
        <Pie data={formatted} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={65} strokeWidth={0}>
          {formatted.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip
          contentStyle={{
            background:'var(--bg-surface)', border:'1px solid var(--border-dim)',
            fontFamily:'var(--font-mono)', fontSize:12, borderRadius:6,
          }}
          labelStyle={{ color:'var(--text-1)' }}
          itemStyle={{ color:'var(--text-2)' }}
        />
        <Legend
          wrapperStyle={{ fontSize:11, fontFamily:'var(--font-mono)', color:'var(--text-2)' }}
          iconType="circle" iconSize={8}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
 