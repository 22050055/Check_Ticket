import React from 'react'
import { DatePicker } from 'antd'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

export default function DateRangePicker({ value, onChange }) {
  return (
    <RangePicker
      value={value}
      onChange={onChange}
      format="DD/MM/YYYY"
      style={{ height: 38, borderRadius: 'var(--radius-sm)' }}
      allowClear={false}
      presets={[
        { label: 'Hôm nay',  value: [dayjs(), dayjs()] },
        { label: '7 ngày',   value: [dayjs().subtract(7,'day'), dayjs()] },
        { label: '30 ngày',  value: [dayjs().subtract(30,'day'), dayjs()] },
        { label: 'Tháng này',value: [dayjs().startOf('month'), dayjs()] },
      ]}
    />
  )
}
