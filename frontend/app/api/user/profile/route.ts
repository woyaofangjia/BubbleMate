import { NextRequest, NextResponse } from 'next/server';
import { forwardAuth } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/user/profile`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...forwardAuth(request),
      },
    });
    
    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: '服务暂时不可用' },
      { status: 500 }
    );
  }
}