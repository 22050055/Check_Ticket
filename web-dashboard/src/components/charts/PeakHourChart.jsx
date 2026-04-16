import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background:'var(--bg-surface)', border:'1px solid var(--border-dim)',
      padding:'8px 12px', borderRadius:'var(--radius-sm)', fontFamily:'var(--font-mono)',
    }}>
      <div style={{ color:'var(--text-2)', fontSize:10, marginBottom:4 }}>GIỜ {label}:00</div>
      <div style={{ color:'var(--cyan)', fontSize:14, fontWeight:600 }}>{payload[0].value} lượt</div>
    </div>
  )
}

export default function PeakHourChart({ data = [] }) {
  const max = Math.max(...data.map(d => d.count), 1)
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} barSize={14} margin={{ top:0, right:0, left:-20, bottom:0 }}>
        <XAxis
          dataKey="hour"
          tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }}
          tickLine={false} axisLine={false}
          tickFormatter={h => `${h}h`}
        />
        <YAxis tick={{ fill:'var(--text-3)', fontSize:10 }} tickLine={false} axisLine={false} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill:'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="count" radius={[3,3,0,0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.count === max ? 'var(--cyan)' : 'rgba(0,229,255,0.25)'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
