import React from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import dayjs from 'dayjs'

const fmtVnd = v => new Intl.NumberFormat('vi-VN', { notation:'compact' }).format(v) + 'đ'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background:'var(--bg-surface)', border:'1px solid var(--border-dim)',
      padding:'10px 14px', borderRadius:'var(--radius-sm)', fontFamily:'var(--font-mono)',
    }}>
      <div style={{ color:'var(--text-2)', fontSize:10, marginBottom:6 }}>{label}</div>
      <div style={{ color:'var(--cyan)', fontSize:14, fontWeight:600 }}>{fmtVnd(payload[0].value)}</div>
      {payload[1] && <div style={{ color:'var(--green)', fontSize:12 }}>{payload[1].value} vé</div>}
    </div>
  )
}

export default function RevenueLineChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top:5, right:5, left:0, bottom:0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="date"
          tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }}
          tickLine={false} axisLine={false}
          tickFormatter={d => dayjs(d).format('DD/MM')}
        />
        <YAxis
          tick={{ fill:'var(--text-3)', fontSize:10 }}
          tickLine={false} axisLine={false}
          tickFormatter={fmtVnd}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line type="monotone" dataKey="revenue" stroke="var(--cyan)" strokeWidth={2} dot={false} activeDot={{ r:4, fill:'var(--cyan)' }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
 