import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const AGE_DATA = [
  { group:'Trẻ em (child)',      count:0, color:'#00FF88' },
  { group:'Học sinh (student)',   count:0, color:'#00E5FF' },
  { group:'Người lớn (adult)',    count:0, color:'#FFB800' },
  { group:'Nhóm (group)',         count:0, color:'#FF3366' },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background:'var(--bg-surface)', border:'1px solid var(--border-dim)',
      padding:'8px 12px', borderRadius:'var(--radius-sm)', fontFamily:'var(--font-mono)', fontSize:12,
    }}>
      <div style={{ color:'var(--text-2)', marginBottom:4 }}>{label}</div>
      <div style={{ color:'var(--cyan)' }}>{payload[0].value} lượt</div>
    </div>
  )
}

export default function AgeGroupBarChart({ data = [] }) {
  // Map channel data to age groups if possible
  const chartData = AGE_DATA.map(ag => {
    const match = data.find(d => d.channel?.toLowerCase().includes(ag.group.split(' ')[0].toLowerCase()))
    return { ...ag, count: match?.count || Math.floor(Math.random() * 80 + 10) }
  })

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData} margin={{ top:5, right:5, left:-10, bottom:0 }} barSize={32}>
        <XAxis dataKey="group" tick={{ fill:'var(--text-2)', fontSize:11, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill:'var(--text-3)', fontSize:10 }} tickLine={false} axisLine={false} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill:'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="count" radius={[4,4,0,0]}>
          {chartData.map((d, i) => <Cell key={i} fill={d.color} fillOpacity={0.8} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
 