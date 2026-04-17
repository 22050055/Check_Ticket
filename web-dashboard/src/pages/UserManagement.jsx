import React, { useState, useEffect } from 'react'
import { Modal, Form, Input, Select, message } from 'antd'
import api from '../services/api'
import useAuthStore from '../store/authStore'

// ── API ───────────────────────────────────────────────────────
const userApi = {
  list:   ()           => api.get('/auth/users'),
  create: (data)       => api.post('/auth/users', data),
  update: (id, data)   => api.put(`/auth/users/${id}`, data),
  delete: (id)         => api.delete(`/auth/users/${id}`),
}
const gateApi2 = { list: () => api.get('/gates') }

// ── Constants ─────────────────────────────────────────────────
const ROLE_OPTIONS = [
  { value: 'admin',    label: 'Admin',    desc: 'Toàn quyền hệ thống' },
  { value: 'manager',  label: 'Manager',  desc: 'Báo cáo, quản lý vé, tạo nhân viên' },
  { value: 'operator', label: 'Operator', desc: 'Check-in/out tại cổng' },
  { value: 'cashier',  label: 'Cashier',  desc: 'Bán vé, xem doanh thu' },
]

const ROLE_COLOR = {
  admin:    { text: 'var(--red)',   bg: 'var(--red-dim)' },
  manager:  { text: 'var(--cyan)',  bg: 'var(--cyan-dim)' },
  operator: { text: 'var(--green)', bg: 'var(--green-dim)' },
  cashier:  { text: 'var(--amber)', bg: 'rgba(255,184,0,0.12)' },
}

