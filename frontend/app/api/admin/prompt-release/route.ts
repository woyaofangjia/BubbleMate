import { NextRequest, NextResponse } from 'next/server';
import { forwardAuth } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

async function proxy(request: NextRequest, method: 'GET' | 'POST') {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/prompt-release`, {
      method,
      headers: { 'Cache-Control': 'no-store', ...forwardAuth(request) },
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json({ error: 'Prompt 发布服务不可用' }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  return proxy(request, 'GET');
}

export async function POST(request: NextRequest) {
  return proxy(request, 'POST');
}
