import React, { useState, useEffect } from 'react'
import { Table, Input, Button, Tag, Space, Modal, message, Select } from 'antd'
import { ticketApi } from '../services/api'
import dayjs from 'dayjs'
import QrDownloadButton from '../components/QrDownloadButton'
import { fmtVnd, fmtDateTime, NUM_COL_STYLE } from '../utils/format'

const { Option } = Select

const STATUS_CONFIG = {
  OUTSIDE: { color: 'var(--text-2)',  bg: 'var(--bg-hover)', label: 'Ngoài khu' },
  INSIDE:  { color: 'var(--green)',   bg: 'var(--green-dim)',  label: 'Trong khu' },
  revoked: { color: 'var(--red)',     bg: 'var(--red-dim)',    label: 'Thu hồi' },
  expired: { color: 'var(--text-3)', bg: 'transparent',       label: 'Hết hạn' },
  active:  { color: 'var(--text-2)', bg: 'var(--bg-hover)',   label: 'Chưa sử dụng' },
}

const StatusBadge = ({ status }) => {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.OUTSIDE
  return (
    <span style={{
      display: 'inline-block', padding: '3px 10px', borderRadius: 4,
      background: cfg.bg, color: cfg.color, fontSize: 11,
      fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', border: `1px solid ${cfg.color}33`,
    }}>
      {cfg.label}
    </span>
  )
}

const TYPE_MAP = { adult:'Người lớn', child:'Trẻ em', student:'Học sinh/SV', group:'Nhóm' }

