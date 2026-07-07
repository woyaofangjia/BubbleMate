'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';

interface Preferences {
  sugar?: string;
  ice?: string;
}

interface Order {
  order_id: string;
  store: string;
  items: string[];
  total: number;
  status: string;
  create_time: string;
}

interface Complaint {
  complaint_id: string;
  complaint: string;
  severity: string;
  category: string;
  time: number;
}

interface ProfileData {
  user_id: string;
  preferences: Preferences;
  stats: {
    total_complaints: number;
    total_feedback: number;
    total_orders: number;
  };
  complaints: Complaint[];
  recent_orders: Order[];
}

const getSessionId = () => {
  let sessionId = localStorage.getItem('bubblemate_session_id');
  if (!sessionId) {
    sessionId = 'default';
    localStorage.setItem('bubblemate_session_id', sessionId);
  }
  return sessionId;
};

const defaultProfile: ProfileData = {
  user_id: '',
  preferences: {},
  stats: { total_complaints: 0, total_feedback: 0, total_orders: 0 },
  complaints: [],
  recent_orders: [],
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData>(defaultProfile);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const sessionId = getSessionId();
    
    fetch(`/api/user/profile?session_id=${sessionId}`)
      .then(res => res.json())
      .then(data => {
        setProfile({ ...defaultProfile, ...data });
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError('加载失败');
        setLoading(false);
      });
  }, []);

  const getStatusColor = (status: string) => {
    if (status.includes('已完成')) return 'bg-green-100 text-green-700';
    if (status.includes('配送中')) return 'bg-blue-100 text-blue-700';
    if (status.includes('待配送')) return 'bg-yellow-100 text-yellow-700';
    return 'bg-gray-100 text-gray-700';
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-pulse text-gray-500">加载中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 p-4 max-w-5xl mx-auto w-full">
        <div className="flex items-center gap-4 mb-6">
          <Link href="/" className="text-gray-500 hover:text-gray-700">
            ← 返回聊天
          </Link>
          <h1 className="text-2xl font-bold text-gray-800">我的画像</h1>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">总订单数</div>
            <div className="text-3xl font-bold text-primary-500">{profile.stats.total_orders}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">投诉次数</div>
            <div className="text-3xl font-bold text-red-500">{profile.stats.total_complaints}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">反馈次数</div>
            <div className="text-3xl font-bold text-blue-500">{profile.stats.total_feedback}</div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 border border-gray-200 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">🍵 口味偏好</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                <span className="text-lg">🍯</span>
              </div>
              <div>
                <div className="text-sm text-gray-500">糖度</div>
                <div className="font-medium text-gray-800">
                  {profile.preferences?.sugar || '未设置'}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                <span className="text-lg">🧊</span>
              </div>
              <div>
                <div className="text-sm text-gray-500">冰量</div>
                <div className="font-medium text-gray-800">
                  {profile.preferences?.ice || '未设置'}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 border border-gray-200 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📋 最近订单</h2>
          {profile.recent_orders?.length > 0 ? (
            <div className="space-y-3">
              {profile.recent_orders.map(order => (
                <div key={order.order_id} className="border border-gray-100 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-gray-800">{order.order_id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs ${getStatusColor(order.status)}`}>
                      {order.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mb-1">{order.store}</div>
                  <div className="text-sm text-gray-600">{order.items?.join(', ')}</div>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs text-gray-400">{order.create_time}</span>
                    <span className="font-medium text-primary-500">¥{order.total}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-400 text-center py-8">暂无订单记录</div>
          )}
        </div>

        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📝 投诉记录</h2>
          {profile.complaints?.length > 0 ? (
            <div className="space-y-3">
              {profile.complaints.map(complaint => (
                <div key={complaint.complaint_id} className="border border-gray-100 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-gray-800">{complaint.complaint_id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs ${complaint.severity === '严重' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>
                      {complaint.severity}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mb-1">{complaint.complaint}</div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-400">分类: {complaint.category}</span>
                    <span className="text-xs text-gray-400">{complaint.time ? formatDate(complaint.time) : ''}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-400 text-center py-8">暂无投诉记录</div>
          )}
        </div>
      </main>
    </div>
  );
}