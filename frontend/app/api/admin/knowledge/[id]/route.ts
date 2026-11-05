import { NextRequest, NextResponse } from 'next/server';
import { forwardAuth } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/knowledge/${params.id}`, {
      method: 'DELETE',
      headers: { ...forwardAuth(request) },
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ success: false });
  }
}