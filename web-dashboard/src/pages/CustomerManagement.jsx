import React, { useState, useEffect } from 'react'
import { Modal, Form, Input, message } from 'antd'
import api from '../services/api'
import useAuthStore from '../store/authStore'

// ── API ───────────────────────────────────────────────────────
const customerApi = {
  list:   ()           => api.get('/customer/all'),
  update: (id, data)   => api.patch(`/customer/${id}`, data),
  delete: (id)         => api.delete(`/customer/${id}`),
}

// ── Sub components ────────────────────────────────────────────
const Panel = ({ children, style }) => (
  <div style={{
    background: 'var(--bg-card)', border: '1px solid var(--border-dim)',
    borderRadius: 'var(--radius-md)', padding: 20, ...style,
  }}>{children}</div>
)

const Label = ({ children }) => (
  <div style={{ color: 'var(--text-2)', fontSize: 11, letterSpacing: '0.12em', marginBottom: 14, fontFamily: 'var(--font-mono)' }}>
    {children}
  </div>
)

const MODAL_STYLES = {
  body:    { background: 'var(--bg-card)', paddingTop: 16 },
  header:  { background: 'var(--bg-card)', borderBottom: '1px solid var(--border-dim)' },
  footer:  { background: 'var(--bg-card)', borderTop: '1px solid var(--border-dim)' },
  mask:    { backdropFilter: 'blur(4px)' },
  content: { background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 'var(--radius-md)' },
}

