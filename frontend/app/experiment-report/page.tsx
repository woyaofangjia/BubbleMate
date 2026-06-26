'use client';

import { useState, useEffect } from 'react';

interface StratifiedResults {
  easy_accuracy: number;
  medium_accuracy: number;
  hard_accuracy: number;
  overall_accuracy: number;
  adversarial_pass_rate: number;
  adversarial_by_type: {
    sarcasm: { correct: number; total: number };
    reference: { correct: number; total: number };
    history_comparison: { correct: number; total: number };
    vague: { correct: number; total: number };
    implied?: { correct: number; total: number };
    neutral?: { correct: number; total: number };
    implied_complaint?: { correct: number; total: number };
  };
}

interface SatisfactionResults {
  average_score: number;
  satisfaction_rate: number;
  total_samples: number;
  method: string;
  distribution: {
    "5分": number;
    "4分": number;
    "3分": number;
    "2分": number;
    "1分": number;
  };
  avg_by_difficulty: Record<string, number>;
  dimensions: string[];
}

interface ExperimentResults {
  intent_accuracy: {
    accuracy: number;
    total: number;
    correct: number;
    bad_cases: Array<{
      input: string;
      expected: string;
      actual: string;
      confidence: number;
    }>;
  };
  baseline_comparison: {
    baseline_accuracy: number;
    agent_accuracy: number;
    improvement: number;
    baseline_type: string;
  };
  tool_fallback: {
    success_rate: number;
    details: Array<{
      name: string;
      expected: string;
      actual: string;
      correct: boolean;
    }>;
  };
  memory_window: {
    memory_results: Array<{
      window_size: number;
      message_count: number;
      has_summary: boolean;
      remembers_drink: boolean;
      remembers_sugar: boolean;
      time_ms: number;
    }>;
  };
  stratified_results: StratifiedResults;
  satisfaction?: SatisfactionResults;
  timestamp?: string;
}

const mockData: ExperimentResults = {
  intent_accuracy: {
    accuracy: 37.0,
    total: 200,
    correct: 74,
    bad_cases: [
      { input: "你们有什么优惠？", expected: "query_promotion", actual: "query_menu", confidence: 0.53 },
      { input: "退款", expected: "complaint_refund", actual: "query_refund", confidence: 0.72 },
      { input: "呵呵，你们这服务绝了", expected: "complaint_sarcasm", actual: "general", confidence: 0.30 },
      { input: "那个", expected: "unclear", actual: "general", confidence: 0.15 },
      { input: "上次买的幽兰拿铁这次怎么没了", expected: "query_menu", actual: "query_order", confidence: 0.45 }
    ]
  },
  baseline_comparison: {
    baseline_accuracy: 45.0,
    agent_accuracy: 37.0,
    improvement: -8.0,
    baseline_type: "纯LLM Zero-shot"
  },
  tool_fallback: {
    success_rate: 100.0,
    details: [
      { name: "参数缺失-订单", expected: "ask_user", actual: "ask_user", correct: true },
      { name: "正常-订单", expected: "success", actual: "success", correct: true },
      { name: "订单不存在", expected: "business_error", actual: "business_error", correct: true },
      { name: "参数缺失-库存", expected: "ask_user", actual: "ask_user", correct: true },
      { name: "正常-库存", expected: "success", actual: "success", correct: true },
      { name: "门店不存在", expected: "business_error", actual: "business_error", correct: true },
      { name: "正常-门店", expected: "success", actual: "success", correct: true },
      { name: "参数缺失-投诉", expected: "ask_user", actual: "ask_user", correct: true },
      { name: "正常-投诉", expected: "success", actual: "success", correct: true }
    ]
  },
  memory_window: {
    memory_results: [
      { window_size: 3, message_count: 4, has_summary: true, remembers_drink: true, remembers_sugar: true, time_ms: 0.2 },
      { window_size: 5, message_count: 6, has_summary: true, remembers_drink: true, remembers_sugar: true, time_ms: 0.0 },
      { window_size: 10, message_count: 6, has_summary: false, remembers_drink: true, remembers_sugar: true, time_ms: 0.0 }
    ]
  },
  stratified_results: {
    easy_accuracy: 50.0,
    medium_accuracy: 33.3,
    hard_accuracy: 10.0,
    overall_accuracy: 37.0,
    adversarial_pass_rate: 10.0,
    adversarial_by_type: {
      sarcasm: { correct: 0, total: 8 },
      reference: { correct: 0, total: 12 },
      history_comparison: { correct: 4, total: 4 },
      vague: { correct: 0, total: 4 },
      implied: { correct: 0, total: 4 },
      neutral: { correct: 0, total: 4 },
      implied_complaint: { correct: 0, total: 4 }
    }
  },
  satisfaction: {
    average_score: 3.85,
    satisfaction_rate: 80.0,
    total_samples: 50,
    method: "LLM-as-Judge (glm-4-flash)",
    distribution: {
      "5分": 10,
      "4分": 30,
      "3分": 8,
      "2分": 2,
      "1分": 0
    },
    avg_by_difficulty: {
      easy: 4.2,
      medium: 3.8,
      hard: 3.3
    },
    dimensions: ["problem_solved", "tone_appropriate", "need_followup"]
  },
  timestamp: '2026-06-26'
};

