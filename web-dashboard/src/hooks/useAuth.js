import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import { authApi } from '../services/api'

export default function useAuth() {
  const { token, role, fullName, login, logout } = useAuthStore()
  const navigate = useNavigate()

  const doLogin = useCallback(async (username, password) => {
    const { data } = await authApi.login({ username, password })
    login(data)
    navigate('/')
  }, [login, navigate])

  const doLogout = useCallback(() => {
    logout()
    navigate('/login')
  }, [logout, navigate])

  const isAdmin   = role === 'admin'
  const isManager = role === 'admin' || role === 'manager'

  return { token, role, fullName, isAdmin, isManager, doLogin, doLogout }
}
