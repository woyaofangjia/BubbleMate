import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const dynamic = 'force-dynamic';

export async function POST() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/identity`, { method: 'POST' });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: '身份服务不可用' }, { status: 502 });
  }
}
