'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import useSWR from 'swr';
import NavBar from '@/components/NavBar';
import { useRole } from '@/context/RoleContext';
import { fetcher } from '@/lib/swr';

interface ContextMessage {
  user: string;
  agent: string;
}

interface Context {
  history: ContextMessage[];
  preferences: Record<string, string>;
}

interface AdminContext {
  session_id: string;
  user_id: string;
  preferences: Record<string, string>;
  complaints: { complaint: string; severity: string; category: string; time: number }[];
  context: Context;
  is_taken_over: boolean;
}

export default function AgentDashboardPage() {
  const router = useRouter();
  const { role, agentVerified, adminVerified } = useRole();
  
  useEffect(() => {
    if (role !== 'agent' && role !== 'admin') {
      router.push('/landing');
    }
  }, [role, router]);

  const [sessionId, setSessionId] = useState('');
  const [reply, setReply] = useState('');

  const { data: context, mutate: mutateContext, error } = useSWR<AdminContext>(
    sessionId.trim() ? `/api/admin/context/${sessionId.trim()}` : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  const handleTakeover = () => {
    if (!sessionId.trim()) return;
    fetch(`/api/admin/takeover/${sessionId.trim()}`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        mutateContext();
      });
  };

  const handleRelease = () => {
    if (!sessionId.trim()) return;
    fetch(`/api/admin/release/${sessionId.trim()}`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        mutateContext();
      });
  };

  const handleReply = () => {
    if (!sessionId.trim() || !reply.trim()) return;
    fetch(`/api/admin/reply/${sessionId.trim()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: reply }),
    }).then(() => {
      setReply('');
      mutateContext();
    });
  };

  return (
    <div className="min-h-screen bg-gray-100 pt-16">
      <NavBar />

      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl p-4 border border-gray-200 mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
              placeholder="输入 session_id 查询..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {!context ? (
          <div className="bg-white rounded-xl p-8 border border-gray-200 text-center text-gray-500">
            输入 session_id 查看用户会话详情
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl p-4 border border-gray-200 mb-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold">💬 对话历史</h2>
                  <div className="flex gap-2">
                    {context.is_taken_over ? (
                      <button
                        onClick={handleRelease}
                        className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
                      >
                        释放会话
                      </button>
                    ) : (
                      <button
                        onClick={handleTakeover}
                        className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        接管会话
                      </button>
                    )}
                  </div>
                </div>
                <div className="border border-gray-100 rounded-lg p-4 h-80 overflow-y-auto space-y-4">
                  {context.context?.history?.map((msg, idx) => (
                    <div key={idx} className="space-y-2">
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <div className="text-xs text-blue-600 mb-1">用户</div>
                        <div className="text-gray-800">{msg.user}</div>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-xs text-gray-600 mb-1">Agent</div>
                        <div className="text-gray-800">{msg.agent}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {context.is_taken_over && (
                <div className="bg-white rounded-xl p-4 border border-red-200">
                  <div className="text-sm text-red-600 mb-3">⚠️ 会话已接管，以下回复将发送给用户</div>
                  <div className="flex gap-4">
                    <input
                      type="text"
                      value={reply}
                      onChange={(e) => setReply(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleReply()}
                      placeholder="输入回复消息..."
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                    />
                    <button
                      onClick={handleReply}
                      className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                    >
                      发送
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-6">
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h2 className="text-lg font-semibold mb-4">👤 用户信息</h2>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-gray-500">Session ID</div>
                    <div className="font-medium text-gray-800">{context.session_id}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">User ID</div>
                    <div className="font-medium text-gray-800">{context.user_id}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">接管状态</div>
                    <div className={`font-medium ${context.is_taken_over ? 'text-red-600' : 'text-green-600'}`}>
                      {context.is_taken_over ? '已接管' : '正常'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h2 className="text-lg font-semibold mb-4">🍵 用户偏好</h2>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-amber-50 p-3 rounded-lg">
                    <div className="text-xs text-gray-500">糖度</div>
                    <div className="font-medium">{context.preferences?.sugar || '未设置'}</div>
                  </div>
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <div className="text-xs text-gray-500">冰量</div>
                    <div className="font-medium">{context.preferences?.ice || '未设置'}</div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h2 className="text-lg font-semibold mb-4">📝 投诉记录</h2>
                <div className="space-y-3">
                  {context.complaints?.slice(0, 5).map((c, idx) => (
                    <div key={idx} className="border border-gray-100 rounded-lg p-3">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm font-medium">{c.category}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${c.severity === '严重' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>
                          {c.severity}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">{c.complaint}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}