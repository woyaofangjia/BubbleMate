'use client';

import { useState, useRef, useEffect, Suspense } from 'react';
import dynamic from 'next/dynamic';
import ChatInterface from '@/components/ChatInterface';
import Header from '@/components/Header';

const ThoughtChainPanel = dynamic(
  () => import('@/components/ThoughtChainPanel'),
  { ssr: false, loading: () => <div className="bg-gray-800 rounded-lg h-48 animate-pulse" /> }
);

const ToolVisualization = dynamic(
  () => import('@/components/ToolVisualization'),
  { ssr: false, loading: () => <div className="bg-gray-800 rounded-lg h-48 animate-pulse" /> }
);

export default function Home() {
  const [messages, setMessages] = useState<Array<{
    role: 'user' | 'agent';
    content: string;
    thoughtChain?: string;
    toolCalls?: Array<{ name: string; status: string; result?: string }>;
  }>>([
    {
      role: 'agent',
      content: '您好，我是BubbleMate奶茶店智能客服！请问有什么可以帮助您的？您可以咨询菜单推荐、订单状态、门店信息等问题。',
    },
  ]);

  const [currentThought, setCurrentThought] = useState<string>('');
  const [currentTools, setCurrentTools] = useState<Array<{ name: string; status: string }>>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  return (
    <main className="min-h-screen flex flex-col">
      {/* 头部 */}
      <Header />
      
      {/* 主内容区 */}
      <div className="flex-1 flex gap-4 p-4 max-w-7xl mx-auto w-full">
        {/* 左侧：聊天界面 */}
        <div className="flex-1 flex flex-col">
          <ChatInterface 
            messages={messages}
            setMessages={setMessages}
            setCurrentThought={setCurrentThought}
            setCurrentTools={setCurrentTools}
            setIsStreaming={setIsStreaming}
            isStreaming={isStreaming}
          />
        </div>
        
        {/* 右侧：可视化面板 */}
        <div className="w-80 flex flex-col gap-4">
          {/* 思考链面板 */}
          <ThoughtChainPanel 
            thought={currentThought}
            isStreaming={isStreaming}
          />
          
          {/* 工具调用面板 */}
          <ToolVisualization 
            tools={currentTools}
            isStreaming={isStreaming}
          />
        </div>
      </div>
    </main>
  );
}