import React, { useState } from 'react';
import { Button, message } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { ticketApi } from '../services/api';

export default function QrDownloadButton({ ticketId }) {
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      const response = await ticketApi.downloadQr(ticketId);
      
      // Tạo URL từ Blob object
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'image/png' }));
      const link = document.createElement('a');
      link.href = url;
      
      // Lấy tên tệp từ header Content-Disposition nếu có thể, hoặc dùng mặc định
      const contentDisposition = response.headers['content-disposition'];
      let filename = `ticket-${ticketId}.png`;
      if (contentDisposition) {
        const matches = /filename="([^"]+)"/.exec(contentDisposition);
        if (matches && matches[1]) {
          filename = matches[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      
      // Dọn dẹp
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      message.success('Đã tải ảnh QR thành công');
    } catch (error) {
      console.error(error);
      message.error('Lỗi khi tải ảnh QR: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button 
      type="dashed" 
      icon={<DownloadOutlined />} 
      size="small" 
      onClick={handleDownload}
      loading={loading}
      style={{
        fontSize: 11,
        fontFamily: 'var(--font-mono)',
        borderRadius: 4,
      }}
    >
      TẢI QR
    </Button>
  );
}
