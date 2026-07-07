import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const knowledge_id = searchParams.get('knowledge_id');
  
  if (!knowledge_id) {
    return NextResponse.json({ complaints: [] });
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/knowledge-complaints?knowledge_id=${knowledge_id}`, {
      cache: 'no-store',
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ complaints: [] });
  }
}