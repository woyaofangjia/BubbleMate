import { NextRequest } from 'next/server';

/**
 * 流式聊天代理 - 透传后端 SSE 响应。
 * 后端：POST http://localhost:8000/chat/stream (text/event-stream)
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const backendRes = await fetch(`${BACKEND_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!backendRes.ok || !backendRes.body) {
      return new Response(
        JSON.stringify({ error: '后端流式服务不可用' }),
        { status: 502, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // 直接透传 ReadableStream，保持 SSE 协议
    return new Response(backendRes.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    return new Response(
      JSON.stringify({ error: '服务暂时不可用' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
