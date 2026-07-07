import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest, { params }: { params: { session_id: string } }) {
  try {
    const body = await request.json();
    const response = await fetch(`${BACKEND_URL}/api/admin/reply/${params.session_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ success: false });
  }
}