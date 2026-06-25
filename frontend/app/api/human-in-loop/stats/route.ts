import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/human-in-loop/stats`);
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({
      total_interventions: 0,
      resolved: 0,
      pending: 0,
      resolution_rate: 0,
      avg_resolution_time: 0
    }, { status: 500 });
  }
}