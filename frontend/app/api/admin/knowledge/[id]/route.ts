import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function DELETE(_request: Request, { params }: { params: { id: string } }) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/knowledge/${params.id}`, {
      method: 'DELETE',
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ success: false });
  }
}