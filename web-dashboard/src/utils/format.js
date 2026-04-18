/**
 * format.js — Các hàm định dạng dùng chung cho Dashboard
 */

/**
 * Định dạng tiền tệ VND (ví dụ: 150.000đ)
 */
export const fmtVnd = (value) => {
  if (value === undefined || value === null) return '0đ'
  return new Intl.NumberFormat('vi-VN').format(value) + 'đ'
}

/**
 * Định dạng số (ví dụ: 1.234)
 */
export const fmtNum = (value) => {
  if (value === undefined || value === null) return '0'
  return new Intl.NumberFormat('vi-VN').format(value)
}

/**
 * Định dạng ngày giờ (ví dụ: 18/04/2026 18:30)
 */
export const fmtDateTime = (isoString) => {
  if (!isoString) return '—'
  const d = new Date(isoString)
  return new Intl.NumberFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  }).format(d).replace(/\//g, '/').replace(',', '')
}

/**
 * Style chuẩn cho cột số trong Table
 */
export const NUM_COL_STYLE = {
  fontFamily: 'var(--font-mono)',
  textAlign: 'right',
  fontWeight: 500
}
