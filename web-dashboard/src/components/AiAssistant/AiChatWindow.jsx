import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, List, Avatar, Spin, Tooltip, Select, message, Popover } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, ClearOutlined, SettingOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { aiApi, settingsApi } from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';

const AI_MODELS = [
  {
    label: 'Dòng Gemini Flash (Khuyên dùng)',
    options: [
      { label: 'Gemini 3 Flash (Thông minh nhất)', value: 'gemini-3-flash' },
      { label: 'Gemini 2.5 Flash (Cân bằng)', value: 'gemini-2.5-flash' },
    ],
  },
  {
    label: 'Dòng Gemini Lite (Tiết kiệm Token)',
    options: [
      { label: 'Gemini 3.1 Flash Lite', value: 'gemini-3.1-flash-lite' },
      { label: 'Gemini 2.5 Flash Lite', value: 'gemini-2.5-flash-lite' },
    ],
  },
  {
    label: 'Dòng Gemma (Thử nghiệm - Không tối ưu Tool)',
    options: [
      { label: 'Gemma 4 31B', value: 'gemma-4-31b' },
      { label: 'Gemma 4 26B', value: 'gemma-4-26b' },
      { label: 'Gemma 3 27B', value: 'gemma-3-27b' },
      { label: 'Gemma 3 12B', value: 'gemma-3-12b' },
      { label: 'Gemma 3 4B', value: 'gemma-3-4b' },
    ],
  },
];

const AiChatWindow = ({ onClose }) => {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('sen_chat_history');
    return saved ? JSON.parse(saved) : [
      { role: 'assistant', content: 'Xin chào! Tôi là trợ lý Tourism Gate AI. Tôi có thể giúp gì cho bạn hôm nay? (Tôi có quyền truy vấn doanh thu, lượt khách và tình trạng vé của hệ thống).' }
    ];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentModel, setCurrentModel] = useState('gemini-2.5-flash');
  const [isUpdatingModel, setIsUpdatingModel] = useState(false);
  
  const userRole = localStorage.getItem('role');
  const isAdmin = userRole === 'admin';

  const scrollRef = useRef(null);

  // Lấy model hiện tại khi mở
  useEffect(() => {
    if (isAdmin) {
      settingsApi.getAiModel().then(res => setCurrentModel(res.data.model_name)).catch(() => {});
    }
  }, [isAdmin]);

  // Lưu vào localStorage mỗi khi có tin nhắn mới
  useEffect(() => {
    localStorage.setItem('sen_chat_history', JSON.stringify(messages));
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const history = messages.slice(-5).map(m => ({
        role: m.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: m.content }]
      }));

      const response = await aiApi.chat(userMsg, history);
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.reply }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Có lỗi xảy ra. Có thể Token đã hết hạn hoặc Model hiện tại không khả dụng. Quản trị viên hãy thử đổi Model khác nhé!' }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    const defaultMsg = [{ role: 'assistant', content: 'Đã xóa lịch sữ chat. Tôi có thể giúp gì mới cho bạn?' }];
    setMessages(defaultMsg);
    localStorage.setItem('sen_chat_history', JSON.stringify(defaultMsg));
  };

  const handleUpdateModel = async (val) => {
    setIsUpdatingModel(true);
    try {
      await settingsApi.updateAiModel(val);
      setCurrentModel(val);
      message.success(`Đã đổi sang mô hình: ${val}`);
    } catch (error) {
      message.error("Không thể cập nhật mô hình. Vui lòng thử lại!");
    } finally {
      setIsUpdatingModel(false);
    }
  };

  const renderSettings = () => (
    <div style={{ padding: '8px', minWidth: '240px' }}>
      <p style={{ fontWeight: '600', marginBottom: '12px', fontSize: '14px', borderBottom: '1px solid #f0f0f0', paddingBottom: '8px' }}>
        Cấu hình Mô hình (Admin)
      </p>
      <div style={{ marginBottom: '12px' }}>
        <p style={{ fontSize: '12px', color: '#595959', marginBottom: '4px' }}>Chọn bộ não cho Sên:</p>
        <Select
          style={{ width: '100%' }}
          placeholder="Chọn mô hình..."
          value={currentModel}
          onChange={handleUpdateModel}
          loading={isUpdatingModel}
          options={AI_MODELS}
          getPopupContainer={trigger => trigger.parentElement}
          dropdownMatchSelectWidth={false}
          dropdownStyle={{ minWidth: 250 }}
        />
      </div>
      <p style={{ fontSize: '11px', color: '#8c8c8c', fontStyle: 'italic', backgroundColor: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
        💡 Thay đổi này sẽ được áp dụng cho cả App Mobile ngay lập tức.
      </p>
    </div>
  );

  return (
    <motion.div
      className="ai-chat-window"
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
    >
      <div className="ai-chat-header">
        <div className="ai-chat-title">
          <RobotOutlined style={{ marginRight: 8, color: '#1677ff' }} />
          <span>Tourism Gate AI Assistant</span>
        </div>
        <div className="ai-chat-actions">
          {isAdmin && (
            <Popover 
              content={renderSettings} 
              title="Cài đặt AI" 
              trigger="click" 
              placement="bottomRight"
              getPopupContainer={trigger => trigger.parentElement}
            >
               <Button type="text" icon={<SettingOutlined />} size="small" style={{ marginRight: 4 }} />
            </Popover>
          )}
          <Tooltip title="Xóa lịch sử">
             <Button type="text" icon={<ClearOutlined />} onClick={clearChat} size="small" />
          </Tooltip>
        </div>
      </div>

      <div className="ai-chat-messages" ref={scrollRef}>
        <List
          dataSource={messages}
          renderItem={(item) => (
            <div className={`chat-message-item ${item.role}`}>
              <Avatar 
                icon={item.role === 'assistant' ? <RobotOutlined /> : <UserOutlined />} 
                style={{ backgroundColor: item.role === 'assistant' ? '#1677ff' : '#87d068' }}
              />
              <div className="message-bubble">
                <ReactMarkdown>{item.content}</ReactMarkdown>
              </div>
            </div>
          )}
        />
        {loading && (
          <div className="chat-loading">
            <Spin size="small" /> AI đang suy nghĩ...
          </div>
        )}
      </div>

      <div className="ai-chat-input">
        <Input.TextArea
          placeholder="Hỏi về doanh thu, lượt khách..."
          autoSize={{ minRows: 1, maxRows: 4 }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <Button 
          type="primary" 
          icon={<SendOutlined />} 
          onClick={handleSend}
          loading={loading}
        />
      </div>
    </motion.div>
  );
};

export default AiChatWindow;
