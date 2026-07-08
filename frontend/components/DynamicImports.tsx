'use client';

import dynamic from 'next/dynamic';
import LoadingSpinner from './LoadingSpinner';

export const AdminPage = dynamic(
  () => import('@/app/admin/page').then(mod => ({ default: mod.default })),
  {
    loading: () => <LoadingSpinner />,
    ssr: false,
  }
);

export const AgentDashboardPage = dynamic(
  () => import('@/app/agent-dashboard/page').then(mod => ({ default: mod.default })),
  {
    loading: () => <LoadingSpinner />,
    ssr: false,
  }
);

export const ProfilePage = dynamic(
  () => import('@/app/profile/page').then(mod => ({ default: mod.default })),
  {
    loading: () => <LoadingSpinner />,
    ssr: false,
  }
);

export const KnowledgeGraphAggregated = dynamic(
  () => import('@/components/KnowledgeGraphAggregated').then(mod => ({ default: mod.default })),
  {
    loading: () => <div className="flex items-center justify-center h-full text-gray-400">加载图谱中...</div>,
    ssr: false,
  }
);

export const KnowledgeGraphD3 = dynamic(
  () => import('@/components/KnowledgeGraphD3').then(mod => ({ default: mod.default })),
  {
    loading: () => <div className="flex items-center justify-center h-full text-gray-400">加载图谱中...</div>,
    ssr: false,
  }
);