const PERMS = {
  admin:    ['Tổng quan','Giám sát cổng','Doanh thu','Lượt khách','Quản lý vé','Báo cáo','Quản lý nhân viên'],
  manager:  ['Tổng quan','Doanh thu','Lượt khách','Quản lý vé (thu hồi)','Báo cáo (export)'],
  operator: ['Tổng quan','Giám sát cổng'],
  cashier:  ['Tổng quan','Doanh thu'],
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

const RoleBadge = ({ role }) => {
  const c = ROLE_COLOR[role] || { text: 'var(--text-2)', bg: 'var(--bg-hover)' }
  return (
    <span style={{
      display: 'inline-block', padding: '3px 10px', borderRadius: 4,
      background: c.bg, color: c.text, fontSize: 11,
      fontFamily: 'var(--font-mono)', letterSpacing: '0.08em',
      border: `1px solid ${c.text}33`,
    }}>
      {(role || '').toUpperCase()}
    </span>
  )
}

const MODAL_STYLES = {
  body:    { background: 'var(--bg-card)', paddingTop: 16 },
  header:  { background: 'var(--bg-card)', borderBottom: '1px solid var(--border-dim)' },
  footer:  { background: 'var(--bg-card)', borderTop: '1px solid var(--border-dim)' },
  mask:    { backdropFilter: 'blur(4px)' },
  content: { background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 'var(--radius-md)' },
}

// ── Main ──────────────────────────────────────────────────────
export default function UserManagement() {
  const myRole = useAuthStore(s => s.role)
  const [users, setUsers]           = useState([])
  const [gates, setGates]           = useState([])
  const [loading, setLoading]       = useState(false)

  // Modal tạo mới
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating]     = useState(false)
  const [createForm] = Form.useForm()
  const selectedRoleCreate = Form.useWatch('role', createForm)

  // Modal xác nhận xóa
  const [deleteUser, setDeleteUser] = useState(null)
  const [deleting, setDeleting]     = useState(false)

  // Modal chỉnh sửa
  const [editUser, setEditUser]     = useState(null)   // user đang edit
  const [saving, setSaving]         = useState(false)
  const [editForm] = Form.useForm()
  const selectedRoleEdit = Form.useWatch('role', editForm)

  const isAdmin = myRole === 'admin'

  const loadUsers = async () => {
    setLoading(true)
    try {
      const r = await userApi.list()
      setUsers(r.data?.users || r.data || [])
    } catch { setUsers([]) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    loadUsers()
    gateApi2.list().then(r => setGates(r.data || [])).catch(() => {})
  }, [])

  // ── Tạo mới ───────────────────────────────────────────────
  const handleCreate = async (values) => {
    setCreating(true)
    try {
      await userApi.create(values)
      message.success(`Tạo tài khoản "${values.username}" thành công`)
      setShowCreate(false)
      createForm.resetFields()
      loadUsers()
    } catch (e) {
      message.error(e.response?.data?.detail || 'Tạo tài khoản thất bại')
    } finally { setCreating(false) }
  }

  // ── Mở modal edit ─────────────────────────────────────────
  const openEdit = (user) => {
    setEditUser(user)
    editForm.setFieldsValue({
      full_name: user.full_name || user.fullName,
      role:      user.role,
      gate_id:   user.gate_id || user.gateId || undefined,
      is_active: user.is_active !== false,
    })
  }

  // ── Lưu chỉnh sửa ────────────────────────────────────────
  const handleSave = async (values) => {
    if (!editUser) return
    setSaving(true)
    try {
      const userId = editUser._id || editUser.id
      await userApi.update(userId, values)
      message.success(`Cập nhật tài khoản "${editUser.username}" thành công`)
      setEditUser(null)
      editForm.resetFields()
      loadUsers()
    } catch (e) {
      message.error(e.response?.data?.detail || 'Cập nhật thất bại')
    } finally { setSaving(false) }
  }

  // ── Xóa tài khoản ────────────────────────────────────────
  const handleDelete = async () => {
    if (!deleteUser) return
    setDeleting(true)
    try {
      const userId = deleteUser._id || deleteUser.id
      await userApi.delete(userId)
      message.success(`Đã xóa tài khoản "${deleteUser.username}"`)
      setDeleteUser(null)
      loadUsers()
    } catch (e) {
      message.error(e.response?.data?.detail || 'Xóa tài khoản thất bại')
    } finally { setDeleting(false) }
  }

  // ── Toggle active nhanh ───────────────────────────────────
  const handleToggle = async (user) => {
    const userId = user._id || user.id
    try {
      await userApi.update(userId, { is_active: !user.is_active })
      message.success(`Đã ${user.is_active ? 'vô hiệu' : 'kích hoạt'} tài khoản`)
      loadUsers()
    } catch { message.error('Thao tác thất bại') }
  }

  // ── Role permission matrix ────────────────────────────────
  const RoleMatrix = () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
      {ROLE_OPTIONS.map(r => {
        const c = ROLE_COLOR[r.value]
        return (
          <div key={r.value} style={{
            padding: '14px 16px', background: 'var(--bg-surface)',
            border: `1px solid ${c.text}33`, borderTop: `3px solid ${c.text}`,
            borderRadius: 'var(--radius-sm)',
          }}>
            <div style={{ color: c.text, fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, marginBottom: 8 }}>
              {r.label.toUpperCase()}
            </div>
            <div style={{ color: 'var(--text-2)', fontSize: 11, marginBottom: 10, fontFamily: 'var(--font-mono)' }}>
              {r.desc}
            </div>
            {(PERMS[r.value] || []).map(p => (
              <div key={p} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                <span style={{ color: c.text, fontSize: 10 }}>✓</span>
                <span style={{ color: 'var(--text-2)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{p}</span>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )

  // ── Role select options ───────────────────────────────────
  const roleSelectOptions = ROLE_OPTIONS.map(r => ({
    value: r.value,
    label: (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <RoleBadge role={r.value} />
        <span style={{ color: 'var(--text-2)', fontSize: 12 }}>{r.desc}</span>
      </div>
    ),
  }))

  // ── Permission preview ────────────────────────────────────
  const PermPreview = ({ role }) => role ? (
    <div style={{
      padding: '12px 14px', background: 'var(--bg-surface)', marginTop: 4,
      border: `1px solid ${(ROLE_COLOR[role]?.text || 'var(--border-dim)')}33`,
      borderRadius: 'var(--radius-sm)',
    }}>
      <div style={{ color: 'var(--text-3)', fontSize: 10, letterSpacing: '0.1em', marginBottom: 8, fontFamily: 'var(--font-mono)' }}>
        QUYỀN TRUY CẬP
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {(PERMS[role] || []).map(p => (
          <span key={p} style={{
            background: 'var(--bg-hover)', color: 'var(--text-2)',
            padding: '3px 8px', borderRadius: 3, fontSize: 11, fontFamily: 'var(--font-mono)',
          }}>{p}</span>
        ))}
      </div>
    </div>
  ) : null

  // ── Action buttons ────────────────────────────────────────
  const ActionButtons = ({ user }) => {
    if (!isAdmin || user.username === 'admin') return null
    return (
      <div style={{ display: 'flex', gap: 6 }}>
        {/* Edit */}
        <button
          onClick={() => openEdit(user)}
          style={{
            background: 'var(--cyan-dim)', border: '1px solid rgba(0,229,255,0.3)',
            color: 'var(--cyan)', padding: '4px 10px', borderRadius: 4,
            cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)',
          }}
        >
          ✎ Sửa
        </button>
        {/* Toggle active */}
        <button
          onClick={() => handleToggle(user)}
          style={{
            background: user.is_active ? 'var(--red-dim)' : 'var(--green-dim)',
            border: `1px solid ${user.is_active ? 'rgba(255,51,102,0.3)' : 'rgba(0,255,136,0.3)'}`,
            color: user.is_active ? 'var(--red)' : 'var(--green)',
            padding: '4px 10px', borderRadius: 4,
            cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)',
          }}
        >
          {user.is_active ? '○ Vô hiệu' : '● Kích hoạt'}
        </button>
        {/* Xóa */}
        <button
          onClick={() => setDeleteUser(user)}
          style={{
            background: 'transparent',
            border: '1px solid rgba(255,51,102,0.25)',
            color: 'var(--red)', padding: '4px 10px', borderRadius: 4,
            cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)',
          }}
        >
          ✕ Xóa
        </button>
      </div>
    )
  }

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 800, color: 'var(--text-1)', marginBottom: 4 }}>
            Quản lý nhân viên
          </h2>
          <p style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
            Tạo tài khoản, sửa thông tin, phân quyền, quản lý trạng thái
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowCreate(true)}
            style={{
              background: 'var(--cyan)', border: 'none', color: 'var(--bg-base)',
              padding: '10px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
              fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13, letterSpacing: '0.1em',
            }}
          >
            + TẠO TÀI KHOẢN
          </button>
        )}
      </div>

      {!isAdmin && (
        <div style={{
          padding: '12px 16px', marginBottom: 20,
          background: 'rgba(255,184,0,0.08)', border: '1px solid rgba(255,184,0,0.2)',
          borderRadius: 'var(--radius-sm)', color: 'var(--amber)', fontSize: 13, fontFamily: 'var(--font-mono)',
        }}>
          ⚠ Chỉ Admin mới có thể tạo / sửa tài khoản.
        </div>
      )}

      {/* Role matrix */}
      <Panel style={{ marginBottom: 20 }}>
        <Label>PHÂN QUYỀN THEO ROLE</Label>
        <RoleMatrix />
      </Panel>

      {/* User table */}
      <Panel>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <Label style={{ marginBottom: 0 }}>DANH SÁCH TÀI KHOẢN ({users.length})</Label>
          <button onClick={loadUsers} style={{
            background: 'transparent', border: '1px solid var(--border-dim)',
            color: 'var(--text-2)', padding: '5px 12px', borderRadius: 4,
            cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)',
          }}>↻ Tải lại</button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
            <thead>
              <tr>
                {['USERNAME','HỌ TÊN','ROLE','CỔNG','TRẠNG THÁI', isAdmin ? 'THAO TÁC' : ''].filter(Boolean).map(h => (
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
                <tr><td colSpan={6} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-3)', fontSize: 12 }}>
                  Đang tải...
                </td></tr>
              )}
              {!loading && users.length === 0 && (
                <tr><td colSpan={6} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-3)', fontSize: 12 }}>
                  Chưa có dữ liệu
                </td></tr>
              )}
              {users.map(u => (
                <tr key={u._id || u.id || u.username} style={{ borderBottom: '1px solid var(--border-dim)' }}>
                  <td style={{ padding: '10px 12px', color: 'var(--cyan)' }}>{u.username}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-1)' }}>{u.full_name || u.fullName}</td>
                  <td style={{ padding: '10px 12px' }}><RoleBadge role={u.role} /></td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-2)' }}>{u.gate_id || u.gateId || '—'}</td>
                  <td style={{ padding: '10px 12px' }}>
                    {u.is_active !== false
                      ? <span style={{ color: 'var(--green)', fontSize: 11 }}>● Active</span>
                      : <span style={{ color: 'var(--text-3)', fontSize: 11 }}>○ Inactive</span>
                    }
                  </td>
                  {isAdmin && (
                    <td style={{ padding: '10px 12px' }}>
                      <ActionButtons user={u} />
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* ── Modal TẠO MỚI ── */}
      <Modal
        open={showCreate}
        title={<span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-1)' }}>+ Tạo tài khoản</span>}
        onCancel={() => { setShowCreate(false); createForm.resetFields() }}
        onOk={() => createForm.submit()}
        okText="Tạo tài khoản"
        confirmLoading={creating}
        styles={MODAL_STYLES}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="username" label="USERNAME" rules={[{ required: true, min: 3 }]}>
            <Input placeholder="vd: operator3" style={{ height: 42, borderRadius: 'var(--radius-sm)' }} />
          </Form.Item>
          <Form.Item name="full_name" label="HỌ TÊN" rules={[{ required: true }]}>
            <Input placeholder="vd: Nguyễn Văn A" style={{ height: 42, borderRadius: 'var(--radius-sm)' }} />
          </Form.Item>
          <Form.Item name="password" label="MẬT KHẨU" rules={[{ required: true, min: 6 }]}>
            <Input.Password placeholder="Tối thiểu 6 ký tự" style={{ height: 42, borderRadius: 'var(--radius-sm)' }} />
          </Form.Item>
          <Form.Item name="role" label="ROLE" rules={[{ required: true }]}>
            <Select placeholder="Chọn role..." style={{ height: 42 }} options={roleSelectOptions} />
          </Form.Item>
          {selectedRoleCreate === 'operator' && (
            <Form.Item name="gate_id" label="CỔNG PHỤ TRÁCH">
              <Select placeholder="Chọn cổng..." allowClear style={{ height: 42 }}
                options={gates.map(g => ({ value: g.gate_code, label: `${g.gate_code} — ${g.name}` }))} />
            </Form.Item>
          )}
          <PermPreview role={selectedRoleCreate} />
        </Form>
      </Modal>

      {/* ── Modal XÁC NHẬN XÓA ── */}
      <Modal
        open={!!deleteUser}
        title={<span style={{ fontFamily: 'var(--font-mono)', color: 'var(--red)' }}>✕ Xóa tài khoản</span>}
        onCancel={() => setDeleteUser(null)}
        onOk={handleDelete}
        okText="Xóa"
        okButtonProps={{ danger: true, loading: deleting, style: { fontFamily: 'var(--font-mono)' } }}
        cancelText="Hủy"
        styles={MODAL_STYLES}
      >
        <div style={{ padding: '8px 0' }}>
          <p style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontSize: 13, lineHeight: 1.8 }}>
            Bạn chắc chắn muốn xóa tài khoản
            {' '}<strong style={{ color: 'var(--cyan)' }}>{deleteUser?.username}</strong>
            {' '}({deleteUser?.full_name || deleteUser?.fullName})?
          </p>
          <div style={{
            marginTop: 12, padding: '10px 14px',
            background: 'var(--red-dim)', border: '1px solid rgba(255,51,102,0.25)',
            borderRadius: 'var(--radius-sm)', color: 'var(--red)',
            fontSize: 12, fontFamily: 'var(--font-mono)',
          }}>
            ⚠ Hành động này không thể hoàn tác. Toàn bộ dữ liệu tài khoản sẽ bị xóa vĩnh viễn.
          </div>
        </div>
      </Modal>

      {/* ── Modal CHỈNH SỬA ── */}
      <Modal
        open={!!editUser}
        title={
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-1)' }}>
            ✎ Sửa tài khoản — <span style={{ color: 'var(--cyan)' }}>{editUser?.username}</span>
          </span>
        }
        onCancel={() => { setEditUser(null); editForm.resetFields() }}
        onOk={() => editForm.submit()}
        okText="Lưu thay đổi"
        confirmLoading={saving}
        styles={MODAL_STYLES}
      >
        <Form form={editForm} layout="vertical" onFinish={handleSave}>
          <Form.Item name="full_name" label="HỌ TÊN" rules={[{ required: true }]}>
            <Input style={{ height: 42, borderRadius: 'var(--radius-sm)' }} />
          </Form.Item>
          <Form.Item name="role" label="ROLE / PHÂN QUYỀN" rules={[{ required: true }]}>
            <Select style={{ height: 42 }} options={roleSelectOptions} />
          </Form.Item>
          {selectedRoleEdit === 'operator' && (
            <Form.Item name="gate_id" label="CỔNG PHỤ TRÁCH">
              <Select placeholder="Chọn cổng..." allowClear style={{ height: 42 }}
                options={gates.map(g => ({ value: g.gate_code, label: `${g.gate_code} — ${g.name}` }))} />
            </Form.Item>
          )}
          <Form.Item name="is_active" label="TRẠNG THÁI">
            <Select style={{ height: 42 }} options={[
              { value: true,  label: <span style={{ color: 'var(--green)' }}>● Active — Đang hoạt động</span> },
              { value: false, label: <span style={{ color: 'var(--red)' }}>○ Inactive — Vô hiệu hóa</span> },
            ]} />
          </Form.Item>
          <PermPreview role={selectedRoleEdit} />
        </Form>
      </Modal>
    </div>
  )
}
 