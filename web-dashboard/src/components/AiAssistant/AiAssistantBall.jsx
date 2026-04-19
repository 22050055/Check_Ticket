import React, { useState } from 'react';
import { motion, useDragControls } from 'framer-motion';
import { RobotOutlined, CloseOutlined } from '@ant-design/icons';
import AiChatWindow from './AiChatWindow';
import './AiAssistant.css';

const AiAssistantBall = () => {
  const [isOpen, setIsOpen] = useState(false);
  const controls = useDragControls();

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      <motion.div
        className={`ai-assistant-ball ${isOpen ? 'open' : ''}`}
        drag
        dragControls={controls}
        dragMomentum={false}
        initial={{ x: 0, y: 0 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={(e) => {
          // Chỉ open nếu không phải đang drag
          if (e.defaultPrevented) return;
          toggleChat();
        }}
        style={{
          position: 'fixed',
          bottom: '30px',
          right: '30px',
          zIndex: 9999,
        }}
      >
        <div className="ai-ball-inner">
          {isOpen ? <CloseOutlined /> : <RobotOutlined />}
          {!isOpen && <div className="ai-ball-ping"></div>}
        </div>
      </motion.div>

      <div style={{ display: isOpen ? 'block' : 'none' }}>
        <AiChatWindow onClose={() => setIsOpen(false)} />
      </div>
    </>
  );
};

export default AiAssistantBall;
