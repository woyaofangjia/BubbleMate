'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const ADMIN_KEY = 'bubble2026';

interface Complaint {
  id: number;
  user_id: string;
  complaint_type: string;
  description: string;
  resolved: number;
  created_at: string;
}

interface Knowledge {
  id: number;
  complaint_type: string;
  solution: string;
  compensation: string;
  reviewed: number;
  created_at: string;
}

interface Stats {
  by_type: { complaint_type: string; count: number }[];
  today_count: number;
  resolved_count: number;
  total_count: number;
}

export default function AdminPage() {
  const [password, setPassword] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [error, setError] = useState('');
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [knowledge, setKnowledge] = useState<Knowledge[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);

  const handleLogin = () => {
    if (password === ADMIN_KEY) {
      setLoggedIn(true);
      setError('');
      loadData();
    } else {
      setError('密码错误');
    }
  };

  const loadData = () => {
    fetch('/api/admin/complaints')
      .then(res => res.json())
      .then(data => setComplaints(data.complaints || []));

    fetch('/api/admin/knowledge')
      .then(res => res.json())
      .then(data => setKnowledge(data.knowledge || []));

    fetch('/api/admin/stats')
      .then(res => res.json())
      .then(data => setStats(data));
  };

  const handleReview = (id: number) => {
    fetch('/api/admin/knowledge/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then(() => loadData());
  };

  const handleDelete = (id: number) => {
    fetch(`/api/admin/knowledge/${id}`, { method: 'DELETE' })
      .then(() => loadData());
  };

  const getMaxCount = () => {
    if (!stats) return 1;
    return Math.max(...stats.by_type.map(t => t.count), 1);
  };

  if (!loggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white rounded-xl p-8 shadow-lg w-full max-w-md">
          <h1 className="text-2xl font-bold text-center mb-6">运营后台</h1>
          <div className="mb-4">
            <label className="block text-gray-700 mb-2">请输入密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary-500"
              placeholder="输入密码..."
            />
          </div>
          {error && <div className="text-red-500 mb-4">{error}</div>}
          <button
            onClick={handleLogin}
            className="w-full py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            登录
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold">运营后台</h1>
            <nav className="flex gap-4">
              <Link href="/agent-dashboard" className="text-gray-600 hover:text-primary-500">
                客服工作台
              </Link>
              <Link href="/" className="text-gray-600 hover:text-primary-500">
                返回首页
              </Link>
            </nav>
          </div>
          <div className="text-sm text-gray-500">管理员</div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">今日新增投诉</div>
            <div className="text-3xl font-bold text-red-500">{stats?.today_count || 0}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">总投诉数</div>
            <div className="text-3xl font-bold text-gray-800">{stats?.total_count || 0}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">已解决</div>
            <div className="text-3xl font-bold text-green-500">{stats?.resolved_count || 0}</div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 border border-gray-200 mb-6">
          <h2 className="text-lg font-semibold mb-4">📊 投诉类型分布</h2>
          <div className="space-y-3">
            {stats?.by_type.map((item, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className="w-32 text-sm text-gray-600 truncate">{item.complaint_type}</div>
                <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full transition-all"
                    style={{ width: `${(item.count / getMaxCount()) * 100}%` }}
                  />
                </div>
                <div className="w-12 text-sm font-medium text-gray-800">{item.count}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <h2 className="text-lg font-semibold mb-4">📝 最近投诉</h2>
            <div className="space-y-3">
              {complaints.slice(0, 10).map(c => (
                <div key={c.id} className="border border-gray-100 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-gray-800">{c.complaint_type}</span>
                    <span className={`text-xs px-2 py-1 rounded ${c.resolved ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {c.resolved ? '已解决' : '待处理'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mb-2">{c.description}</div>
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>用户: {c.user_id}</span>
                    <span>{c.created_at}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <h2 className="text-lg font-semibold mb-4">📚 知识图谱</h2>
            <div className="space-y-3">
              {knowledge.map(k => (
                <div key={k.id} className="border border-gray-100 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-gray-800">{k.complaint_type}</span>
                    <span className={`text-xs px-2 py-1 rounded ${k.reviewed ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>
                      {k.reviewed ? '已审核' : '待审核'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mb-1">解决方案: {k.solution}</div>
                  <div className="text-sm text-gray-600 mb-3">补偿策略: {k.compensation}</div>
                  <div className="flex gap-2">
                    {!k.reviewed && (
                      <button
                        onClick={() => handleReview(k.id)}
                        className="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600"
                      >
                        审核通过
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(k.id)}
                      className="px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}