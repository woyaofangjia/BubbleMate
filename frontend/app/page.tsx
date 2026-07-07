'use client';

import { useState, useRef, useEffect, Suspense } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import ChatInterface from '@/components/ChatInterface';
import NavBar from '@/components/NavBar';
import { useRole } from '@/context/RoleContext';

const ThoughtChainPanel = dynamic(
  () => import('@/components/ThoughtChainPanel'),
  { ssr: false, loading: () => <div className="bg-gray-800 rounded-lg h-48 animate-pulse" /> }
);

const ToolVisualization = dynamic(
  () => import('@/components/ToolVisualization'),
  { ssr: false, loading: () => <div className="bg-gray-800 rounded-lg h-48 animate-pulse" /> }
);

export default function Home() {
  const { role } = useRole();
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
    <main className="min-h-screen flex flex-col pt-16">
      <NavBar />

      <div className="flex-1 flex gap-4 p-4 max-w-7xl mx-auto w-full">
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
        
        <div className="w-80 flex flex-col gap-4">
          <ThoughtChainPanel 
            thought={currentThought}
            isStreaming={isStreaming}
          />
          
          <ToolVisualization 
            tools={currentTools}
            isStreaming={isStreaming}
          />
        </div>
      </div>

      <footer className="bg-gray-50 border-t border-gray-100 py-3 px-4">
        <div className="max-w-7xl mx-auto flex items-center justify-center gap-4 text-sm text-gray-500">
          <span>当前角色：👤 {role === 'customer' ? '顾客' : role === 'admin' ? '管理员' : '客服'}</span>
          <span className="text-gray-300">|</span>
          <Link href="/landing" className="text-blue-500 hover:text-blue-600">切换角色</Link>
        </div>
      </footer>
    </main>
  );
}