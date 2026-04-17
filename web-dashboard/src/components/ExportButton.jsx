import React, { useState } from 'react'
import { Button, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { reportApi } from '../services/api'

export default function ExportButton({ dateFrom, dateTo }) {
  const [loading, setLoading] = useState(false)

  const handleExport = async () => {
    setLoading(true)
    try {
      const { data } = await reportApi.exportCsv({
        date_from: dateFrom,
        date_to:   dateTo,
      })
      const url  = URL.createObjectURL(new Blob([data], { type: 'text/csv' }))
      const link = document.createElement('a')
      link.href     = url
      link.download = `gate_events_${dateFrom?.slice(0,10)}_${dateTo?.slice(0,10)}.csv`
      link.click()
      URL.revokeObjectURL(url)
      message.success('Xuất CSV thành công')
    } catch {
      message.error('Xuất CSV thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Button icon={<DownloadOutlined />} loading={loading} onClick={handleExport}>
      Xuất CSV
    </Button>
  )
}
 