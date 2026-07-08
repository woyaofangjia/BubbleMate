'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useSWR from 'swr';
import NavBar from '@/components/NavBar';
import { useRole } from '@/context/RoleContext';
import { fetcher } from '@/lib/swr';

const KnowledgeGraphAggregated = dynamic(
  () => import('@/components/KnowledgeGraphAggregated'),
  {
    loading: () => <div className="flex items-center justify-center h-full text-gray-400">加载图谱中...</div>,
    ssr: false,
  }
);

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

interface GraphNode {
  id: string;
  name: string;
  type: 'complaint' | 'issue' | 'solution' | 'compensation';
  content: string;
  children?: GraphNode[];
  complaint_count?: number;
  original_id?: number;
}

interface GraphLink {
  source: string;
  target: string;
}

interface Candidate {
  id: number;
  complaint_id: number;
  complaint_type: string;
  proposed_solution: string;
  proposed_compensation: string;
  status: string;
  complaint_description: string;
  user_id: string;
  created_at: string;
}

interface Stats {
  by_type: { complaint_type: string; count: number }[];
  today_count: number;
  resolved_count: number;
  total_count: number;
  pending_candidates: number;
  reviewed_knowledge: number;
}

export default function AdminPage() {
  const router = useRouter();
  const { role, adminVerified } = useRole();
  
  useEffect(() => {
    if (role !== 'admin' || !adminVerified) {
      router.push('/landing');
    }
  }, [role, adminVerified, router]);

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);

  const { data: complaintsData, mutate: mutateComplaints } = useSWR<{ complaints: Complaint[] }>(
    '/api/admin/complaints',
    fetcher,
    { refreshInterval: 15000, revalidateOnFocus: false }
  );
  const complaints = complaintsData?.complaints || [];

  const { data: graphData, mutate: mutateGraph } = useSWR<{ nodes: GraphNode[]; links: GraphLink[]; statistics: any }>(
    '/api/admin/knowledge/graph/aggregated',
    fetcher,
    { refreshInterval: 60000, revalidateOnFocus: false }
  );
  const aggregatedNodes = graphData?.nodes || [];
  const aggregatedLinks = graphData?.links || [];
  const aggregatedStats = graphData?.statistics || null;

  const { data: candidatesData, mutate: mutateCandidates } = useSWR<{ candidates: Candidate[] }>(
    '/api/admin/candidates',
    fetcher,
    { refreshInterval: 30000, revalidateOnFocus: false }
  );
  const candidates = candidatesData?.candidates || [];

  const { data: stats, mutate: mutateStats } = useSWR<Stats>(
    '/api/admin/stats',
    fetcher,
    { refreshInterval: 30000, revalidateOnFocus: false }
  );

  const refreshData = () => {
    mutateComplaints();
    mutateGraph();
    mutateCandidates();
    mutateStats();
  };

  const handleApproveCandidate = (id: number) => {
    fetch(`/api/admin/candidates/${id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }).then(() => {
      setSelectedCandidate(null);
      refreshData();
    });
  };

  const handleRejectCandidate = (id: number) => {
    fetch(`/api/admin/candidates/${id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }).then(() => {
      setSelectedCandidate(null);
      refreshData();
    });
  };

  const handleDeleteNode = (id: number) => {
    fetch(`/api/admin/knowledge/${id}`, { method: 'DELETE' })
      .then(() => {
        setSelectedNode(null);
        refreshData();
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

  const pendingCandidates = candidates.filter(c => c.status === 'pending');

  return (
    <div className="min-h-screen bg-gray-100 pt-16">
      <NavBar />

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">总投诉</div>
            <div className="text-3xl font-bold text-gray-800">{stats?.total_count || 0}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">待审核候选</div>
            <div className="text-3xl font-bold text-yellow-500">{stats?.pending_candidates || 0}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">已审核知识</div>
            <div className="text-3xl font-bold text-green-500">{stats?.reviewed_knowledge || 0}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">已解决</div>
            <div className="text-3xl font-bold text-blue-500">{stats?.resolved_count || 0}</div>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3">
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                ⏳ 待审核候选
                <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                  {pendingCandidates.length}
                </span>
              </h2>
              <div className="space-y-3 max-h-[700px] overflow-y-auto">
                {pendingCandidates.map(c => (
                  <div
                    key={c.id}
                    onClick={() => { setSelectedCandidate(c); setSelectedNode(null); }}
                    className={`border border-gray-100 rounded-lg p-3 cursor-pointer hover:border-blue-300 transition-colors ${selectedCandidate?.id === c.id ? 'border-blue-500 bg-blue-50' : ''}`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium text-gray-800 text-sm">{c.complaint_type}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">待审核</span>
                    </div>
                    <div className="text-sm text-gray-600 mb-2 line-clamp-2">{c.complaint_description}</div>
                    <div className="text-xs text-gray-500 mb-1">解决方案：{c.proposed_solution}</div>
                    <div className="text-xs text-gray-500 mb-2">补偿策略：{c.proposed_compensation}</div>
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleApproveCandidate(c.id); }}
                        className="flex-1 px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                      >
                        通过
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRejectCandidate(c.id); }}
                        className="flex-1 px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                      >
                        拒绝
                      </button>
                    </div>
                  </div>
                ))}
                {pendingCandidates.length === 0 && (
                  <div className="text-center text-gray-400 py-8">
                    <div className="text-4xl mb-2">🎉</div>
                    <div className="text-sm">暂无待审核候选</div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="col-span-6">
            <div className="bg-white rounded-xl p-4 border border-gray-200 h-[740px]">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  ✅ 知识图谱管理
                </h2>
                {aggregatedStats && (
                  <div className="text-sm text-gray-500">
                    投诉类型:{aggregatedStats.total_complaint_types} | 问题:{aggregatedStats.total_issues} | 方案:{aggregatedStats.total_solutions} | 补偿:{aggregatedStats.total_compensations}
                  </div>
                )}
              </div>
              <div className="h-[calc(100%-50px)]">
                <KnowledgeGraphAggregated
                  nodes={aggregatedNodes}
                  links={aggregatedLinks}
                  onNodeClick={(node) => { setSelectedNode(node || null); setSelectedCandidate(null); }}
                />
              </div>
            </div>
          </div>

          <div className="col-span-3">
            {selectedCandidate ? (
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-md font-semibold mb-3">⏳ 候选详情</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-500">投诉类型</span>
                    <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-700">{selectedCandidate.complaint_type}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">投诉描述</span>
                    <p className="text-sm text-gray-700 mt-1">{selectedCandidate.complaint_description}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">建议解决方案</span>
                    <p className="text-sm text-gray-700 mt-1">{selectedCandidate.proposed_solution}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">建议补偿策略</span>
                    <p className="text-sm text-gray-700 mt-1">{selectedCandidate.proposed_compensation}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleApproveCandidate(selectedCandidate.id)}
                      className="flex-1 px-3 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600 transition-colors"
                    >
                      审核通过
                    </button>
                    <button
                      onClick={() => handleRejectCandidate(selectedCandidate.id)}
                      className="flex-1 px-3 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600 transition-colors"
                    >
                      拒绝
                    </button>
                  </div>
                </div>
              </div>
            ) : selectedNode ? (
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-md font-semibold mb-3">📋 节点详情</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-500">名称</span>
                    <span className="font-medium">{selectedNode.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">类型</span>
                    <span className={`px-2 py-1 rounded text-xs text-white ${
                      selectedNode.type === 'complaint' ? 'bg-red-500' :
                      selectedNode.type === 'issue' ? 'bg-orange-500' :
                      selectedNode.type === 'solution' ? 'bg-cyan-500' :
                      'bg-yellow-400'
                    }`}>
                      {selectedNode.type === 'complaint' ? '投诉类型' :
                       selectedNode.type === 'issue' ? '具体问题' :
                       selectedNode.type === 'solution' ? '解决方案' : '补偿策略'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">完整内容</span>
                    <p className="text-sm text-gray-700 mt-1">{selectedNode.content}</p>
                  </div>
                  {selectedNode.complaint_count && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">关联投诉数</span>
                      <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-700">
                        {selectedNode.complaint_count}条
                      </span>
                    </div>
                  )}
                  {selectedNode.type === 'issue' && selectedNode.children && selectedNode.children.length > 0 && (
                    <>
                      <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-blue-600 font-medium text-sm">📋 解决方案</span>
                          <span className="px-2 py-0.5 bg-blue-200 text-blue-700 rounded text-xs">必选</span>
                        </div>
                        {selectedNode.children.filter(c => c.type === 'solution').map(child => (
                          <div key={child.id} className="text-sm text-gray-700">
                            {child.content}
                          </div>
                        ))}
                      </div>
                      <div className="text-xs text-gray-500 mt-2 text-center">
                        在处理问题的同时，还可以为用户提供以下补偿方案：
                      </div>
                      <div className="mt-2 p-3 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-green-600 font-medium text-sm">🎁 可选补偿方案</span>
                          <span className="px-2 py-0.5 bg-green-200 text-green-700 rounded text-xs">多选</span>
                        </div>
                        <div className="space-y-2">
                          {selectedNode.children.filter(c => c.type === 'compensation').map(child => (
                            <div key={child.id} className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-green-500"></div>
                              <span className="text-sm text-gray-700">{child.content}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  )}
                  {selectedNode.type !== 'issue' && selectedNode.children && selectedNode.children.length > 0 && (
                    <div>
                      <span className="text-gray-500">关联子节点</span>
                      <div className="space-y-2 mt-2">
                        {selectedNode.children.map(child => (
                          <div key={child.id} className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded-full ${
                              child.type === 'complaint' ? 'bg-red-500' :
                              child.type === 'issue' ? 'bg-orange-500' :
                              child.type === 'solution' ? 'bg-cyan-500' :
                              'bg-yellow-400'
                            }`}></div>
                            <span className="text-sm text-gray-600">{child.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {selectedNode.type === 'complaint' && (
                    <div>
                      <span className="text-gray-500">关联投诉</span>
                      <div className="space-y-2 mt-2">
                        {complaints.filter(c => c.complaint_type === selectedNode.name).slice(0, 5).map(c => (
                          <div key={c.id} className="bg-gray-50 rounded-lg p-2">
                            <div className="text-xs text-gray-600 truncate">{c.description}</div>
                            <div className="text-xs text-gray-400">{new Date(c.created_at).toLocaleDateString()}</div>
                          </div>
                        ))}
                        {complaints.filter(c => c.complaint_type === selectedNode.name).length > 5 && (
                          <div className="text-xs text-gray-400 mt-1">共{complaints.filter(c => c.complaint_type === selectedNode.name).length}条</div>
                        )}
                      </div>
                    </div>
                  )}
                  {selectedNode.original_id !== undefined && (
                    <button
                      onClick={() => { handleDeleteNode(selectedNode.original_id!); }}
                      className="w-full px-3 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600 transition-colors"
                    >
                      软删除节点
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-md font-semibold mb-3">📋 详情面板</h3>
                <p className="text-gray-400 text-sm">点击候选或图谱节点查看详情</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}