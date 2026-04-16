import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import Login          from './pages/Login'
import Dashboard      from './pages/Dashboard'
import GateMonitor    from './pages/GateMonitor'
import Revenue        from './pages/Revenue'
import Visitors       from './pages/Visitors'
import Tickets        from './pages/Tickets'
import Reports        from './pages/Reports'
import AgeGroupAnalysis from './pages/AgeGroupAnalysis'
import UserManagement from './pages/UserManagement'
import AppLayout      from './components/AppLayout'
import useAuthStore   from './store/authStore'

function PrivateRoute({ children }) {
  const token = useAuthStore(s => s.token)
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <PrivateRoute><AppLayout /></PrivateRoute>
        }>
          <Route index                 element={<Dashboard />} />
          <Route path="gates"          element={<GateMonitor />} />
          <Route path="revenue"        element={<Revenue />} />
          <Route path="visitors"       element={<Visitors />} />
          <Route path="tickets"        element={<Tickets />} />
          <Route path="reports"        element={<Reports />} />
          <Route path="age-groups"     element={<AgeGroupAnalysis />} />
          <Route path="users"          element={<UserManagement />} />
        </Route>
      </Routes>
    </ConfigProvider>
  )
}
