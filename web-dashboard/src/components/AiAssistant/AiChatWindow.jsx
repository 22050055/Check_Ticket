import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, List, Avatar, Spin, Tooltip } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, ClearOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { aiApi } from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';

const AiChatWindow = ({ onClose }) => {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('sen_chat_history');
    return saved ? JSON.parse(saved) : [
      { role: 'assistant', content: 'Xin chào! Tôi là trợ lý Tourism Gate AI. Tôi có thể giúp gì cho bạn hôm nay? (Tôi có quyền truy vấn doanh thu, lượt khách và tình trạng vé của hệ thống).' }
    ];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

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
      // TIẾT KIỆM TOKEN: Chỉ lấy 5 tin nhắn gần nhất để làm ngữ cảnh
      const history = messages.slice(-5).map(m => ({
        role: m.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: m.content }]
      }));

      const response = await aiApi.chat(userMsg, history);
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.reply }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Có lỗi xảy ra khi kết nối với AI. Vui lòng kiểm tra API Key hoặc kết nối mạng.' }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    const defaultMsg = [{ role: 'assistant', content: 'Đã xóa lịch sữ chat. Tôi có thể giúp gì mới cho bạn?' }];
    setMessages(defaultMsg);
    localStorage.setItem('sen_chat_history', JSON.stringify(defaultMsg));
  };

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
