'use client';

import Link from 'next/link';
import { useRole } from '@/context/RoleContext';

export default function NavBar() {
  const { role } = useRole();

  const getRoleLabel = () => {
    switch (role) {
      case 'customer': return { text: '顾客', emoji: '👤' };
      case 'admin': return { text: '管理员', emoji: '👤' };
      case 'agent': return { text: '客服', emoji: '👤' };
      default: return { text: '顾客', emoji: '👤' };
    }
  };

  const roleLabel = getRoleLabel();

  const renderShortcuts = () => {
    switch (role) {
      case 'customer':
        return (
          <Link href="/profile">
            <button className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg text-sm">
              我的画像
            </button>
          </Link>
        );
      case 'admin':
        return (
          <>
            <Link href="/admin">
              <button className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg text-sm">
                运营后台
              </button>
            </Link>
            <Link href="/agent-dashboard">
              <button className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg text-sm">
                客服工作台
              </button>
            </Link>
          </>
        );
      case 'agent':
        return (
          <Link href="/agent-dashboard">
            <button className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg text-sm">
              客服工作台
            </button>
          </Link>
        );
      default:
        return null;
    }
  };

  return (
    <nav className="fixed top-0 left-0 right-0 bg-white shadow-sm z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-4">
            <Link href="/">
              <div className="flex items-center gap-2 cursor-pointer">
                <span className="text-2xl">🧋</span>
                <span className="text-lg font-semibold text-gray-800">BubbleMate</span>
              </div>
            </Link>
            <span className="text-sm text-gray-500">
              {roleLabel.emoji} {roleLabel.text}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {renderShortcuts()}
            <Link href="/landing">
              <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">
                切换角色
              </button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}