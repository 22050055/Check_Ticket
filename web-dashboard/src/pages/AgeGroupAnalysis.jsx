import React, { useEffect, useState } from 'react'
import AgeGroupBarChart from '../components/charts/AgeGroupBarChart'
import DateRangePicker  from '../components/DateRangePicker'
import { reportApi }   from '../services/api'
import dayjs from 'dayjs'

const Panel = ({ children, style }) => (
  <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)', borderRadius:'var(--radius-md)', padding:20, ...style }}>{children}</div>
)
const Label = ({ children }) => (
  <div style={{ color:'var(--text-2)', fontSize:11, letterSpacing:'0.12em', marginBottom:14, fontFamily:'var(--font-mono)' }}>{children}</div>
)

export default function AgeGroupAnalysis() {
  const [data, setData] = useState(null)
  const [range, setRange] = useState([dayjs().subtract(30,'day'), dayjs()])

  const load = ([from, to]) => {
    reportApi.visitors({ date_from: from.toISOString(), date_to: to.toISOString() })
      .then(r => setData(r.data)).catch(() => {})
  }

  useEffect(() => { load(range) }, [])

  return (
    <div className="fade-in">
      <div style={{ marginBottom:24, display:'flex', alignItems:'flex-start', justifyContent:'space-between', flexWrap:'wrap', gap:12 }}>
        <div>
          <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--text-1)', marginBottom:4 }}>
            Phân tích nhóm tuổi
          </h2>
          <p style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
            Cơ cấu khách theo loại vé / nhóm tuổi đăng ký
          </p>
        </div>
        <DateRangePicker value={range} onChange={v => { setRange(v); load(v) }} />
      </div>

      <Panel style={{ marginBottom:20 }}>
        <Label>PHÂN TÍCH NHÓM TUỔI (THEO LOẠI VÉ)</Label>
        <AgeGroupBarChart data={data?.by_channel || []} />
      </Panel>

      <Panel>
        <Label>GHI CHÚ</Label>
        <p style={{ color:'var(--text-2)', fontSize:13, fontFamily:'var(--font-mono)', lineHeight:1.7 }}>
          Dữ liệu nhóm tuổi được suy luận từ loại vé (adult/child/student/group) do người mua khai báo lúc phát hành.
          Nếu hệ thống đăng ký khuôn mặt (Face opt-in), module GenderAge của ArcFace buffalo_l sẽ cung cấp ước tính tuổi chính xác hơn.
        </p>
      </Panel>
    </div>
  )
}
