'use client';

import { useState } from 'react';

interface PasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (password: string) => void;
  title: string;
}

const ADMIN_KEY = 'bubble2026';

export default function PasswordModal({ isOpen, onClose, onConfirm, title }: PasswordModalProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    if (password === ADMIN_KEY) {
      setError('');
      onConfirm(password);
      setPassword('');
    } else {
      setError('密码错误，请重试');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-2xl">🔐</span>
          <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
        </div>
        <div className="space-y-4">
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(''); }}
              onKeyDown={handleKeyDown}
              placeholder="请输入管理密码"
              className={`w-full px-4 py-3 border rounded-lg text-sm focus:outline-none focus:ring-2 ${
                error ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
              }`}
              autoFocus
            />
            {error && (
              <p className="text-red-500 text-sm mt-2">{error}</p>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => { onClose(); setPassword(''); setError(''); }}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
            >
              确认
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}