import React, { useState, useEffect } from 'react'
import { Table, Tag, Space, Input, Select, Button, message, Tooltip } from 'antd'
import { reportApi } from '../services/api'
import dayjs from 'dayjs'
import { fmtDateTime } from '../utils/format'

const { Option } = Select

const ACTION_MAP = {
  ISSUE_TICKET:        { label: '🎫 PHÁT HÀNH', color: 'var(--green)' },
  REVOKE_TICKET:       { label: '✕ THU HỒI', color: 'var(--red)' },
  TICKET_AUTO_EXPIRED: { label: '🕒 HẾT HẠN TỰ ĐỘNG', color: 'var(--amber)' },
  EXPORT_REPORT:       { label: '📂 XUẤT BÁO CÁO', color: 'var(--cyan)' },
  LOGIN:               { label: '🔑 ĐĂNG NHẬP', color: 'var(--text-3)' },
}

export default function AuditLogs() {
  const [data, setData]       = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch]   = useState('')
  const [action, setAction]   = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const r = await reportApi.auditLogs({
        resource: search || undefined,
        action: action || undefined,
        limit: 50
      })
      setData(r.data || [])
    } catch { 
      message.error('Không thể tải nhật ký hệ thống')
      setData([]) 
    }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
  }, [])

  const columns = [
    {
      title: 'THỜI GIAN', dataIndex: 'timestamp', width: 180,
      render: v => <span style={{ color: 'var(--text-2)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{fmtDateTime(v)}</span>
    },
    {
      title: 'HÀNH ĐỘNG', dataIndex: 'action', width: 160,
      render: v => {
        const cfg = ACTION_MAP[v] || { label: v, color: 'var(--text-3)' }
        return (
          <Tag color={cfg.color} style={{ background: `${cfg.color}11`, borderColor: `${cfg.color}33`, fontSize: 10, fontWeight: 700, borderRadius: 2 }}>
            {cfg.label}
          </Tag>
        )
      }
    },
    {
      title: 'NGƯỜI THỰC HIỆN', dataIndex: 'user_id', width: 150,
      render: v => <span style={{ color: v === 'system_auto' ? 'var(--amber)' : 'var(--cyan)', fontSize: 11, fontWeight: 600 }}>{v === 'system_auto' ? '🤖 HỆ THỐNG' : v}</span>
    },
    {
        title: 'TÀI NGUYÊN', dataIndex: 'resource', width: 180,
        render: v => <span style={{ color: 'var(--text-1)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{v || '—'}</span>
    },
    {
      title: 'CHI TIẾT', dataIndex: 'detail',
      render: v => {
        if (!v) return null
        const lines = Object.entries(v).map(([k, val]) => `${k}: ${val}`)
        return (
          <div style={{ color: 'var(--text-3)', fontSize: 11, lineHeight: 1.5 }}>
            {lines.map((l, i) => <div key={i}>• {l}</div>)}
          </div>
        )
      }
    },
    {
      title: 'IP', dataIndex: 'ip', width: 120,
      render: v => <span style={{ color: 'var(--text-3)', fontSize: 10 }}>{v || 'local'}</span>
    }
  ]

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 800, color: 'var(--text-1)', marginBottom: 4 }}>
          Nhật ký hệ thống
        </h2>
        <p style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
          Theo dõi các hoạt động quan trọng, thay đổi trạng thái vé và thao tác quản trị
        </p>
      </div>

      <div style={{ 
        display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap',
        background: 'var(--bg-card)', padding: '16px', borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-dim)' 
      }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ color: 'var(--text-3)', fontSize: 10, marginBottom: 6, fontFamily: 'var(--font-mono)' }}>LỌC TÀI NGUYÊN (TICKET ID)</div>
          <Input 
            placeholder="Nhập Ticket ID..." 
            value={search} 
            onChange={e => setSearch(e.target.value)}
            onPressEnter={load}
            style={{ height: 38 }}
          />
        </div>
        <div style={{ width: 180 }}>
          <div style={{ color: 'var(--text-3)', fontSize: 10, marginBottom: 6, fontFamily: 'var(--font-mono)' }}>LOẠI HÀNH ĐỘNG</div>
          <Select value={action} onChange={setAction} style={{ width: '100%', height: 38 }} placeholder="Tất cả" allowClear>
            {Object.entries(ACTION_MAP).map(([k, v]) => (
              <Option key={k} value={k}>{v.label}</Option>
            ))}
          </Select>
        </div>
        <div style={{ alignSelf: 'flex-end' }}>
          <Button type="primary" onClick={load} loading={loading} style={{ height: 38, padding: '0 24px' }}>
            LỌC DỮ LIỆU
          </Button>
        </div>
      </div>

      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="_id"
          pagination={{ pageSize: 15 }}
          locale={{ emptyText: <div style={{ padding: 40, color: 'var(--text-3)' }}>Không tìm thấy nhật ký nào</div> }}
        />
      </div>
    </div>
  )
}
