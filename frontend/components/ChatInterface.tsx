'use client';

import { useState, useRef, useEffect } from 'react';
import VoiceRecorder from './VoiceRecorder';

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
  messageId?: string;
  feedback?: 'positive' | 'negative';
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
  const [streamStage, setStreamStage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastStageAt = useRef(0);

  // 保证每个流式阶段至少展示 200ms，避免快路径下中间状态一闪即过
  const applyStage = async (stage: string) => {
    const now = Date.now();
    if (lastStageAt.current > 0 && now - lastStageAt.current < 200) {
      await new Promise(r => setTimeout(r, 200 - (now - lastStageAt.current)));
    }
    setStreamStage(stage);
    setCurrentThought(stage);
    lastStageAt.current = Date.now();
  };

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessageToAgent = async (userMessage: string) => {
    if (!userMessage.trim() || isStreaming) return;

    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsStreaming(true);
    lastStageAt.current = 0;
    await applyStage('正在识别意图...');
    setCurrentTools([]);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, session_id: getSessionId() }),
      });

      if (!response.ok || !response.body) {
        throw new Error('流式服务不可用');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finalContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';
        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;
          let data: any;
          try { data = JSON.parse(jsonStr); } catch { continue; }

          switch (data.type) {
            case 'thinking': {
              const intentName = data.intent?.name || '...';
              const conf = data.intent?.confidence != null ? ` (${(data.intent.confidence * 100).toFixed(0)}%)` : '';
              await applyStage(`识别意图: ${intentName}${conf}`);
              break;
            }
            case 'tool_call':
              await applyStage(`调用工具: ${data.tool}`);
              setCurrentTools([{ name: data.tool, status: 'running' }]);
              break;
            case 'tool_result':
              await applyStage('工具返回，正在生成回复...');
              setCurrentTools(prev => prev.map(t => t.status === 'running'
                ? { ...t, status: 'completed', result: `共 ${data.count} 条结果` }
                : t));
              break;
            case 'response':
              finalContent = data.content || '';
              break;
            case 'done':
              break;
            case 'error':
              throw new Error(data.message || '服务异常');
          }
        }
      }

      // 流式结束，解析并添加最终回复
      if (finalContent) {
        const thoughtMatch = finalContent.match(/【思考】(.+)/);
        const thought = thoughtMatch ? thoughtMatch[1] : '';
        const toolMatch = finalContent.match(/【行动】调用工具: (.+)/);
        const tools = toolMatch ? [{ name: toolMatch[1], status: 'completed' }] : [];
        const replyMatch = finalContent.match(/【回复】([\s\S]+)/);
        const reply = replyMatch ? replyMatch[1] : finalContent;

        setCurrentThought(thought);
        setCurrentTools(tools);
        setMessages(prev => [...prev, {
          role: 'agent',
          content: reply,
          thoughtChain: thought,
          toolCalls: tools,
          messageId: `msg_${Date.now()}`,
        }]);
      }
    } catch (error: any) {
      // HMR/页面导航会中断流式请求，属于 dev 模式正常现象，不显示错误
      const isAbort = error?.name === 'AbortError' || /abort|interrupt/i.test(error?.message || '');
      if (isAbort) {
        console.warn('流式请求被中断（通常是热重载或导航引起）');
      } else {
        console.error('流式调用失败:', error);
        setMessages(prev => [...prev, {
          role: 'agent',
          content: '抱歉，服务暂时不可用。请稍后再试。',
        }]);
      }
    }

    setStreamStage('');
    setIsStreaming(false);
  };

  // 发送消息
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    
    const userMessage = input.trim();
    setInput('');
    await sendMessageToAgent(userMessage);
  };

  // 处理语音输入
  const handleVoiceInput = async (text: string) => {
    if (!text.trim()) return;
    await sendMessageToAgent(text);
  };
  
  const handleFeedback = (msgIdx: number, type: 'positive' | 'negative') => {
    setMessages(prev => {
      const newMessages = [...prev];
      const msg = newMessages[msgIdx];
      if (msg.role === 'agent' && !msg.feedback) {
        newMessages[msgIdx] = { ...msg, feedback: type };
        fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message_id: msg.messageId || `msg_${msgIdx}`,
            feedback_type: type,
            session_id: getSessionId(),
          }),
        }).catch(() => {});
      }
      return newMessages;
    });
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
              
              {/* 反馈按钮 */}
              {msg.role === 'agent' && !msg.feedback && (
                <div className="flex gap-2 mt-3 pt-3 border-t border-gray-200">
                  <button
                    onClick={() => handleFeedback(idx, 'positive')}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-green-50 text-green-600 hover:bg-green-100 text-sm transition-colors"
                  >
                    <span>👍</span>
                    <span>有帮助</span>
                  </button>
                  <button
                    onClick={() => handleFeedback(idx, 'negative')}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-red-50 text-red-600 hover:bg-red-100 text-sm transition-colors"
                  >
                    <span>👎</span>
                    <span>无帮助</span>
                  </button>
                </div>
              )}
              {msg.role === 'agent' && msg.feedback === 'positive' && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <span className="text-sm text-green-600">👍 感谢您的反馈！</span>
                </div>
              )}
              {msg.role === 'agent' && msg.feedback === 'negative' && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <span className="text-sm text-red-600">👎 抱歉没能帮到您，我会继续努力！</span>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {/* 流式输出指示 */}
        {isStreaming && (
          <div className="flex justify-start">
            <div className="message-bubble message-agent">
              <div className="flex items-center gap-2">
                <span className="animate-pulse">●</span>
                <span className="streaming-text">{streamStage || '正在思考'}</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* 输入区域 */}
      <div className="p-4 border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex gap-2 items-center">
          <div className="flex-1 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入消息，或点击麦克风说话..."
              className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              disabled={isStreaming}
            />
            <VoiceRecorder 
              onVoiceInput={handleVoiceInput} 
              disabled={isStreaming} 
            />
          </div>
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