export default function ExperimentReport() {
  const [data, setData] = useState<ExperimentResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setError(null);
    try {
      const res = await fetch('/api/experiment-results');
      if (!res.ok) {
        throw new Error('Failed to fetch experiment results');
      }
      const result = await res.json();
      if (result.error) {
        throw new Error(result.error);
      }
      setData(result);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('无法加载实验数据，显示默认数据');
      setData(mockData);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="animate-pulse">加载实验数据中...</div>
      </div>
    );
  }

  const results = data || mockData;

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-teal-400">BubbleMate 实验报告</h1>
            <p className="text-gray-400 text-sm mt-1">分层评测体系 - 面试核心亮点</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-500">
              更新时间: {results.timestamp || '2026-06-26'} | 测试集: {results.intent_accuracy.total}条
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors"
            >
              {refreshing ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  刷新中...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  刷新数据
                </span>
              )}
            </button>
          </div>
        </div>
        {error && (
          <div className="max-w-7xl mx-auto mt-2 text-sm text-yellow-400 bg-yellow-900/20 px-4 py-2 rounded">
            ⚠️ {error}
          </div>
        )}
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* 核心指标卡片 */}
        <section className="grid grid-cols-4 gap-4">
          <MetricCard
            title="意图识别准确率"
            value={`${results.intent_accuracy.accuracy}%`}
            subtitle={`${results.intent_accuracy.correct}/${results.intent_accuracy.total} cases`}
            color="green"
          />
          <MetricCard
            title="Agent vs Baseline"
            value={`+${results.baseline_comparison.improvement}%`}
            subtitle={`${results.baseline_comparison.baseline_accuracy}% → ${results.baseline_comparison.agent_accuracy}%`}
            color="blue"
          />
          <MetricCard
            title="工具调用成功率"
            value={`${results.tool_fallback.success_rate}%`}
            subtitle="9异常场景测试"
            color="purple"
          />
          <MetricCard
            title="对抗样本通过率"
            value={`${results.stratified_results.adversarial_pass_rate}%`}
            subtitle="40条对抗样本"
            color="red"
          />
        </section>

        {/* 实验1: 意图识别 */}
        <section className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center text-sm">1</span>
            实验1：意图识别准确率
          </h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="text-gray-400 text-sm mb-2">准确率分布</h3>
              <div className="bg-gray-700 rounded-lg p-4">
                <div className="flex items-end gap-2 h-32">
                  <div className="flex-1 bg-green-500 rounded-t" style={{ height: '90%' }}></div>
                  <div className="flex-1 bg-gray-500 rounded-t" style={{ height: '10%' }}></div>
                </div>
                <div className="flex gap-2 mt-2 text-xs text-gray-400">
                  <span className="flex-1 text-center">正确: {results.intent_accuracy.correct}</span>
                  <span className="flex-1 text-center">错误: {results.intent_accuracy.total - results.intent_accuracy.correct}</span>
                </div>
              </div>
            </div>
            <div>
              <h3 className="text-gray-400 text-sm mb-2">意图类型覆盖</h3>
              <div className="grid grid-cols-3 gap-2 text-sm">
                {['complaint_taste', 'query_recommend', 'query_order', 'query_location', 'query_refund', 'complaint_delivery'].map(intent => (
                  <div key={intent} className="bg-gray-700 px-3 py-2 rounded text-center text-xs">
                    {intent}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* 实验2: 对比基线 */}
        <section className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-sm">2</span>
            实验2：对比基线（Baseline vs 完整Agent）
          </h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-700 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Baseline</div>
              <div className="text-3xl font-bold text-gray-300">{results.baseline_comparison.baseline_accuracy}%</div>
              <div className="text-xs text-gray-500 mt-1">简单关键词匹配</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-4">
              <div className="text-gray-400 text-sm">完整Agent</div>
              <div className="text-3xl font-bold text-green-400">{results.baseline_comparison.agent_accuracy}%</div>
              <div className="text-xs text-gray-500 mt-1">规则+关键词+训练数据</div>
            </div>
            <div className="bg-green-900/30 border border-green-600 rounded-lg p-4">
              <div className="text-green-400 text-sm">提升幅度</div>
              <div className="text-3xl font-bold text-green-400">+{results.baseline_comparison.improvement}%</div>
              <div className="text-xs text-green-300/70 mt-1">关键修复: "门店营业时间"误识别</div>
            </div>
          </div>
        </section>

        {/* 实验3: 工具降级 */}
        <section className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center text-sm">3</span>
            实验3：工具调用异常处理（成功率: {results.tool_fallback.success_rate}%）
          </h2>
          <div className="grid grid-cols-3 gap-2 text-sm">
            {results.tool_fallback.details.map((detail, i) => (
              <div key={i} className={`px-3 py-2 rounded ${detail.correct ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
                <span className={detail.correct ? 'text-green-400' : 'text-red-400'}>
                  {detail.correct ? '✓' : '✗'}
                </span>{' '}
                {detail.name}
              </div>
            ))}
          </div>
        </section>

        {/* 实验4: 记忆窗口 */}
        <section className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-orange-600 rounded-lg flex items-center justify-center text-sm">4</span>
            实验4：记忆窗口对比（选择5轮为最优）
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {results.memory_window.memory_results.map((result) => (
              <div key={result.window_size} className={`rounded-lg p-4 ${result.window_size === 5 ? 'bg-orange-900/30 border border-orange-500' : 'bg-gray-700'}`}>
                <div className="text-lg font-bold">{result.window_size}轮</div>
                <div className="text-2xl font-bold text-orange-400">{result.has_summary ? '✓' : '✗'}</div>
                <div className="text-xs text-gray-400 mt-2">
                  消息: {result.message_count} | 耗时: {result.time_ms}ms
                </div>
                {result.window_size === 5 && (
                  <div className="text-xs text-orange-300 mt-2 bg-orange-900/50 px-2 py-1 rounded">
                    ⭐ 最优选择
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* 实验5: 分层评测 */}
        <section className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-cyan-600 rounded-lg flex items-center justify-center text-sm">5</span>
            实验5：分层评测（Easy/Medium/Hard）
          </h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-green-900/30 border border-green-600 rounded-lg p-4">
              <div className="text-gray-400 text-sm">😊 Easy（直接表达）</div>
              <div className="text-3xl font-bold text-green-400">{results.stratified_results.easy_accuracy}%</div>
              <div className="text-xs text-gray-500 mt-1">100条（50%）</div>
            </div>
            <div className="bg-yellow-900/30 border border-yellow-600 rounded-lg p-4">
              <div className="text-gray-400 text-sm">😐 Medium（复合意图）</div>
              <div className="text-3xl font-bold text-yellow-400">{results.stratified_results.medium_accuracy}%</div>
              <div className="text-xs text-gray-500 mt-1">60条（30%）</div>
            </div>
            <div className="bg-red-900/30 border border-red-600 rounded-lg p-4">
              <div className="text-gray-400 text-sm">😰 Hard（对抗样本）</div>
              <div className="text-3xl font-bold text-red-400">{results.stratified_results.hard_accuracy}%</div>
              <div className="text-xs text-gray-500 mt-1">40条（20%）</div>
            </div>
          </div>
          <div className="mt-4 bg-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-2">分层分析结论</div>
            <ul className="text-xs space-y-1">
              <li className="text-green-400">✓ Easy样本：规则匹配表现良好（50%）</li>
              <li className="text-yellow-400">⚠️ Medium样本：复合意图处理不足（33%）</li>
              <li className="text-red-400">✗ Hard样本：对抗样本极度困难（10%）</li>
            </ul>
          </div>
        </section>

        {/* 实验6: 对抗样本分析 */}
        <section className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center text-sm">6</span>
            实验6：对抗样本分析（通过率: {results.stratified_results.adversarial_pass_rate}%）
          </h2>
          <div className="grid grid-cols-4 gap-3">
            {[
              { name: "讽刺语气", data: results.stratified_results.adversarial_by_type.sarcasm, color: "red" },
              { name: "指代不明", data: results.stratified_results.adversarial_by_type.reference, color: "red" },
              { name: "历史对比", data: results.stratified_results.adversarial_by_type.history_comparison, color: "green" },
              { name: "模糊表达", data: results.stratified_results.adversarial_by_type.vague, color: "red" },
              { name: "隐含表达", data: results.stratified_results.adversarial_by_type.implied, color: "red" },
              { name: "中性表达", data: results.stratified_results.adversarial_by_type.neutral, color: "yellow" },
              { name: "隐含投诉", data: results.stratified_results.adversarial_by_type.implied_complaint, color: "red" },
            ].filter(item => item.data && item.data.total > 0).map((item) => (
              <div key={item.name} className={`rounded-lg p-3 ${item.color === 'green' ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
                <div className="text-xs text-gray-400">{item.name}</div>
                <div className={`text-xl font-bold ${item.color === 'green' ? 'text-green-400' : 'text-red-400'}`}>
                  {item.data.correct}/{item.data.total}
                </div>
                <div className={`text-xs ${item.color === 'green' ? 'text-green-300/70' : 'text-red-300/70'}`}>
                  {Math.round(item.data.correct / item.data.total * 100)}%
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 bg-red-900/20 border border-red-700 rounded-lg p-4">
            <div className="text-sm text-red-400 mb-2">🔴 关键短板</div>
            <ul className="text-xs text-gray-300 space-y-1">
              <li>• 讽刺语气（如"呵呵"）无法识别 → 需要增加情感分析</li>
              <li>• 指代不明（如"那个"）无法解析 → 需要指代消解逻辑</li>
              <li>• 历史对比场景表现良好 → 上下文记忆有效</li>
            </ul>
          </div>
        </section>

        {/* Bad Case 分析 */}
        <section className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center text-sm">!</span>
            Bad Case 根因分析
          </h2>
          <div className="space-y-4">
            {results.intent_accuracy.bad_cases.map((case_, i) => (
              <div key={i} className="bg-gray-700 rounded-lg p-4 border-l-4 border-red-500">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-mono text-sm text-gray-300">输入: &quot;{case_.input}&quot;</div>
                    <div className="flex gap-4 mt-2 text-sm">
                      <span className="text-red-400">预测: {case_.actual}</span>
                      <span className="text-green-400">期望: {case_.expected}</span>
                      <span className="text-gray-400">置信度: {case_.confidence}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-600">
                  <div className="text-sm text-yellow-400">
                    💡 改进方向: {case_.input.includes('呵呵') ? '增加讽刺语气识别（如"呵呵"、"绝了"）' : 
                               case_.input === '那个' ? '增加指代消解逻辑（如"那个"、"上次"）' :
                               case_.input.includes('退款') ? '优化退款意图边界（query_refund vs complaint_refund）' :
                               case_.input.includes('上次') ? '增加历史对比场景的上下文注入' :
                               '增加"优惠"类关键词优先级'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 实验7：用户满意度评测 */}
        {results.satisfaction && (
          <section className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-xl font-semibold mb-4">
              📊 实验7：LLM-as-Judge 模拟用户满意度（满意率: {results.satisfaction.satisfaction_rate}%）
            </h2>
            <p className="text-gray-400 text-sm mb-4">
              由于没有真实Beta用户，用另一个大模型（glm-4-flash）充当模拟用户，从三个维度对回复打分
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <MetricCard
                title="平均满意度"
                value={`${results.satisfaction.average_score} / 5.0`}
                subtitle={`${results.satisfaction.total_samples}条样本`}
                color="green"
              />
              <MetricCard
                title="满意率（≥4分）"
                value={`${results.satisfaction.satisfaction_rate}%`}
                subtitle="用户认可比例"
                color="blue"
              />
              <MetricCard
                title="评测方法"
                value="LLM-as-Judge"
                subtitle={results.satisfaction.method}
                color="purple"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-300 mb-3">📈 分数分布</h3>
                <div className="space-y-2">
                  {Object.entries(results.satisfaction.distribution).map(([score, count]) => {
                    const total = Object.values(results.satisfaction!.distribution).reduce((a, b) => a + b, 0);
                    const pct = total > 0 ? (count / total * 100).toFixed(0) : 0;
                    return (
                      <div key={score} className="flex items-center gap-3">
                        <span className="w-10 text-sm text-gray-400">{score}</span>
                        <div className="flex-1 bg-gray-700 rounded-full h-6 overflow-hidden">
                          <div 
                            className={`h-full ${Number(pct) >= 40 ? 'bg-green-500' : Number(pct) >= 20 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="w-16 text-sm text-gray-400 text-right">{count}条 ({pct}%)</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-300 mb-3">🎯 三个打分维度</h3>
                <div className="space-y-3">
                  {results.satisfaction.dimensions.map((dim, i) => (
                    <div key={dim} className="bg-gray-700/50 rounded-lg p-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-300">
                          {i === 0 ? '问题解决度' : i === 1 ? '语气得体度' : '追问必要性'}
                        </span>
                        <span className="text-xs text-gray-500">1-5分</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {i === 0 ? '用户的问题被有效解决了吗？' : 
                         i === 1 ? '客服语气自然、礼貌、得体吗？' : 
                         '是否需要进一步追问才能解决问题？（反向计分）'}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-600/30 rounded-lg">
                  <p className="text-xs text-yellow-400">
                    ⚠️ 注意：这是模拟评测，非真人数据。完整评测需引入人工盲测（A/B Test）和在线反馈闭环。
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* 面试话术 */}
        <section className="bg-gradient-to-r from-teal-900/50 to-blue-900/50 rounded-xl p-6 border border-teal-500/30">
          <h2 className="text-xl font-semibold mb-4">🎯 面试核心话术</h2>
          <div className="bg-gray-900/50 rounded-lg p-4 font-mono text-sm text-gray-300">
            <p className="mb-2">这是我项目最核心的部分——<span className="text-teal-400">一套完整的7实验评测体系</span>。</p>
            <p className="mb-2">我用200条测试集（含40条对抗样本）做了7个实验：</p>
            <ul className="list-disc list-inside mb-2 ml-4">
              <li>意图识别准确率: <span className="text-green-400">{results.intent_accuracy.accuracy}%</span>（200条）</li>
              <li>分层评测: <span className="text-green-400">Easy 50%</span> / <span className="text-yellow-400">Medium 33%</span> / <span className="text-red-400">Hard 10%</span></li>
              <li>对抗样本通过率: <span className="text-red-400">{results.stratified_results.adversarial_pass_rate}%</span>（40条）</li>
              <li>工具异常处理成功率: <span className="text-green-400">{results.tool_fallback.success_rate}%</span></li>
              <li>记忆窗口最优配置: <span className="text-green-400">5轮</span></li>
              <li>Baseline对比: 纯LLM <span className="text-gray-400">{results.baseline_comparison.baseline_accuracy}%</span></li>
              <li>用户满意度（LLM模拟）: <span className="text-green-400">{results.satisfaction?.satisfaction_rate || 80}%</span></li>
            </ul>
            <p className="text-teal-300">这套评测体系揭示了核心短板——讽刺语气和指代不明的处理。发现问题→分析根因→优化→再验证，这个闭环才是项目真正的价值。</p>
          </div>
        </section>
      </main>
    </div>
  );
}

function MetricCard({ title, value, subtitle, color }: {
  title: string;
  value: string | number;
  subtitle: string;
  color: 'green' | 'blue' | 'purple' | 'orange';
}) {
  const colorMap = {
    green: 'border-green-500 text-green-400',
    blue: 'border-blue-500 text-blue-400',
    purple: 'border-purple-500 text-purple-400',
    orange: 'border-orange-500 text-orange-400',
  };
  
  return (
    <div className={`bg-gray-800 rounded-xl p-4 border-l-4 ${colorMap[color]}`}>
      <div className="text-sm text-gray-400">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{subtitle}</div>
    </div>
  );
}
