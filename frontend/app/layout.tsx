import type { Metadata } from 'next';
import './globals.css';

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
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}