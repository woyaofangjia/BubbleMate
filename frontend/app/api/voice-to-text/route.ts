import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const audioFile = formData.get('audio') as File;
    
    if (!audioFile) {
      return NextResponse.json({ error: '未接收到音频文件' }, { status: 400 });
    }

    const backendFormData = new FormData();
    backendFormData.append('audio', audioFile, audioFile.name || 'recording.wav');

    const response = await fetch(`${BACKEND_URL}/voice-to-text`, {
      method: 'POST',
      body: backendFormData,
    });

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('语音转文字路由错误:', error);
    return NextResponse.json(
      { error: '语音识别服务暂时不可用' },
      { status: 500 }
    );
  }
}

export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb',
    },
  },
};
