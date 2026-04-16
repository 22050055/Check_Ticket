import { create } from 'zustand'

const useAuthStore = create((set) => ({
  token:    localStorage.getItem('token')    || null,
  role:     localStorage.getItem('role')     || null,
  fullName: localStorage.getItem('fullName') || null,
  gateId:   localStorage.getItem('gateId')  || null,

  login: ({ access_token, role, full_name, gate_id }) => {
    localStorage.setItem('token',    access_token)
    localStorage.setItem('role',     role)
    localStorage.setItem('fullName', full_name)
    localStorage.setItem('gateId',   gate_id || '')
    set({ token: access_token, role, fullName: full_name, gateId: gate_id })
  },

  logout: () => {
    ;['token','role','fullName','gateId'].forEach(k => localStorage.removeItem(k))
    set({ token: null, role: null, fullName: null, gateId: null })
  },
}))

export default useAuthStore
