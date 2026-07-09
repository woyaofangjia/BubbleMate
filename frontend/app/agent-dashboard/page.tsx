'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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

interface Complaint {
  id: number;
  user_id: string;
  session_id: string | null;
  complaint_type: string;
  description: string;
  status: string;
  knowledge_id: number | null;
  candidate_id: number | null;
  created_at: string;
  resolved_at: string | null;
}

interface KnowledgeNode {
  id: number;
  node_name: string;
  node_type: string;
  content: string;
}

export default function AgentDashboardPage() {
  const router = useRouter();
  const { role } = useRole();
  
  useEffect(() => {
    if (role !== 'agent' && role !== 'admin') {
      router.push('/landing');
    }
  }, [role, router]);

  const [sessionId, setSessionId] = useState('');
  const [reply, setReply] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);

  const { data: context, mutate: mutateContext } = useSWR<AdminContext>(
    sessionId.trim() ? `/api/admin/context/${sessionId.trim()}` : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  const { data: complaintsData, mutate: mutateComplaints } = useSWR<{ complaints: Complaint[] }>(
    '/api/admin/complaints',
    fetcher,
    { refreshInterval: 15000, revalidateOnFocus: false }
  );

  const { data: knowledgeData } = useSWR<{ knowledge: KnowledgeNode[] }>(
    selectedComplaint?.knowledge_id ? `/api/admin/complaints/${selectedComplaint.id}/knowledge` : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  const filteredComplaints = complaintsData?.complaints?.filter(c => {
    if (filterStatus === 'all') return true;
    return c.status === filterStatus;
  }) || [];

  const handleTakeover = () => {
    if (!sessionId.trim()) return;
    fetch(`/api/admin/takeover/${sessionId.trim()}`, { method: 'POST' })
      .then(() => mutateContext());
  };

  const handleRelease = () => {
    if (!sessionId.trim()) return;
    fetch(`/api/admin/release/${sessionId.trim()}`, { method: 'POST' })
      .then(() => mutateContext());
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

  const handleResolveComplaint = (id: number) => {
    fetch(`/api/admin/complaints/resolve/${id}`, { method: 'POST' })
      .then(() => {
        setSelectedComplaint(null);
        mutateComplaints();
      });
  };

  const getComplaintStatus = (complaint: Complaint) => {
    switch (complaint.status) {
      case '已解决':
        if (complaint.knowledge_id) return { text: '已解决(已关联)', color: 'bg-green-100 text-green-700' };
        return { text: '已解决', color: 'bg-green-100 text-green-700' };
      case '待处理':
        if (complaint.knowledge_id) return { text: '已关联知识', color: 'bg-blue-100 text-blue-700' };
        if (complaint.candidate_id) return { text: '待审核', color: 'bg-yellow-100 text-yellow-700' };
        return { text: '待处理', color: 'bg-gray-100 text-gray-700' };
      default:
        return { text: complaint.status, color: 'bg-gray-100 text-gray-700' };
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 pt-16">
      <NavBar />

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3">
            <div className="bg-white rounded-xl p-4 border border-gray-200 sticky top-20">
              <h2 className="text-lg font-semibold mb-4">📝 投诉列表</h2>
              <div className="flex gap-2 mb-4">
                <button
                  onClick={() => setFilterStatus('all')}
                  className={`flex-1 px-3 py-1.5 text-xs rounded-lg transition-colors ${
                    filterStatus === 'all' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  全部 ({complaintsData?.complaints?.length || 0})
                </button>
                <button
                  onClick={() => setFilterStatus('待处理')}
                  className={`flex-1 px-3 py-1.5 text-xs rounded-lg transition-colors ${
                    filterStatus === '待处理' ? 'bg-yellow-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  待处理 ({complaintsData?.complaints?.filter(c => c.status === '待处理').length || 0})
                </button>
                <button
                  onClick={() => setFilterStatus('已解决')}
                  className={`flex-1 px-3 py-1.5 text-xs rounded-lg transition-colors ${
                    filterStatus === '已解决' ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  已解决 ({complaintsData?.complaints?.filter(c => c.status === '已解决').length || 0})
                </button>
              </div>
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {filteredComplaints.map(c => {
                  const status = getComplaintStatus(c);
                  return (
                    <div
                      key={c.id}
                      onClick={() => setSelectedComplaint(c)}
                      className={`border border-gray-100 rounded-lg p-3 cursor-pointer hover:border-blue-300 transition-colors ${
                        selectedComplaint?.id === c.id ? 'border-blue-500 bg-blue-50' : ''
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-gray-800 text-sm">{c.complaint_type}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${status.color}`}>{status.text}</span>
                      </div>
                      <div className="text-sm text-gray-600 mb-2 line-clamp-2">{c.description}</div>
                      <div className="text-xs text-gray-500">{new Date(c.created_at).toLocaleDateString()}</div>
                    </div>
                  );
                })}
                {filteredComplaints.length === 0 && (
                  <div className="text-center text-gray-400 py-8 text-sm">暂无投诉记录</div>
                )}
              </div>
            </div>
          </div>

          <div className="col-span-6">
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
              <>
                <div className="bg-white rounded-xl p-4 border border-gray-200 mb-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold">💬 对话历史</h2>
                    <div className="flex gap-2">
                      {context.is_taken_over ? (
                        <button onClick={handleRelease} className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600">
                          释放会话
                        </button>
                      ) : (
                        <button onClick={handleTakeover} className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600">
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
                      <button onClick={handleReply} className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
                        发送
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="col-span-3">
            {selectedComplaint ? (
              <div className="bg-white rounded-xl p-4 border border-gray-200 sticky top-20">
                <h3 className="text-md font-semibold mb-3">📋 投诉详情</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-500">投诉类型</span>
                    <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-700">{selectedComplaint.complaint_type}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">投诉描述</span>
                    <p className="text-sm text-gray-700 mt-1">{selectedComplaint.description}</p>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">状态</span>
                    <span className={`px-2 py-1 rounded text-xs ${getComplaintStatus(selectedComplaint).color}`}>
                      {getComplaintStatus(selectedComplaint).text}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">创建时间</span>
                    <span className="text-sm text-gray-600">{new Date(selectedComplaint.created_at).toLocaleString()}</span>
                  </div>
                  {selectedComplaint.knowledge_id && (
                    <div className="pt-3 border-t border-gray-100">
                      <span className="text-gray-500">关联知识</span>
                      {knowledgeData?.knowledge?.map(k => (
                        <div key={k.id} className="mt-2 p-3 bg-blue-50 rounded-lg">
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-sm font-medium text-blue-700">{k.node_name}</span>
                            <span className="text-xs px-2 py-0.5 rounded bg-blue-200 text-blue-700">
                              {k.node_type === 'complaint' ? '投诉类型' : 
                               k.node_type === 'issue' ? '具体问题' :
                               k.node_type === 'solution' ? '解决方案' : '补偿策略'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">{k.content}</p>
                        </div>
                      ))}
                      {!knowledgeData?.knowledge?.length && (
                        <div className="text-sm text-gray-400 mt-2">加载中...</div>
                      )}
                    </div>
                  )}
                  {selectedComplaint.status === '待处理' && (
                    <button
                      onClick={() => handleResolveComplaint(selectedComplaint.id)}
                      className="w-full px-3 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600 transition-colors"
                    >
                      标记已解决
                    </button>
                  )}
                </div>
              </div>
            ) : context ? (
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
              </div>
            ) : (
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-md font-semibold mb-3">📋 详情面板</h3>
                <p className="text-gray-400 text-sm">选择投诉或输入session_id查看详情</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}