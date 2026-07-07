import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(_request: Request, { params }: { params: { session_id: string } }) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/takeover/${params.session_id}`, {
      method: 'POST',
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ success: false });
  }
}