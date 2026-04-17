import React, { useEffect } from 'react'
import { Row, Col, Statistic } from 'antd'
import useWebSocket    from '../hooks/useWebSocket'
import useReportStore  from '../store/reportStore'
import useGateStore    from '../store/gateStore'
import RealtimeTable   from '../components/RealtimeTable'
import GateStatusCard  from '../components/GateStatusCard'
import ChannelPieChart from '../components/charts/ChannelPieChart'
import PeakHourChart   from '../components/charts/PeakHourChart'
import { reportApi, gateApi } from '../services/api'

const fmtVnd = v => new Intl.NumberFormat('vi-VN', { notation: 'compact', compactDisplay: 'short' }).format(v) + 'đ'
const fmtNum = v => new Intl.NumberFormat('vi-VN').format(v)

const StatCard = ({ label, value, formatter, accent='var(--cyan)', suffix='' }) => (
  <div style={{
    background: 'var(--bg-card)',
    border: `1px solid var(--border-dim)`,
    borderTop: `2px solid ${accent}`,
    borderRadius: 'var(--radius-md)',
    padding: '20px 22px',
  }}>
    <div style={{ color: 'var(--text-2)', fontSize: 10, letterSpacing: '0.15em', marginBottom: 12, fontFamily: 'var(--font-mono)' }}>
      {label}
    </div>
    <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 28, color: accent, lineHeight: 1 }}>
      {formatter ? formatter(value) : fmtNum(value)}{suffix}
    </div>
  </div>
)

export default function Dashboard() {
  useWebSocket()
  const { currentInside, checkinsToday, checkoutsToday, revenueToday, errorRateToday, visitorData, setVisitorData } = useReportStore()
  const { recentEvents, gatesStatus, setGatesStatus } = useGateStore()

  useEffect(() => {
    reportApi.visitors({ date_from: new Date(Date.now() - 86400000).toISOString() })
      .then(r => setVisitorData(r.data)).catch(() => {})
    gateApi.list().then(r => setGatesStatus(
      r.data.map(g => ({ gate_id: g.gate_id, gate_code: g.gate_code, name: g.name, last_event: null }))
    )).catch(() => {})
  }, [])

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 800, color: 'var(--text-1)', marginBottom: 4 }}>
            Tổng quan vận hành
          </h2>
          <p style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
            Realtime · Cập nhật mỗi 5 giây
          </p>
        </div>
        <div style={{ color: 'var(--text-3)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
          {new Date().toLocaleDateString('vi-VN', { weekday:'long', year:'numeric', month:'long', day:'numeric' })}
        </div>
      </div>

      {/* Stats row */}
      <Row gutter={[14, 14]} style={{ marginBottom: 20 }}>
        <Col xs={12} md={8} xl={24/5 * 1}>
          <StatCard label="Khách trong khu"      value={currentInside}   accent="var(--cyan)" />
        </Col>
        <Col xs={12} md={8} xl={24/5 * 1}>
          <StatCard label="Vào hôm nay"          value={checkinsToday}   accent="var(--green)" />
        </Col>
        <Col xs={12} md={8} xl={24/5 * 1}>
          <StatCard label="Ra hôm nay"           value={checkoutsToday}  accent="var(--amber)" />
        </Col>
        <Col xs={12} md={8} xl={24/5 * 1}>
          <StatCard label="Doanh thu hôm nay"    value={revenueToday}    accent="var(--cyan)"  formatter={fmtVnd} />
        </Col>
        <Col xs={12} md={8} xl={24/5 * 1}>
          <StatCard label="Tỷ lệ lỗi hôm nay"   value={+(errorRateToday||0).toFixed(1)} accent="var(--red)" suffix="%" />
        </Col>
      </Row>

      {/* Charts row */}
      <Row gutter={[14, 14]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={16}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 'var(--radius-md)', padding: 20 }}>
            <div style={{ color: 'var(--text-2)', fontSize: 11, letterSpacing: '0.12em', marginBottom: 16, fontFamily: 'var(--font-mono)' }}>
              GIỜ CAO ĐIỂM
            </div>
            <PeakHourChart data={visitorData?.by_hour || []} />
          </div>
        </Col>
        <Col xs={24} lg={8}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 'var(--radius-md)', padding: 20, height: '100%' }}>
            <div style={{ color: 'var(--text-2)', fontSize: 11, letterSpacing: '0.12em', marginBottom: 16, fontFamily: 'var(--font-mono)' }}>
              KÊNH XÁC THỰC
            </div>
            <ChannelPieChart data={visitorData?.by_channel || []} />
          </div>
        </Col>
      </Row>

      {/* Bottom row */}
      <Row gutter={[14, 14]}>
        <Col xs={24} lg={14}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 'var(--radius-md)', padding: 20 }}>
            <div style={{ color: 'var(--text-2)', fontSize: 11, letterSpacing: '0.12em', marginBottom: 16, fontFamily: 'var(--font-mono)' }}>
              SỰ KIỆN GẦN NHẤT
            </div>
            <RealtimeTable events={recentEvents} />
          </div>
        </Col>
        <Col xs={24} lg={10}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 'var(--radius-md)', padding: 20 }}>
            <div style={{ color: 'var(--text-2)', fontSize: 11, letterSpacing: '0.12em', marginBottom: 16, fontFamily: 'var(--font-mono)' }}>
              TRẠNG THÁI CỔNG
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {gatesStatus.length === 0 && (
                <div style={{ color: 'var(--text-3)', fontSize: 12, textAlign: 'center', padding: '20px 0' }}>
                  Chưa có dữ liệu cổng
                </div>
              )}
              {gatesStatus.map(g => <GateStatusCard key={g.gate_id} gate={g} />)}
            </div>
          </div>
        </Col>
      </Row>
    </div>
  )
}
 