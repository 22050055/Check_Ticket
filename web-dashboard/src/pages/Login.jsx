import React, { useState } from 'react'
import { Form, Input, Button, Alert } from 'antd'
import useAuth from '../hooks/useAuth'

export default function Login() {
  const { doLogin } = useAuth()
  const [error, setError]     = useState(null)
  const [loading, setLoading] = useState(false)

  const onFinish = async ({ username, password }) => {
    setError(null); setLoading(true)
    try   { await doLogin(username, password) }
    catch { setError('Sai username hoặc mật khẩu') }
    finally { setLoading(false) }
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg-base)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Grid pattern */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: 'linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px)',
        backgroundSize: '48px 48px',
      }}/>
      {/* Glow */}
      <div style={{
        position: 'absolute', top: '15%', left: '50%', transform: 'translateX(-50%)',
        width: 700, height: 400, pointerEvents: 'none',
        background: 'radial-gradient(ellipse, rgba(0,229,255,0.05) 0%, transparent 65%)',
      }}/>

      <div className="fade-in" style={{
        width: 420, padding: '48px 40px', position: 'relative', zIndex: 1,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-dim)',
        borderRadius: 'var(--radius-lg)',
      }}>
        {/* Brand */}
        <div style={{ marginBottom: 36 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 20,
            background: 'var(--cyan-dim)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)', padding: '5px 12px',
          }}>
            <span>🏖</span>
            <span style={{ color: 'var(--cyan)', fontSize: 11, letterSpacing: '0.2em' }}>TOURISM GATE</span>
          </div>
          <h1 style={{
            fontFamily: 'var(--font-display)', fontSize: 32, fontWeight: 800,
            color: 'var(--text-1)', marginBottom: 6, lineHeight: 1.1,
          }}>Control Center</h1>
          <p style={{ color: 'var(--text-2)', fontSize: 13 }}>
            Phân tích vận hành &amp; Dashboard báo cáo
          </p>
        </div>

        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="username" label="USERNAME" rules={[{ required: true, message: '' }]} style={{ marginBottom: 14 }}>
            <Input placeholder="Nhập username" size="large" style={{ height: 46, borderRadius: 'var(--radius-sm)' }}/>
          </Form.Item>
          <Form.Item name="password" label="PASSWORD" rules={[{ required: true, message: '' }]} style={{ marginBottom: 20 }}>
            <Input.Password placeholder="••••••••" size="large" style={{ height: 46, borderRadius: 'var(--radius-sm)' }}/>
          </Form.Item>
          {error && (
            <div style={{
              marginBottom: 14, padding: '10px 14px', fontSize: 13,
              background: 'var(--red-dim)', border: '1px solid rgba(255,51,102,0.25)',
              borderRadius: 'var(--radius-sm)', color: 'var(--red)',
            }}>{error}</div>
          )}
          <Button htmlType="submit" loading={loading} block size="large" style={{
            height: 50, fontWeight: 600, fontSize: 13, letterSpacing: '0.12em',
            borderRadius: 'var(--radius-sm)',
          }}>
            ĐĂNG NHẬP  →
          </Button>
        </Form>

        <div style={{
          marginTop: 28, paddingTop: 20, borderTop: '1px solid var(--border-dim)',
          display: 'flex', justifyContent: 'space-between',
          color: 'var(--text-3)', fontSize: 11,
        }}>
          <span>v1.0.0</span><span>Read-only Dashboard</span>
        </div>
      </div>
    </div>
  )
}
 