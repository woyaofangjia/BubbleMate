'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRole } from '@/context/RoleContext';
import PasswordModal from '@/components/PasswordModal';

export default function LandingPage() {
  const router = useRouter();
  const { setRole, setAdminVerified, setAgentVerified } = useRole();
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [targetRole, setTargetRole] = useState<'admin' | 'agent'>('admin');
  const [targetPath, setTargetPath] = useState('');

  const handleCustomerClick = () => {
    setRole('customer');
    router.push('/');
  };

  const handleAdminClick = () => {
    setModalTitle('🔐 管理员验证');
    setTargetRole('admin');
    setTargetPath('/admin');
    setModalOpen(true);
  };

  const handleAgentClick = () => {
    setModalTitle('🔐 客服验证');
    setTargetRole('agent');
    setTargetPath('/agent-dashboard');
    setModalOpen(true);
  };

  const handlePasswordConfirm = () => {
    if (targetRole === 'admin') {
      setAdminVerified(true);
    } else {
      setAgentVerified(true);
    }
    setRole(targetRole);
    setModalOpen(false);
    router.push(targetPath);
  };

  const cards = [
    {
      emoji: '🍵',
      title: '我是顾客',
      description: '咨询饮品、查询订单、投诉反馈',
      buttonText: '进入聊天',
      onClick: handleCustomerClick,
      color: 'from-green-50 to-white',
      hoverColor: 'hover:shadow-lg hover:shadow-green-100',
    },
    {
      emoji: '📊',
      title: '运营人员',
      description: '管理投诉、审核知识、查看统计',
      buttonText: '进入后台',
      onClick: handleAdminClick,
      color: 'from-blue-50 to-white',
      hoverColor: 'hover:shadow-lg hover:shadow-blue-100',
    },
    {
      emoji: '🛠️',
      title: '客服人员',
      description: '接管会话、人工回复、处理投诉',
      buttonText: '进入工作台',
      onClick: handleAgentClick,
      color: 'from-purple-50 to-white',
      hoverColor: 'hover:shadow-lg hover:shadow-purple-100',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-pink-50 to-white flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="text-center mb-12">
          <div className="text-6xl mb-4">🧋</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">BubbleMate</h1>
          <p className="text-gray-500">智能奶茶店客服系统</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl w-full">
          {cards.map((card, index) => (
            <div
              key={index}
              className={`bg-gradient-to-br ${card.color} rounded-2xl p-6 border border-gray-100 shadow-sm transition-all duration-300 ${card.hoverColor} cursor-pointer`}
              onClick={card.onClick}
            >
              <div className="text-4xl mb-4">{card.emoji}</div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">{card.title}</h3>
              <p className="text-gray-500 text-sm mb-4">{card.description}</p>
              <button className="w-full py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition-colors text-sm">
                {card.buttonText}
              </button>
            </div>
          ))}
        </div>

        <p className="mt-12 text-gray-400 text-sm">首次访问？选择身份开始使用</p>
      </div>

      <PasswordModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onConfirm={handlePasswordConfirm}
        title={modalTitle}
      />
    </div>
  );
}