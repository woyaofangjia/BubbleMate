import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const status = searchParams.get('status');
  try {
    const url = status ? `${BACKEND_URL}/api/admin/candidates?status=${status}` : `${BACKEND_URL}/api/admin/candidates`;
    const response = await fetch(url, { cache: 'no-store' });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ candidates: [] });
  }
}