import React, { useEffect, useState } from 'react'
import { Row, Col } from 'antd'
import PeakHourChart   from '../components/charts/PeakHourChart'
import ChannelPieChart from '../components/charts/ChannelPieChart'
import DateRangePicker from '../components/DateRangePicker'
import { reportApi }   from '../services/api'
import dayjs from 'dayjs'

const Panel = ({ children, style }) => (
  <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)', borderRadius:'var(--radius-md)', padding:20, ...style }}>
    {children}
  </div>
)
const Label = ({ children }) => (
  <div style={{ color:'var(--text-2)', fontSize:11, letterSpacing:'0.12em', marginBottom:14, fontFamily:'var(--font-mono)' }}>{children}</div>
)

const StatCard = ({ label, value, accent='var(--cyan)' }) => (
  <Panel style={{ borderTop:`2px solid ${accent}` }}>
    <div style={{ color:'var(--text-2)', fontSize:10, letterSpacing:'0.15em', marginBottom:10, fontFamily:'var(--font-mono)' }}>{label}</div>
    <div style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:24, color:accent }}>
      {new Intl.NumberFormat('vi-VN').format(value || 0)}
    </div>
  </Panel>
)

export default function Visitors() {
  const [data, setData]       = useState(null)
  const [range, setRange]     = useState([dayjs().subtract(1,'day'), dayjs()])
  const [loading, setLoading] = useState(false)

  const load = ([from, to]) => {
    setLoading(true)
    reportApi.visitors({ date_from: from.toISOString(), date_to: to.toISOString() })
      .then(r => setData(r.data)).catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(range) }, [])

  return (
    <div className="fade-in">
      <div style={{ marginBottom:24, display:'flex', alignItems:'flex-start', justifyContent:'space-between', flexWrap:'wrap', gap:12 }}>
        <div>
          <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--text-1)', marginBottom:4 }}>
            Lượt khách
          </h2>
          <p style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
            Thống kê lượt vào/ra, giờ cao điểm, kênh xác thực
          </p>
        </div>
        <DateRangePicker value={range} onChange={v => { setRange(v); load(v) }} />
      </div>

      <Row gutter={[14,14]} style={{ marginBottom:20 }}>
        <Col xs={12} md={6}><StatCard label="KHÁCH TRONG KHU"  value={data?.current_inside}  accent="var(--cyan)" /></Col>
        <Col xs={12} md={6}><StatCard label="TỔNG LƯỢT VÀO"   value={data?.total_checkins}  accent="var(--green)" /></Col>
        <Col xs={12} md={6}><StatCard label="TỔNG LƯỢT RA"    value={data?.total_checkouts} accent="var(--amber)" /></Col>
        <Col xs={12} md={6}><StatCard label="SỰ KIỆN GHI NHẬN" value={(data?.total_checkins||0)+(data?.total_checkouts||0)} accent="var(--text-2)" /></Col>
      </Row>

      <Row gutter={[14,14]} style={{ marginBottom:20 }}>
        <Col xs={24} lg={16}>
          <Panel>
            <Label>GIỜ CAO ĐIỂM</Label>
            <PeakHourChart data={data?.by_hour || []} />
          </Panel>
        </Col>
        <Col xs={24} lg={8}>
          <Panel>
            <Label>KÊNH XÁC THỰC</Label>
            <ChannelPieChart data={data?.by_channel || []} />
          </Panel>
        </Col>
      </Row>

      {/* By gate */}
      <Panel>
        <Label>LƯỢT THEO CỔNG</Label>
        <div style={{ overflowX:'auto' }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontFamily:'var(--font-mono)', fontSize:13 }}>
            <thead>
              <tr>
                {['CỔNG','TÊN','SỰ KIỆN','TỶ LỆ'].map(h => (
                  <th key={h} style={{ padding:'8px 12px', textAlign:'left', color:'var(--text-3)', fontSize:10, letterSpacing:'0.1em', borderBottom:'1px solid var(--border-dim)', fontWeight:400 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.by_gate || []).map((g, i) => {
                const total = (data?.by_gate||[]).reduce((s,x) => s + x.count, 0)
                const pct = total > 0 ? (g.count / total * 100).toFixed(1) : 0
                return (
                  <tr key={g.gate_id || i} style={{ borderBottom:'1px solid var(--border-dim)' }}>
                    <td style={{ padding:'10px 12px', color:'var(--cyan)', fontFamily:'var(--font-mono)' }}>{g.gate_id}</td>
                    <td style={{ padding:'10px 12px', color:'var(--text-1)' }}>{g.gate || '—'}</td>
                    <td style={{ padding:'10px 12px', color:'var(--text-2)' }}>{new Intl.NumberFormat('vi-VN').format(g.count)}</td>
                    <td style={{ padding:'10px 12px' }}>
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <div style={{ flex:1, height:4, background:'var(--bg-hover)', borderRadius:2, maxWidth:100 }}>
                          <div style={{ width:`${pct}%`, height:'100%', background:'var(--cyan)', borderRadius:2 }}/>
                        </div>
                        <span style={{ color:'var(--text-2)', fontSize:12, minWidth:36 }}>{pct}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {!(data?.by_gate?.length) && (
                <tr><td colSpan={4} style={{ padding:'24px', textAlign:'center', color:'var(--text-3)', fontSize:12 }}>Chọn khoảng thời gian</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
 