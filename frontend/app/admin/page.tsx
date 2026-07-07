'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import KnowledgeGraphD3 from '@/components/KnowledgeGraphD3';
import KnowledgeGraphAggregated from '@/components/KnowledgeGraphAggregated';
import NavBar from '@/components/NavBar';
import { useRole } from '@/context/RoleContext';

interface Complaint {
  id: number;
  user_id: string;
  complaint_type: string;
  description: string;
  resolved: number;
  knowledge_id: number | null;
  candidate_id: number | null;
  created_at: string;
}

interface KnowledgeNode {
  id: number;
  node_type: string;
  content: string;
  reviewed: number;
  parent_id: number | null;
  children: KnowledgeNode[];
}

interface AggregatedNode {
  id: string;
  name: string;
  type: 'complaint' | 'issue' | 'solution' | 'compensation';
  content: string;
  children?: AggregatedNode[];
  complaint_count?: number;
  original_id?: number;
}

interface AggregatedLink {
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

type TabType = 'complaints' | 'candidates' | 'knowledge' | 'stats';

export default function AdminPage() {
  const router = useRouter();
  const { role, adminVerified } = useRole();
  
  useEffect(() => {
    if (role !== 'admin' || !adminVerified) {
      router.push('/landing');
    }
  }, [role, adminVerified, router]);

  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeNode[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('candidates');
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [allNodes, setAllNodes] = useState<KnowledgeNode[]>([]);
  const [relationTarget, setRelationTarget] = useState<number | null>(null);
  const [aggregatedNodes, setAggregatedNodes] = useState<AggregatedNode[]>([]);
  const [aggregatedLinks, setAggregatedLinks] = useState<AggregatedLink[]>([]);
  const [aggregatedStats, setAggregatedStats] = useState<{
    total_complaint_types: number;
    total_issues: number;
    total_solutions: number;
    total_compensations: number;
  } | null>(null);
  const [selectedAggregatedNode, setSelectedAggregatedNode] = useState<AggregatedNode | null>(null);

  const loadData = useCallback(() => {
    fetch('/api/admin/complaints', { cache: 'no-store' })
      .then(res => res.json())
      .then(data => setComplaints(data.complaints || []));

    fetch('/api/admin/knowledge/graph', { cache: 'no-store' })
      .then(res => res.json())
      .then(data => {
        setKnowledge(data.graph || []);
        const flatNodes: KnowledgeNode[] = [];
        const traverse = (node: KnowledgeNode) => {
          flatNodes.push(node);
          node.children?.forEach(traverse);
        };
        data.graph?.forEach(traverse);
        setAllNodes(flatNodes);
      });

    fetch('/api/admin/knowledge/graph/aggregated', { cache: 'no-store' })
      .then(res => res.json())
      .then(data => {
        setAggregatedNodes(data.nodes || []);
        setAggregatedLinks(data.links || []);
        setAggregatedStats(data.statistics || null);
      });

    fetch('/api/admin/candidates', { cache: 'no-store' })
      .then(res => res.json())
      .then(data => setCandidates(data.candidates || []));

    fetch('/api/admin/stats', { cache: 'no-store' })
      .then(res => res.json())
      .then(data => setStats(data));
  }, []);

  useEffect(() => {
    if (role === 'admin' && adminVerified) {
      loadData();
    }
  }, [role, adminVerified, loadData]);

  const handleReview = (id: number) => {
    fetch('/api/admin/knowledge/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then(() => loadData());
  };

  const handleDelete = (id: number) => {
    fetch(`/api/admin/knowledge/${id}`, { method: 'DELETE' })
      .then(() => {
        setSelectedNode(null);
        loadData();
      });
  };

  const handleResolve = (id: number) => {
    fetch('/api/admin/complaints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'resolve', id }),
    }).then(() => loadData());
  };

  const handleAddRelation = (parentId: number, childId: number) => {
    fetch('/api/admin/knowledge/relation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parent_id: parentId, child_id: childId }),
    }).then(() => loadData());
  };

  const handleApproveCandidate = (id: number) => {
    fetch('/api/admin/candidate-approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then(() => loadData());
  };

  const handleRejectCandidate = (id: number) => {
    fetch('/api/admin/candidate-reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then(() => loadData());
  };

  const getNodeLabel = (node_type: string) => {
    switch (node_type) {
      case 'complaint_type': return '投诉类型';
      case 'solution': return '解决方案';
      case 'compensation': return '补偿策略';
      default: return '其他';
    }
  };

  const getNodeColor = (node_type: string) => {
    switch (node_type) {
      case 'complaint_type': return 'bg-red-500';
      case 'solution': return 'bg-cyan-500';
      case 'compensation': return 'bg-yellow-400';
      default: return 'bg-blue-500';
    }
  };

  const getComplaintStatus = (complaint: Complaint) => {
    if (complaint.resolved) {
      if (complaint.knowledge_id) return { text: '已解决(已关联)', color: 'bg-green-100 text-green-700' };
      return { text: '已解决', color: 'bg-green-100 text-green-700' };
    }
    if (complaint.knowledge_id) return { text: '已关联知识', color: 'bg-blue-100 text-blue-700' };
    if (complaint.candidate_id) return { text: '待审核', color: 'bg-yellow-100 text-yellow-700' };
    return { text: '待处理', color: 'bg-gray-100 text-gray-700' };
  };

  const renderComplaints = () => (
    <div className="bg-white rounded-xl p-4 border border-gray-200">
      <h2 className="text-lg font-semibold mb-4">📋 投诉列表</h2>
      <div className="space-y-3 max-h-[500px] overflow-y-auto">
        {complaints.map(c => {
          const status = getComplaintStatus(c);
          return (
            <div
              key={c.id}
              onClick={() => { setSelectedComplaint(c); setSelectedNode(null); setSelectedCandidate(null); }}
              className={`border border-gray-100 rounded-lg p-3 cursor-pointer hover:border-blue-300 ${selectedComplaint?.id === c.id ? 'border-blue-500' : ''}`}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-medium text-gray-800 text-sm">{c.complaint_type}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${status.color}`}>{status.text}</span>
              </div>
              <div className="text-sm text-gray-600 truncate">{c.description}</div>
              <div className="text-xs text-gray-400 mt-1">{new Date(c.created_at).toLocaleString()}</div>
              {!c.resolved && (
                <button
                  onClick={(e) => { e.stopPropagation(); handleResolve(c.id); }}
                  className="mt-2 px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600"
                >
                  解决
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderCandidates = () => (
    <div className="bg-white rounded-xl p-4 border border-gray-200">
      <h2 className="text-lg font-semibold mb-4">⏳ 待审核候选</h2>
      <div className="space-y-3 max-h-[500px] overflow-y-auto">
        {candidates.filter(c => c.status === 'pending').map(c => (
          <div
            key={c.id}
            onClick={() => { setSelectedCandidate(c); setSelectedNode(null); setSelectedComplaint(null); }}
            className={`border border-gray-100 rounded-lg p-3 cursor-pointer hover:border-blue-300 ${selectedCandidate?.id === c.id ? 'border-blue-500' : ''}`}
          >
            <div className="flex justify-between items-center mb-1">
              <span className="font-medium text-gray-800 text-sm">{c.complaint_type}</span>
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">待审核</span>
            </div>
            <div className="text-sm text-gray-600 mb-2">投诉：{c.complaint_description}</div>
            <div className="text-xs text-gray-500 mb-1">解决方案：{c.proposed_solution}</div>
            <div className="text-xs text-gray-500 mb-2">补偿策略：{c.proposed_compensation}</div>
            <div className="flex gap-2">
              <button
                onClick={(e) => { e.stopPropagation(); handleApproveCandidate(c.id); }}
                className="flex-1 px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600"
              >
                审核通过
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleRejectCandidate(c.id); }}
                className="flex-1 px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
              >
                拒绝
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderKnowledge = () => (
    <div className="bg-white rounded-xl p-4 border border-gray-200 h-[560px]">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">✅ 知识图谱</h2>
        {aggregatedStats && (
          <div className="text-sm text-gray-500">
            投诉类型:{aggregatedStats.total_complaint_types} | 具体问题:{aggregatedStats.total_issues} | 方案:{aggregatedStats.total_solutions} | 补偿:{aggregatedStats.total_compensations}
          </div>
        )}
      </div>
      <div className="h-[calc(100%-40px)]">
        <KnowledgeGraphAggregated
          nodes={aggregatedNodes}
          links={aggregatedLinks}
          onNodeClick={(node) => { setSelectedAggregatedNode(node || null); setSelectedNode(null); setSelectedComplaint(null); setSelectedCandidate(null); }}
        />
      </div>
    </div>
  );

  const renderStats = () => (
    <div className="bg-white rounded-xl p-4 border border-gray-200">
      <h2 className="text-lg font-semibold mb-4">📊 统计看板</h2>
      {stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-gray-500">总投诉</div>
              <div className="text-3xl font-bold text-blue-600">{stats.total_count}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-sm text-gray-500">已解决</div>
              <div className="text-3xl font-bold text-green-600">{stats.resolved_count}</div>
            </div>
            <div className="bg-yellow-50 rounded-lg p-4">
              <div className="text-sm text-gray-500">待审核候选</div>
              <div className="text-3xl font-bold text-yellow-600">{stats.pending_candidates}</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-gray-500">已审核知识</div>
              <div className="text-3xl font-bold text-purple-600">{stats.reviewed_knowledge}</div>
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-4">投诉类型分布</div>
            <div className="space-y-2">
              {stats.by_type.map(t => (
                <div key={t.complaint_type} className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-4">
                    <div className="h-4 rounded-full bg-blue-500" style={{ width: `${(t.count / stats.total_count) * 100}%` }}></div>
                  </div>
                  <span className="text-sm text-gray-600 w-24">{t.complaint_type}</span>
                  <span className="text-sm font-semibold">{t.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const [complaintKnowledge, setComplaintKnowledge] = useState<any[]>([]);
  const [nodeComplaints, setNodeComplaints] = useState<any[]>([]);

  useEffect(() => {
    if (selectedComplaint?.knowledge_id) {
      fetch(`/api/admin/knowledge-complaints?knowledge_id=${selectedComplaint.knowledge_id}`, { cache: 'no-store' })
        .then(res => res.json())
        .then(data => setComplaintKnowledge(data.complaints || []));
    } else {
      setComplaintKnowledge([]);
    }
  }, [selectedComplaint]);

  useEffect(() => {
    if (selectedNode?.id) {
      fetch(`/api/admin/knowledge-complaints?knowledge_id=${selectedNode.id}`, { cache: 'no-store' })
        .then(res => res.json())
        .then(data => setNodeComplaints(data.complaints || []));
    } else {
      setNodeComplaints([]);
    }
  }, [selectedNode]);

  const renderComplaintsDetail = () => {
    if (selectedComplaint) {
      return (
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <h3 className="text-md font-semibold mb-3">📋 投诉详情</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-500">类型</span>
              <span className={`px-2 py-1 rounded text-xs ${getNodeColor(selectedComplaint.complaint_type)} text-white`}>
                {selectedComplaint.complaint_type}
              </span>
            </div>
            <div>
              <span className="text-gray-500">描述</span>
              <p className="text-sm text-gray-700 mt-1">{selectedComplaint.description}</p>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">状态</span>
              <span className={`px-2 py-1 rounded text-xs ${getComplaintStatus(selectedComplaint).color}`}>
                {getComplaintStatus(selectedComplaint).text}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">时间</span>
              <span className="text-sm">{new Date(selectedComplaint.created_at).toLocaleString()}</span>
            </div>
            {selectedComplaint.knowledge_id && (
              <div className="bg-blue-50 rounded-lg p-3">
                <span className="text-gray-500 text-sm">关联知识</span>
                <p className="text-sm text-blue-600 mt-1">已关联知识节点</p>
              </div>
            )}
            {selectedComplaint.candidate_id && !selectedComplaint.knowledge_id && (
              <div className="bg-yellow-50 rounded-lg p-3">
                <span className="text-gray-500 text-sm">待审核候选</span>
                <p className="text-sm text-yellow-600 mt-1">已生成候选知识，等待审核</p>
              </div>
            )}
            {!selectedComplaint.resolved && (
              <button
                onClick={() => handleResolve(selectedComplaint.id)}
                className="w-full px-3 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600"
              >
                标记为已解决
              </button>
            )}
          </div>
        </div>
      );
    }
    return (
      <div className="bg-white rounded-xl p-4 border border-gray-200">
        <h3 className="text-md font-semibold mb-3">📋 投诉详情</h3>
        <p className="text-gray-400 text-sm">点击投诉条目查看详情</p>
      </div>
    );
  };

  const renderCandidatesDetail = () => {
    if (selectedCandidate) {
      return (
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <h3 className="text-md font-semibold mb-3">⏳ 候选详情</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-500">投诉类型</span>
              <span className={`px-2 py-1 rounded text-xs ${getNodeColor(selectedCandidate.complaint_type)} text-white`}>
                {selectedCandidate.complaint_type}
              </span>
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
                className="flex-1 px-3 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600"
              >
                审核通过
              </button>
              <button
                onClick={() => handleRejectCandidate(selectedCandidate.id)}
                className="flex-1 px-3 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600"
              >
                拒绝
              </button>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="bg-white rounded-xl p-4 border border-gray-200">
        <h3 className="text-md font-semibold mb-3">⏳ 候选详情</h3>
        <p className="text-gray-400 text-sm">点击候选条目查看详情</p>
      </div>
    );
  };

  const renderKnowledgeDetail = () => {
    if (selectedAggregatedNode) {
      const typeLabels = {
        complaint: '投诉类型',
        issue: '具体问题',
        solution: '解决方案',
        compensation: '补偿策略',
      };
      const typeColors = {
        complaint: 'bg-red-500',
        issue: 'bg-orange-500',
        solution: 'bg-cyan-500',
        compensation: 'bg-yellow-400',
      };
      const relatedComplaints = selectedAggregatedNode.type === 'complaint' 
        ? complaints.filter(c => c.complaint_type === selectedAggregatedNode.name)
        : complaints.filter(c => c.description.includes(selectedAggregatedNode.name));
      
      return (
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <h3 className="text-md font-semibold mb-3">📋 节点详情</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-500">名称</span>
              <span className="font-medium">{selectedAggregatedNode.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">类型</span>
              <span className={`px-2 py-1 rounded text-xs ${typeColors[selectedAggregatedNode.type]} text-white`}>
                {typeLabels[selectedAggregatedNode.type]}
              </span>
            </div>
            <div>
              <span className="text-gray-500">完整内容</span>
              <p className="text-sm text-gray-700 mt-1">{selectedAggregatedNode.content}</p>
            </div>
            {selectedAggregatedNode.complaint_count && (
              <div className="flex justify-between">
                <span className="text-gray-500">关联投诉数</span>
                <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-700">
                  {selectedAggregatedNode.complaint_count}条
                </span>
              </div>
            )}
            {selectedAggregatedNode.children && selectedAggregatedNode.children.length > 0 && (
              <div>
                <span className="text-gray-500">关联子节点</span>
                <div className="space-y-2 mt-2">
                  {selectedAggregatedNode.children.map(child => (
                    <div key={child.id} className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${typeColors[child.type]}`}></div>
                      <span className="text-sm text-gray-600">{child.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {relatedComplaints.length > 0 && (
              <div>
                <span className="text-gray-500">关联投诉</span>
                <div className="space-y-2 mt-2">
                  {relatedComplaints.slice(0, 5).map(c => (
                    <div key={c.id} className="bg-gray-50 rounded-lg p-2">
                      <div className="text-xs text-gray-600 truncate">{c.description}</div>
                      <div className="text-xs text-gray-400">{new Date(c.created_at).toLocaleDateString()}</div>
                    </div>
                  ))}
                </div>
                {relatedComplaints.length > 5 && (
                  <div className="text-xs text-gray-400 mt-1">共{relatedComplaints.length}条，显示前5条</div>
                )}
              </div>
            )}
            {selectedAggregatedNode.original_id && (
              <div className="flex gap-2">
                <button
                  onClick={() => { handleDelete(selectedAggregatedNode.original_id); setSelectedAggregatedNode(null); loadData(); }}
                  className="flex-1 px-3 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600"
                >
                  删除
                </button>
              </div>
            )}
          </div>
        </div>
      );
    }
    return (
      <div className="bg-white rounded-xl p-4 border border-gray-200">
        <h3 className="text-md font-semibold mb-3">📋 节点详情</h3>
        <p className="text-gray-400 text-sm">点击图谱节点查看详情</p>
      </div>
    );
  };

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
          <div className="col-span-2">
            <nav className="bg-white rounded-xl p-4 border border-gray-200">
              <ul className="space-y-2">
                <li>
                  <button
                    onClick={() => setActiveTab('complaints')}
                    className={`w-full px-4 py-3 rounded-lg text-left transition-colors ${activeTab === 'complaints' ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    📋 投诉列表
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveTab('candidates')}
                    className={`w-full px-4 py-3 rounded-lg text-left transition-colors ${activeTab === 'candidates' ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    ⏳ 待审核
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveTab('knowledge')}
                    className={`w-full px-4 py-3 rounded-lg text-left transition-colors ${activeTab === 'knowledge' ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    ✅ 知识图谱
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveTab('stats')}
                    className={`w-full px-4 py-3 rounded-lg text-left transition-colors ${activeTab === 'stats' ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    📊 统计看板
                  </button>
                </li>
              </ul>
            </nav>
          </div>

          <div className="col-span-7">
            {activeTab === 'complaints' && renderComplaints()}
            {activeTab === 'candidates' && renderCandidates()}
            {activeTab === 'knowledge' && renderKnowledge()}
            {activeTab === 'stats' && renderStats()}
          </div>

          <div className="col-span-3">
            {activeTab === 'complaints' && renderComplaintsDetail()}
            {activeTab === 'candidates' && renderCandidatesDetail()}
            {activeTab === 'knowledge' && renderKnowledgeDetail()}
            {activeTab === 'stats' && (
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-md font-semibold mb-3">📊 统计说明</h3>
                <p className="text-gray-400 text-sm">查看投诉数据统计概览</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}