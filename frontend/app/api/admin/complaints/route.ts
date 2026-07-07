import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/complaints`, {
      method: 'GET',
      cache: 'no-store',
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ complaints: [] });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    if (body.action === 'resolve') {
      const response = await fetch(`${BACKEND_URL}/api/admin/complaints/resolve/${body.id}`, {
        method: 'POST',
      });
      const data = await response.json();
      return NextResponse.json(data);
    }
  } catch {}
  return NextResponse.json({ success: false });
}