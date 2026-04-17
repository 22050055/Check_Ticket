import React, { useState, useEffect } from 'react'
import { Table, Input, Button, Tag, Space, Modal, message } from 'antd'
import { ticketApi } from '../services/api'
import dayjs from 'dayjs'
import QrDownloadButton from '../components/QrDownloadButton'

const STATUS_CONFIG = {
  OUTSIDE: { color: 'var(--text-2)',  bg: 'var(--bg-hover)', label: 'Ngoài khu' },
  INSIDE:  { color: 'var(--green)',   bg: 'var(--green-dim)',  label: 'Trong khu' },
  revoked: { color: 'var(--red)',     bg: 'var(--red-dim)',    label: 'Thu hồi' },
  expired: { color: 'var(--text-3)', bg: 'transparent',       label: 'Hết hạn' },
  active:  { color: 'var(--text-2)', bg: 'var(--bg-hover)',   label: 'Ngoài khu' },  // compat
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
  const [revoking, setRevoking] = useState(null)

  const load = async (q = '') => {
    setLoading(true)
    try {
      // Demo: load ticket by ID search
      if (q.length > 4) {
        const r = await ticketApi.get(q.trim())
        setData([r.data])
      } else {
        setData([])
      }
    } catch { setData([]) }
    finally { setLoading(false) }
  }

  const handleRevoke = async (ticket_id) => {
    try {
      await ticketApi.revoke(ticket_id, { reason: 'manual_revoke' })
      message.success('Đã thu hồi vé')
      setRevoking(null)
      load(search)
    } catch (e) {
      message.error(e.response?.data?.detail || 'Lỗi thu hồi vé')
    }
  }

  const COLS = [
    {
      title: 'TICKET ID', dataIndex: 'ticket_id', width: 280,
      render: v => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--cyan)' }}>{v}</span>
    },
    {
      title: 'LOẠI VÉ', dataIndex: 'ticket_type',
      render: v => <span style={{ color: 'var(--text-1)', fontSize: 13 }}>{TYPE_MAP[v] || v}</span>
    },
    {
      title: 'GIÁ', dataIndex: 'price',
      render: v => <span style={{ fontFamily: 'var(--font-mono)' }}>{new Intl.NumberFormat('vi-VN').format(v)}đ</span>
    },
    {
      title: 'TRẠNG THÁI', dataIndex: 'status',
      render: v => <StatusBadge status={v} />
    },
    {
      title: 'FACE ID', dataIndex: 'has_face',
      render: v => v
        ? <span style={{ color:'var(--green)', fontSize:11, fontFamily:'var(--font-mono)' }}>✓ ĐÃ ĐĂNG KÝ</span>
        : <span style={{ color:'var(--text-3)', fontSize:11, fontFamily:'var(--font-mono)' }}>— Không có</span>
    },
    {
      title: 'HẾT HẠN', dataIndex: 'valid_until',
      render: v => <span style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
        {dayjs(v).format('DD/MM/YYYY HH:mm')}
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
                letterSpacing: '0.08em',
              }}
            >
              THU HỒI
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
          <h2 style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--text-1)', marginBottom:4 }}>
            Quản lý vé
          </h2>
          <p style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
            Tra cứu, kiểm tra trạng thái và thu hồi vé
          </p>
        </div>
        {/* State machine legend */}
        <div style={{ display:'flex', gap:12, alignItems:'center' }}>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            <span style={{ width:8, height:8, borderRadius:'50%', background:'var(--text-2)', display:'inline-block' }}/>
            <span style={{ color:'var(--text-2)', fontSize:11, fontFamily:'var(--font-mono)' }}>OUTSIDE</span>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            <span style={{ width:8, height:8, borderRadius:'50%', background:'var(--green)', display:'inline-block' }}/>
            <span style={{ color:'var(--text-2)', fontSize:11, fontFamily:'var(--font-mono)' }}>INSIDE</span>
          </div>
        </div>
      </div>

      {/* Info banner */}
      <div style={{
        marginBottom: 20, padding: '12px 16px',
        background: 'var(--cyan-dim)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-sm)', display:'flex', gap:12, alignItems:'center',
      }}>
        <span style={{ color:'var(--cyan)', fontSize:16 }}>ℹ</span>
        <span style={{ color:'var(--text-2)', fontSize:12, fontFamily:'var(--font-mono)' }}>
          Phát hành vé mới được thực hiện tại <strong style={{ color:'var(--text-1)' }}>Gate App</strong> (Nhân viên bán vé). Dashboard chỉ tra cứu và thu hồi.
        </span>
      </div>

      {/* Search */}
      <div style={{ display:'flex', gap:10, marginBottom:20 }}>
        <Input
          placeholder="Nhập Ticket ID để tra cứu..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onPressEnter={() => load(search)}
          style={{ maxWidth: 400, height:42, borderRadius:'var(--radius-sm)' }}
        />
        <Button onClick={() => load(search)} loading={loading} style={{ height:42, borderRadius:'var(--radius-sm)' }}>
          Tra cứu
        </Button>
      </div>

      {/* Table */}
      <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)', borderRadius:'var(--radius-md)', overflow:'hidden' }}>
        <Table
          columns={COLS}
          dataSource={data}
          loading={loading}
          rowKey="ticket_id"
          pagination={false}
          locale={{ emptyText: (
            <div style={{ padding:'40px 0', color:'var(--text-3)', fontFamily:'var(--font-mono)', fontSize:13, textAlign:'center' }}>
              Nhập Ticket ID để tra cứu vé
            </div>
          )}}
        />
      </div>

      {/* Revoke confirm */}
      <Modal
        open={!!revoking}
        title={<span style={{ fontFamily:'var(--font-mono)', color:'var(--text-1)' }}>Xác nhận thu hồi vé</span>}
        onOk={() => handleRevoke(revoking?.ticket_id)}
        onCancel={() => setRevoking(null)}
        okText="Thu hồi"
        okButtonProps={{ danger: true }}
        styles={{ body: { background:'var(--bg-card)' }, header: { background:'var(--bg-card)' }, footer: { background:'var(--bg-card)' }, mask: { backdropFilter:'blur(4px)' } }}
      >
        <p style={{ color:'var(--text-2)', fontFamily:'var(--font-mono)', fontSize:13 }}>
          Thu hồi vé <strong style={{ color:'var(--cyan)' }}>{revoking?.ticket_id}</strong>?
          <br/><br/>
          Hành động này không thể hoàn tác.
        </p>
      </Modal>
    </div>
  )
}
 