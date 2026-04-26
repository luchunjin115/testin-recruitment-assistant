import React, { useState, useRef, useEffect } from 'react';
import { Drawer, Input, Button, Tag, Spin } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import type { ChatMessage } from '../types';
import { chatWithCopilot } from '../api';

const { TextArea } = Input;

const QUICK_QUESTIONS = [
  '今天有多少新候选人？',
  '哪些候选人需要跟进？',
  '招聘漏斗情况如何？',
  '有什么优化建议？',
];

const CopilotChat: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: '您好！我是Testin云测招聘助手，可以帮您查询候选人数据、分析招聘进展、提供跟进建议。请问有什么需要帮助的？' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text?: string) => {
    const content = text || input.trim();
    if (!content || loading) return;

    const userMsg: ChatMessage = { role: 'user', content };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const { reply } = await chatWithCopilot(newMessages.filter(m => m.role !== 'assistant' || newMessages.indexOf(m) > 0));
      setMessages([...newMessages, { role: 'assistant', content: reply }]);
    } catch {
      setMessages([...newMessages, { role: 'assistant', content: '抱歉，请求失败，请稍后重试。' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Drawer
      title={<span><RobotOutlined /> HR Copilot - Testin云测招聘助手</span>}
      open={open}
      onClose={onClose}
      width={420}
      styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', height: '100%' } }}
    >
      <div ref={listRef} style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: 12,
          }}>
            <div style={{
              maxWidth: '80%', padding: '8px 12px', borderRadius: 12,
              background: msg.role === 'user' ? '#1677ff' : '#f0f2f5',
              color: msg.role === 'user' ? '#fff' : '#333',
              fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap',
            }}>
              <div style={{ marginBottom: 2 }}>
                {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                <span style={{ marginLeft: 4, fontSize: 12, opacity: 0.7 }}>
                  {msg.role === 'user' ? 'HR' : 'AI助手'}
                </span>
              </div>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ textAlign: 'center', padding: 8 }}>
            <Spin size="small" /> <span style={{ color: '#999', marginLeft: 8 }}>AI正在思考...</span>
          </div>
        )}
      </div>

      <div style={{ padding: '8px 16px', borderTop: '1px solid #f0f0f0' }}>
        <div style={{ marginBottom: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {QUICK_QUESTIONS.map(q => (
            <Tag key={q} color="blue" style={{ cursor: 'pointer', fontSize: 12 }} onClick={() => handleSend(q)}>
              {q}
            </Tag>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <TextArea
            value={input}
            onChange={e => setInput(e.target.value)}
            onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="输入问题，按回车发送..."
            autoSize={{ minRows: 1, maxRows: 3 }}
            style={{ flex: 1 }}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={() => handleSend()} loading={loading} />
        </div>
      </div>
    </Drawer>
  );
};

export default CopilotChat;
