'use client';

interface ThoughtChainPanelProps {
  thought: string;
  isStreaming: boolean;
}

export default function ThoughtChainPanel({ thought, isStreaming }: ThoughtChainPanelProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-800">💭 思考链 (Chain of Thought)</h3>
        {isStreaming && (
          <span className="text-xs text-primary-500 animate-pulse">思考中...</span>
        )}
      </div>
      
      <div className="space-y-2">
        {thought ? (
          <div className="thought-chain">
            <p className="text-sm text-gray-700">{thought}</p>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400 text-sm">
            <p>等待用户输入...</p>
            <p className="text-xs mt-1">Agent会在思考后展示推理过程</p>
          </div>
        )}
      </div>
      
      {/* 说明 */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg text-xs text-gray-500">
        <p className="font-medium mb-1">💡 什么是思考链？</p>
        <p>Chain of Thought展示了Agent的推理过程，让您了解它是如何一步步得出结论的。这是大模型应用层的核心调试手段。</p>
      </div>
    </div>
  );
}