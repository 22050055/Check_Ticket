/**
 * api.js — Axios instance với JWT header tự động
 * Base URL: Linh hoạt giữa local proxy và production URL
 */
import axios from 'axios'

const getBaseURL = () => {
  const url = import.meta.env.VITE_API_URL || ''
  if (url && !url.endsWith('/api')) {
    return `${url}/api`
  }
  return url || '/api'
}

const api = axios.create({ 
  baseURL: getBaseURL(), 
  timeout: 60000 // Tăng lên 60 giây để đợi AI phản hồi
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
  issue:      (data)      => api.post('/tickets',             data),
  get:        (id)        => api.get(`/tickets/${id}`),
  search:     (params)    => api.get('/tickets/search',       { params }),
  revoke:     (id, data)  => api.put(`/tickets/${id}/revoke`, data),
  enroll:     (id, data)  => api.post(`/tickets/${id}/enroll-face`, data),
  downloadQr: (id)        => api.get(`/tickets/${id}/qr.png`, { responseType: 'blob' }),
}

// ── Reviews ───────────────────────────────────────────────────
export const reviewApi = {
  list:     () => api.get('/reports/reviews'),
  getStats: () => api.get('/reports/review-stats'),
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
  auditLogs:  (params) => api.get('/reports/audit-logs',           { params }),
}

// ── AI Assistant ─────────────────────────────────────────────
export const aiApi = {
  chat: (message, history) => api.post('/ai/chat', { message, history }),
}

// ── System Settings ──────────────────────────────────────────
export const settingsApi = {
  getAiModel: () => api.get('/settings/ai-model'),
  updateAiModel: (modelName) => api.post('/settings/ai-model', { model_name: modelName }),
}

export default api
 