'use client';

import { useState, useEffect } from 'react';

interface PasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (password: string) => void;
  title: string;
}

const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_PASSWORD || 'bubble2026';
const MAX_ATTEMPTS = 3;

export default function PasswordModal({ isOpen, onClose, onConfirm, title }: PasswordModalProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [attempts, setAttempts] = useState(0);
  const [locked, setLocked] = useState(false);
  const [lockTime, setLockTime] = useState(0);

  useEffect(() => {
    if (locked && Date.now() - lockTime >= 60000) {
      setLocked(false);
      setAttempts(0);
    }
  }, [locked, lockTime]);

  useEffect(() => {
    if (isOpen) {
      setPassword('');
      setError('');
    }
  }, [isOpen]);

  const validatePassword = (pwd: string) => {
    if (pwd.length < 6) return '密码长度不能少于6位';
    if (!/[a-zA-Z]/.test(pwd)) return '密码必须包含字母';
    if (!/[0-9]/.test(pwd)) return '密码必须包含数字';
    return null;
  };

  const handleSubmit = () => {
    if (locked) {
      const remaining = Math.ceil((60000 - (Date.now() - lockTime)) / 1000);
      setError(`账户已锁定，请${remaining}秒后再试`);
      return;
    }

    const validationError = validatePassword(password);
    if (validationError) {
      setError(validationError);
      return;
    }

    if (password === ADMIN_KEY) {
      setError('');
      setAttempts(0);
      onConfirm(password);
      setPassword('');
    } else {
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);
      if (newAttempts >= MAX_ATTEMPTS) {
        setLocked(true);
        setLockTime(Date.now());
        setError(`连续输错${MAX_ATTEMPTS}次，账户已锁定1分钟`);
      } else {
        setError(`密码错误，还剩${MAX_ATTEMPTS - newAttempts}次机会`);
      }
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
              disabled={locked}
            />
            {error && (
              <p className="text-red-500 text-sm mt-2">{error}</p>
            )}
            {!error && password.length > 0 && (
              <p className="text-gray-400 text-xs mt-2">提示：密码需包含字母和数字，至少6位</p>
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
              disabled={locked || password.length < 6}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              确认
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}