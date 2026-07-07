'use client';

import Link from 'next/link';

export default function Header() {
  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
            <span className="text-white text-xl">🧋</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">BubbleMate</h1>
            <p className="text-xs text-gray-500">智能奶茶店客服Agent</p>
          </div>
        </Link>
        
        {/* 状态指示 */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span className="text-sm text-gray-600">在线</span>
          </div>
          
          {/* 快捷入口 */}
          <nav className="flex gap-2">
            <Link href="/profile" className="px-3 py-1 rounded-lg text-sm text-gray-600 hover:bg-gray-100">
              我的画像
            </Link>
            <Link href="/experiment-report" className="px-3 py-1 rounded-lg text-sm text-gray-600 hover:bg-gray-100">
              实验报告
            </Link>
            <Link href="/human-support" className="px-3 py-1 rounded-lg text-sm bg-red-50 text-red-600 hover:bg-red-100">
              人工客服
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}