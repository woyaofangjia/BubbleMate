'use client';

import { useState, useRef, useEffect } from 'react';

const getSessionId = () => {
  let sessionId = localStorage.getItem('bubblemate_session_id');
  if (!sessionId) {
    sessionId = `session_${Date.now()}`;
    localStorage.setItem('bubblemate_session_id', sessionId);
  }
  return sessionId;
};

interface Message {
  role: 'user' | 'agent';
  content: string;
  thoughtChain?: string;
  toolCalls?: Array<{ name: string; status: string; result?: string }>;
}

interface ChatInterfaceProps {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setCurrentThought: React.Dispatch<React.SetStateAction<string>>;
  setCurrentTools: React.Dispatch<React.SetStateAction<Array<{ name: string; status: string }>>>;
  setIsStreaming: React.Dispatch<React.SetStateAction<boolean>>;
  isStreaming: boolean;
}

export default function ChatInterface({
  messages,
  setMessages,
  setCurrentThought,
  setCurrentTools,
  setIsStreaming,
  isStreaming,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // 发送消息
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    
    const userMessage = input.trim();
    setInput('');
    
    // 添加用户消息
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsStreaming(true);
    
    // 调用API
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, session_id: getSessionId() }),
      });
      
      const data = await response.json();
      
      // 解析回复，提取思考链和工具调用
      const agentMessage = data.response;
      
      // 提取思考链
      const thoughtMatch = agentMessage.match(/【思考】(.+)/);
      const thought = thoughtMatch ? thoughtMatch[1] : '';
      
      // 提取工具调用
      const toolMatch = agentMessage.match(/【行动】调用工具: (.+)/);
      const tools = toolMatch ? [{ name: toolMatch[1], status: 'completed' }] : [];
      
      // 更新思考链和工具面板
      setCurrentThought(thought);
      setCurrentTools(tools);
      
      // 提取最终回复
      const replyMatch = agentMessage.match(/【回复】(.+)/s);
      const reply = replyMatch ? replyMatch[1] : agentMessage;
      
      // 添加Agent回复
      setMessages(prev => [...prev, {
        role: 'agent',
        content: reply,
        thoughtChain: thought,
        toolCalls: tools,
      }]);
    } catch (error) {
      console.error('API调用失败:', error);
      setMessages(prev => [...prev, {
        role: 'agent',
        content: '抱歉，服务暂时不可用。请稍后再试。',
      }]);
    }
    
    setIsStreaming(false);
  };
  
  return (
    <div className="flex flex-col h-full bg-white rounded-xl shadow-sm border border-gray-200">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`message-bubble ${msg.role === 'user' ? 'message-user' : 'message-agent'}`}>
              {/* Agent消息显示思考链 */}
              {msg.role === 'agent' && msg.thoughtChain && (
                <div className="thought-chain mb-2 text-sm text-gray-600">
                  <span className="text-primary-500 font-medium">💭 思考: </span>
                  {msg.thoughtChain}
                </div>
              )}
              
              {/* 工具调用 */}
              {msg.role === 'agent' && msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="tool-card mb-2">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-primary-500">🔧</span>
                    <span className="font-medium">{msg.toolCalls[0].name}</span>
                    <span className="text-green-500">✓</span>
                  </div>
                </div>
              )}
              
              {/* 消息内容 */}
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        
        {/* 流式输出指示 */}
        {isStreaming && (
          <div className="flex justify-start">
            <div className="message-bubble message-agent">
              <div className="flex items-center gap-2">
                <span className="animate-pulse">●</span>
                <span className="streaming-text">正在思考</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* 输入区域 */}
      <div className="p-4 border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入消息，例如：你们有什么招牌推荐？"
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            发送
          </button>
        </form>
        
        {/* 快捷提示 */}
        <div className="mt-2 flex gap-2 text-xs">
          <button 
            onClick={() => setInput('你们有什么招牌推荐？')}
            className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
          >
            推荐
          </button>
          <button 
            onClick={() => setInput('订单12345什么时候能送到？')}
            className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
          >
            查订单
          </button>
          <button 
            onClick={() => setInput('附近有门店吗？')}
            className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
          >
            门店
          </button>
          <button 
            onClick={() => setInput('太甜了，喝不下去')}
            className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
          >
            投诉
          </button>
        </div>
      </div>
    </div>
  );
}