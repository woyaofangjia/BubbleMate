import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/stats`, {
      method: 'GET',
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ by_type: [], today_count: 0, resolved_count: 0, total_count: 0 });
  }
}