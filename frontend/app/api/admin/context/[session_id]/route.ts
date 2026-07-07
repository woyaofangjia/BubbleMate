import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(_request: Request, { params }: { params: { session_id: string } }) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/context/${params.session_id}`, {
      method: 'GET',
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: '查询失败' });
  }
}