// ── Main ──────────────────────────────────────────────────────
export default function CustomerManagement() {
  const myRole = useAuthStore(s => s.role)
  const [customers, setCustomers] = useState([])
  const [loading, setLoading]     = useState(false)
  
  // Search state
  const [search, setSearch]       = useState('')

  // Modal xác nhận xóa
  const [deleteCust, setDeleteCust] = useState(null)
  const [deleting, setDeleting]     = useState(false)

  // Modal chỉnh sửa
  const [editCust, setEditCust]     = useState(null)
  const [saving, setSaving]         = useState(false)
  const [editForm]                  = Form.useForm()

  const isAdmin = myRole === 'admin'
  const isManager = myRole === 'manager' || isAdmin

  const loadCustomers = async () => {
    setLoading(true)
    try {
      const r = await customerApi.list()
      setCustomers(r.data || [])
    } catch { 
      message.error("Lỗi khi tải danh sách khách hàng")
      setCustomers([]) 
    }
    finally { setLoading(false) }
  }

  useEffect(() => {
    loadCustomers()
  }, [])

  // ── Mở modal edit ─────────────────────────────────────────
  const openEdit = (cust) => {
    setEditCust(cust)
    editForm.setFieldsValue({
      name: cust.name,
      email: cust.email,
    })
  }

  // ── Lưu chỉnh sửa ────────────────────────────────────────
  const handleSave = async (values) => {
    if (!editCust) return
    setSaving(true)
    try {
      await customerApi.update(editCust.id, values)
      message.success(`Cập nhật khách hàng "${editCust.name}" thành công`)
      setEditCust(null)
      editForm.resetFields()
      loadCustomers()
    } catch (e) {
      message.error(e.response?.data?.detail || 'Cập nhật thất bại')
    } finally { setSaving(false) }
  }

  // ── Xóa tài khoản ────────────────────────────────────────
  const handleDelete = async () => {
    if (!deleteCust) return
    setDeleting(true)
    try {
      await customerApi.delete(deleteCust.id)
      message.success(`Đã xóa tài khoản khách hàng "${deleteCust.name}"`)
      setDeleteCust(null)
      loadCustomers()
    } catch (e) {
      message.error(e.response?.data?.detail || 'Xóa tài khoản thất bại')
    } finally { setDeleting(false) }
  }

  // Lọc danh sách theo search
  const filtered = customers.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) || 
    c.email.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 800, color: 'var(--text-1)', marginBottom: 4 }}>
            Quản lý khách hàng
          </h2>
          <p style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
            Xem danh sách, sửa thông tin và quản lý tài khoản khách hàng đăng ký App
          </p>
        </div>
      </div>

      {!isManager && (
        <div style={{
          padding: '12px 16px', marginBottom: 20,
          background: 'rgba(255,184,0,0.08)', border: '1px solid rgba(255,184,0,0.2)',
          borderRadius: 'var(--radius-sm)', color: 'var(--amber)', fontSize: 13, fontFamily: 'var(--font-mono)',
        }}>
          ⚠ Bạn không có quyền truy cập trang này.
        </div>
      )}

      {isManager && (
        <>
          {/* Toolbar */}
          <Panel style={{ marginBottom: 20, display: 'flex', gap: 12, alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <Input 
                placeholder="Tìm kiếm theo tên hoặc email..." 
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ 
                  background: 'var(--bg-card)', 
                  border: '1px solid var(--border-dim)',
                  height: 42,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-1)'
                }}
              />
            </div>
            <button onClick={loadCustomers} style={{
              background: 'transparent', border: '1px solid var(--border-dim)',
              color: 'var(--text-2)', padding: '0 20px', borderRadius: 'var(--radius-sm)',
              cursor: 'pointer', fontSize: 13, fontFamily: 'var(--font-mono)', height: 42
            }}>↻ TẢI LẠI</button>
          </Panel>

          {/* Customer table */}
          <Panel>
            <Label>DANH SÁCH KHÁCH HÀNG ({filtered.length})</Label>
            
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                <thead>
                  <tr>
                    {['TÊN KHÁCH HÀNG','EMAIL','ID','THAO TÁC'].map(h => (
                      <th key={h} style={{
                        padding: '9px 12px', textAlign: 'left',
                        color: 'var(--text-3)', fontSize: 10, letterSpacing: '0.1em',
                        borderBottom: '1px solid var(--border-dim)', fontWeight: 400,
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading && (
                    <tr><td colSpan={4} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-3)', fontSize: 12 }}>
                      Đang tải dữ liệu...
                    </td></tr>
                  )}
                  {!loading && filtered.length === 0 && (
                    <tr><td colSpan={4} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-3)', fontSize: 12 }}>
                      {search ? 'Không tìm thấy kết quả phù hợp' : 'Chưa có khách hàng nào đăng ký'}
                    </td></tr>
                  )}
                  {filtered.map(c => (
                    <tr key={c.id} style={{ borderBottom: '1px solid var(--border-dim)' }}>
                      <td style={{ padding: '12px', color: 'var(--text-1)', fontWeight: 600 }}>{c.name}</td>
                      <td style={{ padding: '12px', color: 'var(--cyan)' }}>{c.email}</td>
                      <td style={{ padding: '12px', color: 'var(--text-3)', fontSize: 11 }}>{c.id}</td>
                      <td style={{ padding: '12px' }}>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button
                            onClick={() => openEdit(c)}
                            disabled={!isAdmin}
                            style={{
                              background: 'var(--cyan-dim)', border: '1px solid rgba(0,229,255,0.3)',
                              color: 'var(--cyan)', padding: '4px 10px', borderRadius: 4,
                              cursor: isAdmin ? 'pointer' : 'not-allowed', fontSize: 11, fontFamily: 'var(--font-mono)',
                              opacity: isAdmin ? 1 : 0.5
                            }}
                          >
                            ✎ Sửa
                          </button>
                          <button
                            onClick={() => setDeleteCust(c)}
                            disabled={!isAdmin}
                            style={{
                              background: 'transparent',
                              border: '1px solid rgba(255,51,102,0.25)',
                              color: 'var(--red)', padding: '4px 10px', borderRadius: 4,
                              cursor: isAdmin ? 'pointer' : 'not-allowed', fontSize: 11, fontFamily: 'var(--font-mono)',
                              opacity: isAdmin ? 1 : 0.5
                            }}
                          >
                            ✕ Xóa
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}

      {/* ── Modal XÁC NHẬN XÓA ── */}
      <Modal
        open={!!deleteCust}
        title={<span style={{ fontFamily: 'var(--font-mono)', color: 'var(--red)' }}>✕ Xóa tài khoản khách hàng</span>}
        onCancel={() => setDeleteCust(null)}
        onOk={handleDelete}
        okText="Xóa vĩnh viễn"
        okButtonProps={{ danger: true, loading: deleting, style: { fontFamily: 'var(--font-mono)' } }}
        cancelText="Hủy"
        styles={MODAL_STYLES}
      >
        <div style={{ padding: '8px 0' }}>
          <p style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontSize: 13, lineHeight: 1.8 }}>
            Bạn chắc chắn muốn xóa tài khoản khách hàng
            {' '}<strong style={{ color: 'var(--cyan)' }}>{deleteCust?.name}</strong>?
          </p>
          <div style={{
            marginTop: 12, padding: '10px 14px',
            background: 'var(--red-dim)', border: '1px solid rgba(255,51,102,0.25)',
            borderRadius: 'var(--radius-sm)', color: 'var(--red)',
            fontSize: 12, fontFamily: 'var(--font-mono)',
          }}>
            ⚠ Hành động này không thể hoàn tác. Khách hàng sẽ không thể đăng nhập vào App được nữa.
          </div>
        </div>
      </Modal>

      {/* ── Modal CHỈNH SỬA ── */}
      <Modal
        open={!!editCust}
        title={
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-1)' }}>
            ✎ Sửa thông tin khách hàng
          </span>
        }
        onCancel={() => { setEditCust(null); editForm.resetFields() }}
        onOk={() => editForm.submit()}
        okText="Lưu thay đổi"
        confirmLoading={saving}
        styles={MODAL_STYLES}
      >
        <Form form={editForm} layout="vertical" onFinish={handleSave}>
          <Form.Item name="name" label="TÊN KHÁCH HÀNG" rules={[{ required: true }]}>
            <Input style={{ height: 42, background: 'var(--bg-card)', color: 'var(--text-1)' }} />
          </Form.Item>
          <Form.Item name="email" label="EMAIL" rules={[{ required: true, type: 'email' }]}>
            <Input style={{ height: 42, background: 'var(--bg-card)', color: 'var(--text-1)' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
