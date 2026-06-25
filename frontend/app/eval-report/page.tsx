'use client';

import { useState, useEffect } from 'react';

interface EvalReport {
  timestamp: string;
  test_cases_count: number;
  level1_component: {
    intent_accuracy: number;
    tool_accuracy: number;
    clarification_rate: number;
    avg_latency_ms: number;
  };
  level2_end_to_end: {
    solved_rate: number;
    partial_rate: number;
    failure_rate: number;
  };
  level3_adversarial: {
    adversarial_pass_rate: number;
    category_breakdown: Record<string, { passed: number; total: number }>;
  };
  overall_pass_rate: number;
  bad_cases: Array<{
    case_id: string;
    category: string;
    predicted_intent: string;
    expected_intent: string;
  }>;
}

export default function EvalReportPage() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReport();
  }, []);

  const fetchReport = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/eval/report');
      if (!res.ok) throw new Error('评测报告未生成');
      const data = await res.json();
      setReport(data);
      setError(null);
    } catch (err) {
      setError('请先运行评测脚本: python scripts/bubble_eval_runner.py');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">加载评测报告...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md">
          <div className="text-center">
            <div className="text-red-500 mb-4">⚠️</div>
            <h2 className="text-xl font-bold mb-2">评测报告未生成</h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={fetchReport}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              重新加载
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">BubbleMate 评测报告</h1>
              <p className="text-gray-600 mt-1">Anthropic框架三层评测体系</p>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">生成时间</div>
              <div className="text-lg font-semibold">{new Date(report.timestamp).toLocaleString()}</div>
            </div>
          </div>
          
          {/* Overall Pass Rate */}
          <div className="mt-6 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">综合通过率</div>
                <div className="text-4xl font-bold text-blue-600">
                  {(report.overall_pass_rate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600">测试样本数</div>
                <div className="text-2xl font-semibold">{report.test_cases_count}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Level 1: Component-level */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Level 1: 组件级评测
          </h2>
          
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-gray-600">意图识别准确率</div>
              <div className="text-2xl font-bold text-blue-600">
                {(report.level1_component.intent_accuracy * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                目标: ≥90%
              </div>
            </div>
            
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-sm text-gray-600">工具选择准确率</div>
              <div className="text-2xl font-bold text-green-600">
                {(report.level1_component.tool_accuracy * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                目标: ≥85%
              </div>
            </div>
            
            <div className="bg-yellow-50 rounded-lg p-4">
              <div className="text-sm text-gray-600">反问准确率</div>
              <div className="text-2xl font-bold text-yellow-600">
                {(report.level1_component.clarification_rate * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                目标: ≥80%
              </div>
            </div>
            
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-gray-600">平均响应时间</div>
              <div className="text-2xl font-bold text-purple-600">
                {report.level1_component.avg_latency_ms.toFixed(0)}ms
              </div>
              <div className="text-xs text-gray-500 mt-1">
                目标: <500ms
              </div>
            </div>
          </div>
        </div>

        {/* Level 2: End-to-end */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Level 2: 端到端评测
          </h2>
          
          <div className="flex gap-4">
            <div className="flex-1 bg-green-50 rounded-lg p-4">
              <div className="text-sm text-gray-600">完全解决率</div>
              <div className="text-2xl font-bold text-green-600">
                {(report.level2_end_to_end.solved_rate * 100).toFixed(1)}%
              </div>
            </div>
            
            <div className="flex-1 bg-yellow-50 rounded-lg p-4">
              <div className="text-sm text-gray-600">部分解决率</div>
              <div className="text-2xl font-bold text-yellow-600">
                {(report.level2_end_to_end.partial_rate * 100).toFixed(1)}%
              </div>
            </div>
            
            <div className="flex-1 bg-red-50 rounded-lg p-4">
              <div className="text-sm text-gray-600">未解决率</div>
              <div className="text-2xl font-bold text-red-600">
                {(report.level2_end_to_end.failure_rate * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

        {/* Level 3: Adversarial */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Level 3: 对抗性评测
          </h2>
          
          <div className="bg-orange-50 rounded-lg p-4 mb-4">
            <div className="text-sm text-gray-600">对抗性通过率</div>
            <div className="text-2xl font-bold text-orange-600">
              {(report.level3_adversarial.adversarial_pass_rate * 100).toFixed(1)}%
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(report.level3_adversarial.category_breakdown).map(([category, data]) => (
              <div key={category} className="bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-600">{category}</div>
                <div className="text-sm font-semibold">
                  {data.passed}/{data.total}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bad Cases */}
        {report.bad_cases.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-red-600 mb-4">
              Bad Cases 根因分析 ({report.bad_cases.length}条)
            </h2>
            
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">ID</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">类别</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">预测意图</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">期望意图</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {report.bad_cases.map((case_) => (
                    <tr key={case_.case_id}>
                      <td className="px-4 py-2 text-sm">{case_.case_id}</td>
                      <td className="px-4 py-2 text-sm">{case_.category}</td>
                      <td className="px-4 py-2 text-sm text-red-600">{case_.predicted_intent}</td>
                      <td className="px-4 py-2 text-sm text-green-600">{case_.expected_intent}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}