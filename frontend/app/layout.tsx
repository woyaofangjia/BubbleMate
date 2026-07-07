import type { Metadata } from 'next';
import './globals.css';
import { RoleProvider } from '@/context/RoleContext';

export const metadata: Metadata = {
  title: 'BubbleMate - 智能奶茶店客服',
  description: '武汉大学周边奶茶店智能客服Agent',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="font-sans antialiased">
        <RoleProvider>{children}</RoleProvider>
      </body>
    </html>
  );
}