export default function Tickets() {
  const [data, setData]         = useState([])
  const [loading, setLoading]   = useState(false)
  const [search, setSearch]     = useState('')
  const [ticketType, setTicketType] = useState(null)
  const [status, setStatus]     = useState(null)
  const [revoking, setRevoking] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      // Gọi API search mới được update ở backend
      const r = await ticketApi.search({
        q: search || undefined,
        ticket_type: ticketType || undefined,
        status: status || undefined
      })
      setData(r.data || [])
    } catch { setData([]) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
  }, [])

  const handleRevoke = async (ticket_id) => {
    try {
      await ticketApi.revoke(ticket_id, { reason: 'manual_revoke' })
      message.success('Đã thu hồi vé')
      setRevoking(null)
      load()
    } catch (e) {
      message.error(e.response?.data?.detail || 'Lỗi thu hồi vé')
    }
  }

  const COLS = [
    {
      title: 'TICKET ID', dataIndex: 'ticket_id', width: 220,
      render: v => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--cyan)' }}>{v}</span>
    },
    {
      title: 'LOẠI VÉ', dataIndex: 'ticket_type',
      render: v => <span style={{ color: 'var(--text-1)', fontSize: 13 }}>{TYPE_MAP[v] || v}</span>
    },
    {
      title: 'GIÁ', dataIndex: 'price',
      render: v => <span style={NUM_COL_STYLE}>{fmtVnd(v)}</span>
    },
    {
      title: 'TRẠNG THÁI', dataIndex: 'status',
      render: v => <StatusBadge status={v} />
    },
    {
        title: 'NGƯỜI BÁN', dataIndex: 'issued_by_name',
        render: v => <span style={{ color: 'var(--text-3)', fontSize: 11 }}>{v || 'Online'}</span>
    },
    {
      title: 'FACE ID', dataIndex: 'has_face',
      render: v => v
        ? <span style={{ color:'var(--green)', fontSize:10, fontFamily:'var(--font-mono)' }}>✓ ĐÃ ĐĂNG KÝ</span>
        : <span style={{ color:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }}>— Trống</span>
    },
    {
      title: 'HẾT HẠN', dataIndex: 'valid_until',
      render: v => <span style={{ color:'var(--text-2)', fontSize:11, ...NUM_COL_STYLE }}>
        {fmtDateTime(v)}
      </span>
    },
    {
      title: '', key: 'action',
      render: (_, record) => (
        <Space size="small">
          <QrDownloadButton ticketId={record.ticket_id} />
          {record.status !== 'revoked' && (
            <button
              onClick={() => setRevoking(record)}
              style={{
                background: 'var(--red-dim)', border: '1px solid rgba(255,51,102,0.3)',
                color: 'var(--red)', padding: '5px 12px', borderRadius: 4,
                cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)',
              }}
            >
              ✕
            </button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24, display:'flex', alignItems:'baseline', justifyContent:'space-between' }}>
        <div>
          <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight: 800, color: 'var(--text-1)', marginBottom: 4 }}>
            Quản lý vé
          </h2>
          <p style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
            Tra cứu, lọc dữ liệu và thu hồi vé
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div style={{ 
        display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap',
        background: 'var(--bg-card)', padding: '16px', borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-dim)' 
      }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ color: 'var(--text-3)', fontSize: 10, marginBottom: 6, fontFamily: 'var(--font-mono)' }}>TÌM KIẾM (ID/BOOKING)</div>
          <Input
            placeholder="Nhập Ticket ID hoặc Booking ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onPressEnter={load}
            style={{ height: 38 }}
          />
        </div>
        <div style={{ width: 140 }}>
            <div style={{ color: 'var(--text-3)', fontSize: 10, marginBottom: 6, fontFamily: 'var(--font-mono)' }}>LOẠI VÉ</div>
            <Select value={ticketType} onChange={setTicketType} style={{ width: '100%', height: 38 }} placeholder="Tất cả" allowClear>
                {Object.entries(TYPE_MAP).map(([k, v]) => <Option key={k} value={k}>{v}</Option>)}
            </Select>
        </div>
        <div style={{ width: 140 }}>
            <div style={{ color: 'var(--text-3)', fontSize: 10, marginBottom: 6, fontFamily: 'var(--font-mono)' }}>TRẠNG THÁI</div>
            <Select value={status} onChange={setStatus} style={{ width: '100%', height: 38 }} placeholder="Tất cả" allowClear>
                {Object.entries(STATUS_CONFIG).map(([k, v]) => <Option key={k} value={k}>{v.label}</Option>)}
            </Select>
        </div>
        <div style={{ alignSelf: 'flex-end' }}>
            <Button type="primary" onClick={load} loading={loading} style={{ height: 38, padding: '0 24px' }}>
                LỌC DỮ LIỆU
            </Button>
        </div>
      </div>

      {/* Table */}
      <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)', borderRadius:'var(--radius-md)', overflow:'hidden' }}>
        <Table
          columns={COLS}
          dataSource={data}
          loading={loading}
          rowKey="ticket_id"
          pagination={{ pageSize: 10, showSizeChanger: false }}
          locale={{ emptyText: (
            <div style={{ padding:'40px 0', color:'var(--text-3)', fontFamily:'var(--font-mono)', fontSize:13 }}>
              {search || ticketType || status ? 'Không tìm thấy vé nào phù hợp' : 'Nhấn "Lọc dữ liệu" để xem danh sách vé mới nhất'}
            </div>
          )}}
        />
      </div>

      <Modal
        open={!!revoking}
        title={<span style={{ fontFamily:'var(--font-mono)', color:'var(--text-1)' }}>✕ THU HỒI VÉ</span>}
        onOk={() => handleRevoke(revoking?.ticket_id)}
        onCancel={() => setRevoking(null)}
        okText="Xác nhận thu hồi"
        okButtonProps={{ danger: true }}
        styles={{ body: { background:'var(--bg-card)' }, header: { background:'var(--bg-card)' }, footer: { background:'var(--bg-card)' }, mask: { backdropFilter:'blur(4px)' } }}
      >
        <p style={{ color:'var(--text-2)', fontFamily:'var(--font-mono)', fontSize:13, lineHeight: 1.6 }}>
          Bạn đang thu hồi vé <strong style={{ color:'var(--cyan)' }}>{revoking?.ticket_id}</strong>?
          <br/>
          Hành động này không thể hoàn tác và vé sẽ không thể check-in được nữa.
        </p>
      </Modal>
    </div>
  )
}
 