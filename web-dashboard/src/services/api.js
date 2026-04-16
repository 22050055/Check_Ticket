/**
 * api.js — Axios instance với JWT header tự động
 * Base URL: Linh hoạt giữa local proxy và production URL
 */
import axios from 'axios'

const api = axios.create({ 
  baseURL: import.meta.env.VITE_API_URL || '/api', 
  timeout: 15000 
})

// Tự động gắn Authorization header
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// Tự redirect về /login nếu 401
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.clear()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────
export const authApi = {
  login:   (data)  => api.post('/auth/login',   data),
  refresh: (token) => api.post('/auth/refresh', { refresh_token: token }),
  me:      ()      => api.get('/auth/me'),
}

// ── Tickets ───────────────────────────────────────────────────
export const ticketApi = {
  issue:   (data)      => api.post('/tickets',             data),
  get:     (id)        => api.get(`/tickets/${id}`),
  revoke:  (id, data)  => api.put(`/tickets/${id}/revoke`, data),
  enroll:  (id, data)  => api.post(`/tickets/${id}/enroll-face`, data),
  downloadQr: (id)     => api.get(`/tickets/${id}/qr.png`, { responseType: 'blob' }),
}

// ── Gates ─────────────────────────────────────────────────────
export const gateApi = {
  list:       ()     => api.get('/gates'),
  get:        (id)   => api.get(`/gates/${id}`),
  create:     (data) => api.post('/gates', data),
  deactivate: (id)   => api.put(`/gates/${id}/deactivate`),
  events:     (id, limit = 50) => api.get(`/gates/${id}/events`, { params: { limit } }),
}

// ── Reports ───────────────────────────────────────────────────
export const reportApi = {
  revenue:    (params) => api.get('/reports/revenue',              { params }),
  visitors:   (params) => api.get('/reports/visitors',             { params }),
  errors:     (params) => api.get('/reports/errors',               { params }),
  realtime:   ()       => api.get('/reports/realtime'),
  exportCsv:  (params) => api.get('/reports/export/gate-events',   { params, responseType: 'blob' }),
}

export default api
