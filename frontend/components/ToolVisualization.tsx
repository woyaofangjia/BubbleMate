'use client';

interface ToolVisualizationProps {
  tools: Array<{ name: string; status: string }>;
  isStreaming: boolean;
}

const toolIcons: Record<string, string> = {
  query_order_status: '📦',
  check_inventory: '📊',
  query_shop_info: '📍',
  query_menu_info: '📋',
  handle_complaint: '🛠️',
};

const toolNames: Record<string, string> = {
  query_order_status: '订单查询',
  check_inventory: '库存查询',
  query_shop_info: '门店查询',
  query_menu_info: '菜单查询',
  handle_complaint: '投诉处理',
};

export default function ToolVisualization({ tools, isStreaming }: ToolVisualizationProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex-1">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-800">🔧 工具调用</h3>
        {isStreaming && (
          <span className="text-xs text-primary-500 animate-pulse">调用中...</span>
        )}
      </div>
      
      {/* 工具列表 */}
      <div className="space-y-2">
        {tools.length > 0 ? (
          tools.map((tool, idx) => (
            <div key={idx} className={`tool-card ${tool.status === 'active' ? 'tool-card-active' : ''}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{toolIcons[tool.name] || '⚙️'}</span>
                  <div>
                    <span className="font-medium text-gray-800">{toolNames[tool.name] || tool.name}</span>
                    <p className="text-xs text-gray-500">{tool.name}</p>
                  </div>
                </div>
                <span className={`text-sm ${tool.status === 'completed' ? 'text-green-500' : 'text-primary-500 animate-pulse'}`}>
                  {tool.status === 'completed' ? '✓ 完成' : '● 运行中'}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-gray-400 text-sm">
            <p>暂无工具调用</p>
            <p className="text-xs mt-1">Agent会根据需求调用相应工具</p>
          </div>
        )}
      </div>
      
      {/* 可用工具列表 */}
      <div className="mt-4">
        <p className="text-xs font-medium text-gray-600 mb-2">可用工具库：</p>
        <div className="grid grid-cols-2 gap-1">
          {Object.entries(toolNames).map(([key, name]) => (
            <div key={key} className="text-xs text-gray-500 flex items-center gap-1">
              <span>{toolIcons[key]}</span>
              <span>{name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}