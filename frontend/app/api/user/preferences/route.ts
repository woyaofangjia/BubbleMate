import { NextRequest, NextResponse } from 'next/server';
import { forwardAuth } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function DELETE(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/user/preferences`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', ...forwardAuth(request) },
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: '服务不可用' }, { status: 502 });
  }
}
