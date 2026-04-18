import React, { useState, useEffect } from 'react'
import { Table, Rate, Card, Row, Col, Progress, Spin } from 'antd'
import { reviewApi } from '../services/api'
import { fmtDateTime } from '../utils/format'

export default function Reviews() {
  const [reviews, setReviews] = useState([])
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [rList, rStats] = await Promise.all([
        reviewApi.list(),
        reviewApi.getStats()
      ])
      setReviews(rList.data || [])
      setStats(rStats.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // Refresh mỗi 30s
    const timer = setInterval(loadData, 30000)
    return () => clearInterval(timer)
  }, [])

  const COLS = [
    {
      title: 'THỜI GIAN', dataIndex: 'created_at', width: 180,
      render: v => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color:'var(--text-3)' }}>{fmtDateTime(v)}</span>
    },
    {
      title: 'KHÁCH HÀNG', dataIndex: 'customer_name', width: 160,
      render: v => <span style={{ color: 'var(--cyan)', fontWeight: 600 }}>{v}</span>
    },
    {
      title: 'ĐÁNH GIÁ', dataIndex: 'rating', width: 150,
      render: v => <Rate disabled defaultValue={v} style={{ fontSize: 12 }} />
    },
    {
      title: 'NHẬN XÉT', dataIndex: 'comment',
      render: v => <span style={{ color: 'var(--text-2)', fontSize: 13 }}>{v || <i style={{ color:'var(--text-3)' }}>(Không có nội dung)</i>}</span>
    }
  ]

  if (loading && !stats) return <div style={{ textAlign:'center', padding:100 }}><Spin /></div>

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight: 800, color: 'var(--text-1)', marginBottom: 4 }}>
          Đánh giá từ khách hàng
        </h2>
        <p style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
          Phản hồi thực tế về chất lượng dịch vụ khu du lịch
        </p>
      </div>

      <Row gutter={20} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <div style={{ 
            background:'var(--bg-card)', padding:24, borderRadius:'var(--radius-md)', 
            border:'1px solid var(--border-dim)', textAlign:'center', height:'100%' 
          }}>
            <div style={{ color:'var(--text-3)', fontSize:12, marginBottom:8, fontFamily:'var(--font-mono)' }}>ĐIỂM TRUNG BÌNH</div>
            <div style={{ fontSize:48, fontWeight:800, color:'var(--cyan)', fontFamily:'var(--font-display)' }}>
              {stats?.average_rating || 0}
            </div>
            <Rate disabled allowHalf value={stats?.average_rating || 0} style={{ color:'var(--cyan)', marginBottom:16 }} />
            <div style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
              Dựa trên {stats?.total_reviews || 0} đánh giá
            </div>
          </div>
        </Col>
        <Col xs={24} md={16}>
          <div style={{ 
            background:'var(--bg-card)', padding:20, borderRadius:'var(--radius-md)', 
            border:'1px solid var(--border-dim)', height:'100%' 
          }}>
             <div style={{ color:'var(--text-3)', fontSize:11, marginBottom:16, fontFamily:'var(--font-mono)' }}>PHÂN PHỐI SAO</div>
             {[5, 4, 3, 2, 1].map(star => {
               const count = stats?.rating_distribution?.[star] || 0
               const percent = stats?.total_reviews ? (count / stats.total_reviews) * 100 : 0
               return (
                 <div key={star} style={{ display:'flex', alignItems:'center', gap:12, marginBottom:8 }}>
                    <span style={{ width:40, color:'var(--text-2)', fontSize:11, fontFamily:'var(--font-mono)' }}>{star} Sao</span>
                    <div style={{ flex:1 }}>
                        <Progress 
                            percent={percent} 
                            showInfo={false} 
                            strokeColor={star >= 4 ? 'var(--cyan)' : star >= 3 ? 'var(--amber)' : 'var(--red)'}
                            trailColor="var(--bg-surface)"
                        />
                    </div>
                    <span style={{ width:30, color:'var(--text-3)', fontSize:11, textAlign:'right', fontFamily:'var(--font-mono)' }}>{count}</span>
                 </div>
               )
             })}
          </div>
        </Col>
      </Row>

      <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)', borderRadius:'var(--radius-md)', overflow:'hidden' }}>
        <Table 
          columns={COLS} 
          dataSource={reviews} 
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 8 }}
        />
      </div>
    </div>
  )
}
