'use client';

import { useState, useEffect } from 'react';

interface Intervention {
  id: string;
  session_id: string;
  type: string;
  confidence: {
    overall: number;
    intent: number;
    tool: number;
    context: number;
    safety: number;
  };
  user_message: string;
  agent_response: string;
  status: string;
  created_at: string;
}

export default function HumanSupport() {
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [stats, setStats] = useState({
    total_interventions: 0,
    resolved: 0,
    pending: 0,
    resolution_rate: 0,
    avg_resolution_time: 0
  });
  const [selected, setSelected] = useState<Intervention | null>(null);
  const [resolution, setResolution] = useState('');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [intervRes, statsRes] = await Promise.all([
        fetch('/api/human-in-loop/pending'),
        fetch('/api/human-in-loop/stats')
      ]);
      
      if (intervRes.ok) setInterventions(await intervRes.json());
      if (statsRes.ok) setStats(await statsRes.ok);
    } catch (error) {
      console.error('获取数据失败:', error);
    }
  };

  const handleResolve = async () => {
    if (!selected || !resolution.trim()) return;

    try {
      const response = await fetch(`/api/human-in-loop/${selected.id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution, agent_id: 'agent-001' })
      });

      if (response.ok) {
        setResolution('');
        setSelected(null);
        fetchData();
      }
    } catch (error) {
      console.error('解决失败:', error);
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      low_confidence: '置信度低',
      tool_failure: '工具失败',
      user_complaint: '用户投诉',
      safety_check: '安全检查',
      complex_query: '复杂查询'
    };
    return labels[type] || type;
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      low_confidence: 'bg-yellow-100 text-yellow-800',
      tool_failure: 'bg-red-100 text-red-800',
      user_complaint: 'bg-orange-100 text-orange-800',
      safety_check: 'bg-purple-100 text-purple-800',
      complex_query: 'bg-blue-100 text-blue-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">人工客服工作台</h1>
            <p className="text-sm text-gray-500 mt-1">Human-in-the-Loop 管理面板</p>
          </div>
          <div className="flex gap-4">
            <div className="text-center px-4 py-2 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{stats.total_interventions}</div>
              <div className="text-xs text-blue-500">总介入数</div>
            </div>
            <div className="text-center px-4 py-2 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{stats.resolved}</div>
              <div className="text-xs text-green-500">已解决</div>
            </div>
            <div className="text-center px-4 py-2 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
              <div className="text-xs text-yellow-500">待处理</div>
            </div>
            <div className="text-center px-4 py-2 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {(stats.resolution_rate * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-purple-500">解决率</div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-2 gap-6">
          {/* 左侧：待处理列表 */}
          <div>
            <h2 className="text-lg font-semibold mb-4">待处理介入请求</h2>
            <div className="space-y-3">
              {interventions.length === 0 ? (
                <div className="bg-white rounded-lg p-8 text-center text-gray-500">
                  <div className="text-4xl mb-2">✅</div>
                  <p>暂无待处理请求</p>
                </div>
              ) : (
                interventions.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setSelected(item)}
                    className={`bg-white rounded-lg p-4 border-2 cursor-pointer transition-colors ${
                      selected?.id === item.id ? 'border-blue-500' : 'border-transparent hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(item.type)}`}>
                        {getTypeLabel(item.type)}
                      </span>
                      <span className="text-xs text-gray-400">
                        {new Date(item.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{item.user_message}</p>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-500">置信度:</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            item.confidence.overall > 0.5 ? 'bg-green-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${item.confidence.overall * 100}%` }}
                        />
                      </div>
                      <span className="text-gray-600">{(item.confidence.overall * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 右侧：处理面板 */}
          <div>
            <h2 className="text-lg font-semibold mb-4">处理详情</h2>
            {selected ? (
              <div className="bg-white rounded-lg p-6 space-y-4">
                {/* 会话信息 */}
                <div>
                  <label className="text-sm font-medium text-gray-600">用户消息</label>
                  <div className="mt-1 p-3 bg-gray-50 rounded-lg text-sm">
                    {selected.user_message}
                  </div>
                </div>

                {/* 置信度详情 */}
                <div>
                  <label className="text-sm font-medium text-gray-600">置信度分析</label>
                  <div className="mt-2 space-y-2">
                    {[
                      { label: '意图识别', value: selected.confidence.intent },
                      { label: '工具可靠性', value: selected.confidence.tool },
                      { label: '上下文连续性', value: selected.confidence.context },
                      { label: '安全评分', value: selected.confidence.safety },
                    ].map((item) => (
                      <div key={item.label} className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 w-24">{item.label}</span>
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              item.value > 0.7 ? 'bg-green-500' : item.value > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${item.value * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600 w-12">{(item.value * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 解决输入 */}
                <div>
                  <label className="text-sm font-medium text-gray-600">处理方案</label>
                  <textarea
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    placeholder="输入处理方案..."
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 text-sm"
                    rows={4}
                  />
                </div>

                {/* 操作按钮 */}
                <div className="flex gap-3">
                  <button
                    onClick={handleResolve}
                    disabled={!resolution.trim()}
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    标记为已解决
                  </button>
                  <button
                    onClick={() => setSelected(null)}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  >
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg p-8 text-center text-gray-500">
                <div className="text-4xl mb-2">👈</div>
                <p>选择左侧请求进行处理</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}