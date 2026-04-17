import React, { useEffect, useState } from 'react'
import { Row, Col } from 'antd'
import dayjs from 'dayjs'
import RevenueLineChart from '../components/charts/RevenueLineChart'
import ChannelPieChart  from '../components/charts/ChannelPieChart'
import DateRangePicker  from '../components/DateRangePicker'
import ExportButton     from '../components/ExportButton'
import { reportApi }   from '../services/api'

const fmtVnd = v => new Intl.NumberFormat('vi-VN').format(v) + 'đ'
const fmtVndFull = v => new Intl.NumberFormat('vi-VN', { style:'currency', currency:'VND' }).format(v)

const Panel = ({ children, style }) => (
  <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)', borderRadius:'var(--radius-md)', padding:20, ...style }}>
    {children}
  </div>
)

const SectionLabel = ({ children }) => (
  <div style={{ color:'var(--text-2)', fontSize:11, letterSpacing:'0.12em', marginBottom:16, fontFamily:'var(--font-mono)' }}>
    {children}
  </div>
)

const TYPE_MAP = { adult:'Người lớn', child:'Trẻ em', student:'Học sinh/SV', group:'Nhóm' }
const TYPE_COLORS = ['var(--cyan)', 'var(--green)', 'var(--amber)', 'var(--red)', 'var(--text-2)']

export default function Revenue() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [range, setRange]     = useState([dayjs().subtract(30,'day'), dayjs()])

  const load = ([from, to]) => {
    setLoading(true)
    reportApi.revenue({ date_from: from.toISOString(), date_to: to.toISOString() })
      .then(r => setData(r.data)).catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(range) }, [])

  const byType = data?.by_type ? Object.entries(data.by_type) : []
  const totalRevenue = data?.total_revenue || 0
  const totalTickets = data?.total_tickets || 0

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom:24, display:'flex', alignItems:'flex-start', justifyContent:'space-between', flexWrap:'wrap', gap:12 }}>
        <div>
          <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--text-1)', marginBottom:4 }}>
            Doanh thu
          </h2>
          <p style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
            Phân tích doanh thu theo ngày và loại vé
          </p>
        </div>
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <DateRangePicker value={range} onChange={v => { setRange(v); load(v) }} />
          <ExportButton />
        </div>
      </div>

      {/* Top stats */}
      <Row gutter={[14,14]} style={{ marginBottom:20 }}>
        <Col xs={12} md={6}>
          <Panel style={{ borderTop:'2px solid var(--cyan)' }}>
            <div style={{ color:'var(--text-2)', fontSize:10, letterSpacing:'0.15em', marginBottom:10, fontFamily:'var(--font-mono)' }}>TỔNG DOANH THU</div>
            <div style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:22, color:'var(--cyan)' }}>{fmtVnd(totalRevenue)}</div>
          </Panel>
        </Col>
        <Col xs={12} md={6}>
          <Panel style={{ borderTop:'2px solid var(--green)' }}>
            <div style={{ color:'var(--text-2)', fontSize:10, letterSpacing:'0.15em', marginBottom:10, fontFamily:'var(--font-mono)' }}>TỔNG VÉ BÁN</div>
            <div style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:22, color:'var(--green)' }}>
              {new Intl.NumberFormat('vi-VN').format(totalTickets)}
            </div>
          </Panel>
        </Col>
        <Col xs={12} md={6}>
          <Panel style={{ borderTop:'2px solid var(--amber)' }}>
            <div style={{ color:'var(--text-2)', fontSize:10, letterSpacing:'0.15em', marginBottom:10, fontFamily:'var(--font-mono)' }}>TRUNG BÌNH/VÉ</div>
            <div style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:22, color:'var(--amber)' }}>
              {totalTickets ? fmtVnd(Math.round(totalRevenue / totalTickets)) : '—'}
            </div>
          </Panel>
        </Col>
        <Col xs={12} md={6}>
          <Panel style={{ borderTop:'2px solid var(--text-2)' }}>
            <div style={{ color:'var(--text-2)', fontSize:10, letterSpacing:'0.15em', marginBottom:10, fontFamily:'var(--font-mono)' }}>LOẠI VÉ PHỔ BIẾN</div>
            <div style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:20, color:'var(--text-1)' }}>
              {byType.sort((a,b) => b[1].count - a[1].count)[0]
                ? TYPE_MAP[byType.sort((a,b)=>b[1].count-a[1].count)[0][0]] || byType[0][0]
                : '—'}
            </div>
          </Panel>
        </Col>
      </Row>

      {/* Chart */}
      <Row gutter={[14,14]} style={{ marginBottom:20 }}>
        <Col xs={24} lg={16}>
          <Panel>
            <SectionLabel>DOANH THU THEO NGÀY</SectionLabel>
            <RevenueLineChart data={data?.by_date || []} />
          </Panel>
        </Col>
        <Col xs={24} lg={8}>
          <Panel style={{ height:'100%' }}>
            <SectionLabel>CƠ CẤU DOANH THU</SectionLabel>
            <ChannelPieChart data={byType.map(([k,v]) => ({ channel: TYPE_MAP[k]||k, count: v.count }))} />
          </Panel>
        </Col>
      </Row>

      {/* By type table */}
      <Panel>
        <SectionLabel>CHI TIẾT THEO LOẠI VÉ</SectionLabel>
        <div style={{ overflowX:'auto' }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontFamily:'var(--font-mono)', fontSize:13 }}>
            <thead>
              <tr>
                {['LOẠI VÉ','SỐ LƯỢNG','DOANH THU','TỶ LỆ'].map(h => (
                  <th key={h} style={{
                    padding:'8px 12px', textAlign:'left',
                    color:'var(--text-3)', fontSize:10, letterSpacing:'0.1em',
                    borderBottom:'1px solid var(--border-dim)', fontWeight:400,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {byType.map(([type, val], i) => {
                const pct = totalRevenue > 0 ? (val.revenue / totalRevenue * 100).toFixed(1) : 0
                return (
                  <tr key={type} style={{ borderBottom:'1px solid var(--border-dim)' }}>
                    <td style={{ padding:'10px 12px' }}>
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <div style={{ width:8, height:8, borderRadius:'50%', background: TYPE_COLORS[i % TYPE_COLORS.length] }}/>
                        <span style={{ color:'var(--text-1)' }}>{TYPE_MAP[type] || type}</span>
                      </div>
                    </td>
                    <td style={{ padding:'10px 12px', color:'var(--text-2)' }}>{new Intl.NumberFormat('vi-VN').format(val.count)}</td>
                    <td style={{ padding:'10px 12px', color:'var(--cyan)', fontWeight:500 }}>{fmtVnd(val.revenue)}</td>
                    <td style={{ padding:'10px 12px' }}>
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <div style={{ flex:1, height:4, background:'var(--bg-hover)', borderRadius:2, maxWidth:100 }}>
                          <div style={{ width:`${pct}%`, height:'100%', background:TYPE_COLORS[i%TYPE_COLORS.length], borderRadius:2 }}/>
                        </div>
                        <span style={{ color:'var(--text-2)', fontSize:12, minWidth:36 }}>{pct}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {byType.length === 0 && (
                <tr><td colSpan={4} style={{ padding:'24px 12px', textAlign:'center', color:'var(--text-3)', fontSize:12 }}>
                  Chọn khoảng thời gian để xem dữ liệu
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
 