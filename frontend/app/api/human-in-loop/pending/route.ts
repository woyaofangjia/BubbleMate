import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/human-in-loop/pending`);
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json([], { status: 500 });
  }
}