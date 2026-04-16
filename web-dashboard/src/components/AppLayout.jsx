import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout } from 'antd'
import useAuth from '../hooks/useAuth'

const { Sider, Content } = Layout

// role-based menu: null = tất cả, ['admin'] = chỉ admin, v.v.
const MENU = [
  { path: '/',         icon: '⬡', label: 'Tổng quan',        roles: null },
  { path: '/gates',    icon: '◈', label: 'Giám sát cổng',    roles: null },
  { path: '/revenue',  icon: '◎', label: 'Doanh thu',        roles: ['admin','manager','cashier'] },
  { path: '/visitors', icon: '◉', label: 'Lượt khách',       roles: ['admin','manager','operator'] },
  { path: '/tickets',  icon: '◇', label: 'Quản lý vé',       roles: ['admin','manager'] },
  { path: '/reports',  icon: '◫', label: 'Báo cáo / Export', roles: ['admin','manager'] },
  { path: '/users',    icon: '◎', label: 'Nhân viên',        roles: ['admin','manager'] },
  { path: '/customers', icon: '👥', label: 'Khách hàng',      roles: ['admin','manager'] },
]

const ROLE_LABEL = { admin:'Admin', manager:'Manager', operator:'Operator', cashier:'Cashier' }
const ROLE_COLOR = { admin:'var(--red)', manager:'var(--cyan)', operator:'var(--green)', cashier:'var(--amber)' }

export default function AppLayout() {
  const { fullName, role, doLogout } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const active = location.pathname

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        collapsedWidth={60}
        collapsed={collapsed}
        style={{
          position: 'fixed', height: '100vh', left: 0, top: 0, zIndex: 100,
          display: 'flex', flexDirection: 'column',
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-dim)',
        }}
      >
        {/* Logo */}
        <div style={{
          padding: collapsed ? '20px 0' : '20px 18px',
          borderBottom: '1px solid var(--border-dim)',
          display: 'flex', alignItems: 'center', gap: 10,
          justifyContent: collapsed ? 'center' : 'flex-start',
          cursor: 'pointer',
        }} onClick={() => setCollapsed(!collapsed)}>
          <span style={{ fontSize: 20 }}>🏖</span>
          {!collapsed && (
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 14, color: 'var(--text-1)', lineHeight: 1.2 }}>
                Tourism
              </div>
              <div style={{ color: 'var(--cyan)', fontSize: 10, letterSpacing: '0.2em', fontFamily: 'var(--font-mono)' }}>
                CONTROL CENTER
              </div>
            </div>
          )}
        </div>

        {/* Nav items */}
        <div style={{ flex: 1, padding: '12px 0', overflowY: 'auto' }}>
          {MENU.filter(item => !item.roles || item.roles.includes(role)).map(item => {
            const isActive = active === item.path || (item.path !== '/' && active.startsWith(item.path))
            return (
              <div
                key={item.path}
                onClick={() => navigate(item.path)}
                style={{
                  display: 'flex', alignItems: 'center',
                  gap: 10,
                  padding: collapsed ? '12px 0' : '11px 16px',
                  margin: '1px 8px',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  transition: 'all 0.15s',
                  background: isActive ? 'var(--cyan-dim)' : 'transparent',
                  borderLeft: isActive ? `2px solid var(--cyan)` : '2px solid transparent',
                  color: isActive ? 'var(--cyan)' : 'var(--text-2)',
                }}
                onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background='var(--bg-hover)'; e.currentTarget.style.color='var(--text-1)' } }}
                onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background='transparent'; e.currentTarget.style.color='var(--text-2)' } }}
              >
                <span style={{ fontSize: 16, minWidth: 18, textAlign: 'center' }}>{item.icon}</span>
                {!collapsed && (
                  <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                    {item.label}
                  </span>
                )}
              </div>
            )
          })}
        </div>

        {/* User section */}
        <div style={{
          padding: collapsed ? '12px 0' : '12px 14px',
          borderTop: '1px solid var(--border-dim)',
        }}>
          {!collapsed && (
            <div style={{ marginBottom: 10 }}>
              <div style={{
                fontSize: 13, color: 'var(--text-1)', fontFamily: 'var(--font-mono)',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                marginBottom: 3,
              }}>{fullName}</div>
              <span style={{
                fontSize: 10, letterSpacing: '0.12em',
                color: ROLE_COLOR[role] || 'var(--text-2)',
                fontFamily: 'var(--font-mono)',
              }}>
                {(ROLE_LABEL[role] || role || '').toUpperCase()}
              </span>
            </div>
          )}
          <div
            onClick={doLogout}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: collapsed ? 'center' : 'flex-start',
              gap: 8, padding: '8px', borderRadius: 'var(--radius-sm)',
              cursor: 'pointer', color: 'var(--text-2)', fontSize: 12,
              fontFamily: 'var(--font-mono)',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color='var(--red)'; e.currentTarget.style.background='var(--red-dim)' }}
            onMouseLeave={e => { e.currentTarget.style.color='var(--text-2)'; e.currentTarget.style.background='transparent' }}
          >
            <span>⏻</span>
            {!collapsed && <span>Đăng xuất</span>}
          </div>
        </div>
      </Sider>

      {/* Main content */}
      <Layout style={{ marginLeft: collapsed ? 60 : 220, transition: 'margin 0.2s', background: 'var(--bg-base)' }}>
        {/* Top bar */}
        <div style={{
          height: 52, background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-dim)',
          display: 'flex', alignItems: 'center',
          padding: '0 24px', position: 'sticky', top: 0, zIndex: 50,
          justifyContent: 'space-between',
        }}>
          <div style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
            {MENU.find(m => m.path === active || (m.path !== '/' && active.startsWith(m.path)))?.label || 'Dashboard'}
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 12px',
            background: 'var(--green-dim)',
            border: '1px solid rgba(0,255,136,0.2)',
            borderRadius: 'var(--radius-sm)',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', display: 'inline-block' }}/>
            <span style={{ color: 'var(--green)', fontSize: 11, fontFamily: 'var(--font-mono)', letterSpacing: '0.1em' }}>
              LIVE
            </span>
          </div>
        </div>

        <Content style={{ padding: 24, minHeight: 'calc(100vh - 52px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
