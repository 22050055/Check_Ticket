import React, { useState } from 'react'
import { Button, message } from 'antd'
import DateRangePicker from '../components/DateRangePicker'
import ErrorRateChart  from '../components/charts/ErrorRateChart'
import { reportApi }  from '../services/api'
import dayjs from 'dayjs'

const Panel = ({ children, style }) => (
  <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)', borderRadius:'var(--radius-md)', padding:20, ...style }}>
    {children}
  </div>
)
const Label = ({ children }) => (
  <div style={{ color:'var(--text-2)', fontSize:11, letterSpacing:'0.12em', marginBottom:14, fontFamily:'var(--font-mono)' }}>{children}</div>
)

export default function Reports() {
  const [range, setRange]       = useState([dayjs().subtract(7,'day'), dayjs()])
  const [errors, setErrors]     = useState(null)
  const [loading, setLoading]   = useState({ err: false, csv: false })

  const loadErrors = ([from, to]) => {
    setLoading(l => ({...l, err:true}))
    reportApi.errors({ date_from: from.toISOString(), date_to: to.toISOString() })
      .then(r => setErrors(r.data)).catch(() => {})
      .finally(() => setLoading(l => ({...l, err:false})))
  }

  const handleExport = async () => {
    setLoading(l => ({...l, csv:true}))
    try {
      const r = await reportApi.exportCsv({
        date_from: range[0].toISOString(),
        date_to: range[1].toISOString(),
      })
      const url = URL.createObjectURL(new Blob(['\uFEFF', r.data], { type: 'text/csv;charset=utf-8' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `gate_events_${range[0].format('YYYYMMDD')}_${range[1].format('YYYYMMDD')}.csv`
      a.click()
      URL.revokeObjectURL(url)
      message.success('Xuất file thành công')
    } catch { message.error('Xuất file thất bại') }
    finally { setLoading(l => ({...l, csv:false})) }
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom:24, display:'flex', alignItems:'flex-start', justifyContent:'space-between', flexWrap:'wrap', gap:12 }}>
        <div>
          <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--text-1)', marginBottom:4 }}>
            Báo cáo & Export
          </h2>
          <p style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
            Phân tích lỗi, xuất dữ liệu CSV
          </p>
        </div>
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <DateRangePicker value={range} onChange={v => { setRange(v); loadErrors(v) }} />
          <Button
            loading={loading.csv}
            onClick={handleExport}
            style={{
              height:38, fontFamily:'var(--font-mono)', fontSize:12, letterSpacing:'0.08em',
              background:'var(--bg-surface)', border:'1px solid var(--border-dim)', color:'var(--text-1)',
              borderRadius:'var(--radius-sm)',
            }}
          >
            ↓ EXPORT CSV
          </Button>
        </div>
      </div>

      {/* Error rate summary */}
      {errors && (
        <div style={{ display:'flex', gap:14, marginBottom:20, flexWrap:'wrap' }}>
          {[
            { label:'TỔNG SỰ KIỆN',  value: errors.total_events,   accent:'var(--text-2)' },
            { label:'THẤT BẠI',      value: errors.total_failed,   accent:'var(--red)' },
            { label:'TỶ LỆ LỖI',    value: errors.overall_error_rate?.toFixed(1) + '%', accent:'var(--amber)', raw:true },
          ].map(s => (
            <Panel key={s.label} style={{ flex:'1 1 160px', borderTop:`2px solid ${s.accent}` }}>
              <div style={{ color:'var(--text-2)', fontSize:10, letterSpacing:'0.15em', marginBottom:10, fontFamily:'var(--font-mono)' }}>{s.label}</div>
              <div style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:22, color:s.accent }}>
                {s.raw ? s.value : new Intl.NumberFormat('vi-VN').format(s.value)}
              </div>
            </Panel>
          ))}
        </div>
      )}

      {/* Error rate chart */}
      <Panel style={{ marginBottom:20 }}>
        <Label>TỶ LỆ LỖI THEO KÊNH</Label>
        <ErrorRateChart data={errors?.by_channel || []} />
        {!errors && (
          <div style={{ textAlign:'center', padding:'30px 0' }}>
            <button
              onClick={() => loadErrors(range)}
              style={{
                background:'var(--cyan-dim)', border:'1px solid var(--border)', color:'var(--cyan)',
                padding:'10px 20px', borderRadius:'var(--radius-sm)', cursor:'pointer',
                fontFamily:'var(--font-mono)', fontSize:12, letterSpacing:'0.1em',
              }}
            >
              TẢI DỮ LIỆU
            </button>
          </div>
        )}
      </Panel>

      {/* Export info */}
      <Panel>
        <Label>THÔNG TIN EXPORT</Label>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(200px, 1fr))', gap:12 }}>
          {[
            ['Định dạng','CSV (UTF-8)'],
            ['Khoảng thời gian', `${range[0].format('DD/MM/YYYY')} → ${range[1].format('DD/MM/YYYY')}`],
            ['Phân quyền','Manager / Admin'],
            ['Trường xuất','event_id, ticket_id, gate_id, direction, channel, result, created_at'],
          ].map(([k, v]) => (
            <div key={k} style={{ padding:'12px 14px', background:'var(--bg-surface)', borderRadius:'var(--radius-sm)', border:'1px solid var(--border-dim)' }}>
              <div style={{ color:'var(--text-3)', fontSize:10, letterSpacing:'0.1em', marginBottom:4, fontFamily:'var(--font-mono)' }}>{k}</div>
              <div style={{ color:'var(--text-1)', fontSize:12, fontFamily:'var(--font-mono)' }}>{v}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  )
}
 