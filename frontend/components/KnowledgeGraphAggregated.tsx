'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';

interface GraphNode {
  id: string;
  name: string;
  type: 'complaint' | 'issue' | 'solution' | 'compensation';
  content: string;
  children?: GraphNode[];
  complaint_count?: number;
  original_id?: number;
}

interface GraphLink {
  source: string;
  target: string;
}

interface KnowledgeGraphAggregatedProps {
  nodes: GraphNode[];
  links: GraphLink[];
  onNodeClick: (node: GraphNode | null) => void;
}

const NODE_COLORS: Record<string, string> = {
  complaint: '#FF6B6B',
  issue: '#FFA94D',
  compensation: '#FFE66D',
  solution: '#4ECDC4',
};

const MAX_NODES_FOR_RENDER = 100;
const AGGREGATION_THRESHOLD = 50;

function debounce<T extends (...args: any[]) => any>(fn: T, delay: number): T {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return ((...args: Parameters<T>) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  }) as T;
}

function aggregateNodes(nodes: GraphNode[]): GraphNode[] {
  if (nodes.length <= AGGREGATION_THRESHOLD) return nodes;
  
  const complaintMap = new Map<string, GraphNode[]>();
  nodes.forEach(node => {
    if (node.type === 'complaint') {
      complaintMap.set(node.id, [node]);
    } else {
      const parentComplaint = nodes.find(n => n.type === 'complaint' && 
        node.id.startsWith(n.id.split('_')[0]));
      if (parentComplaint) {
        const existing = complaintMap.get(parentComplaint.id) || [];
        complaintMap.set(parentComplaint.id, [...existing, node]);
      }
    }
  });
  
  return Array.from(complaintMap.values()).map((group, idx) => {
    const complaint = group.find(n => n.type === 'complaint');
    const count = group.length - 1;
    return {
      ...complaint!,
      id: `agg_${idx}`,
      name: complaint ? `${complaint.name} (${count}项)` : `组${idx + 1}`,
      content: `包含${count}个子节点`,
      children: [],
      complaint_count: complaint?.complaint_count || count,
    };
  });
}

export default function KnowledgeGraphAggregated({ nodes, onNodeClick }: KnowledgeGraphAggregatedProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const [renderedNodes, setRenderedNodes] = useState<GraphNode[]>([]);
  const [showAggregation, setShowAggregation] = useState(false);

  useEffect(() => {
    return () => {
      if (tooltipRef.current) {
        tooltipRef.current.remove();
        tooltipRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (nodes.length > AGGREGATION_THRESHOLD) {
      setShowAggregation(true);
      setRenderedNodes(aggregateNodes(nodes));
    } else {
      setShowAggregation(false);
      setRenderedNodes(nodes);
    }
  }, [nodes]);

  const renderGraph = useCallback(debounce(() => {
    if (!svgRef.current || renderedNodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const container = svg.append('g')
      .attr('transform', 'translate(50, 30)');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 2])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);

    const rootData = { id: 'root', name: '', type: 'complaint' as GraphNode['type'], content: '', children: renderedNodes };

    const hierarchy = d3.hierarchy<GraphNode>(rootData)
      .sort((a, b) => {
        const typeOrder = { complaint: 0, issue: 1, solution: 2, compensation: 3 };
        return typeOrder[a.data.type] - typeOrder[b.data.type];
      });

    const treeLayout = d3.tree<GraphNode>()
      .size([height - 80, width - 100])
      .nodeSize([50, 120]);

    const root = treeLayout(hierarchy);

    const linkGroup = container.selectAll('g.links')
      .data([null])
      .join('g')
      .attr('class', 'links');

    linkGroup.selectAll('path')
      .data(root.links())
      .join(
        enter => enter.append('path')
          .attr('d', (d) => {
            const sourceX = d.source.x ?? 0;
            const sourceY = d.source.y ?? 0;
            const targetX = d.target.x ?? 0;
            const targetY = d.target.y ?? 0;
            const midX = (sourceX + targetX) / 2;
            return `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`;
          })
          .attr('stroke', '#9CA3AF')
          .attr('stroke-width', 2)
          .attr('fill', 'none'),
        update => update.attr('d', (d) => {
          const sourceX = d.source.x ?? 0;
          const sourceY = d.source.y ?? 0;
          const targetX = d.target.x ?? 0;
          const targetY = d.target.y ?? 0;
          const midX = (sourceX + targetX) / 2;
          return `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`;
        }),
        exit => exit.remove()
      );

    const nodeGroup = container.selectAll('g.nodes')
      .data([null])
      .join('g')
      .attr('class', 'nodes');

    const nodes = nodeGroup.selectAll<SVGGElement, d3.HierarchyNode<GraphNode>>('g.node')
      .data(root.descendants());

    nodes.exit().remove();

    const newNodes = nodes.enter().append<SVGGElement>('g')
      .attr('class', 'node')
      .style('cursor', 'pointer');

    const allNodes = newNodes.merge(nodes as any);

    allNodes.attr('transform', (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`);

    newNodes.each(function(d) {
      const node = d.data as GraphNode;
      if (node.id === 'root') return;
      const group = d3.select(this);
      const color = NODE_COLORS[node.type];
      
      if (node.type === 'complaint') {
        group.append('polygon')
          .attr('points', '0,-28 24,-14 24,14 0,28 -24,14 -24,-14')
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      } else if (node.type === 'issue') {
        group.append('rect')
          .attr('width', 56)
          .attr('height', 32)
          .attr('x', -28)
          .attr('y', -16)
          .attr('rx', 8)
          .attr('ry', 8)
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      } else if (node.type === 'solution') {
        group.append('circle')
          .attr('r', 20)
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      } else {
        group.append('polygon')
          .attr('points', '0,-22 22,0 0,22 -22,0')
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      }

      group.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('fill', '#fff')
        .attr('font-size', '11px')
        .attr('font-weight', '500')
        .attr('pointer-events', 'none')
        .text(node.id === 'root' ? '' : (node.name.length > 7 ? node.name.slice(0, 7) + '..' : node.name));
    });

    nodeGroup.selectAll<SVGGElement, d3.HierarchyNode<GraphNode>>('g.node')
      .on('mouseenter', function(event, d) {
        const node = d.data as GraphNode;
        if (node.id === 'root') return;
        
        if (!tooltipRef.current) {
          tooltipRef.current = document.createElement('div');
          tooltipRef.current.className = 'fixed pointer-events-none z-50 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg text-sm max-w-xs';
          document.body.appendChild(tooltipRef.current);
        }
        
        const typeLabel = node.type === 'complaint' ? '投诉类型' : node.type === 'issue' ? '具体问题' : node.type === 'solution' ? '解决方案' : '补偿策略';
        tooltipRef.current.innerHTML = `
          <div class="font-semibold text-gray-100">${node.name}</div>
          <div class="text-gray-400 text-xs mt-1">类型: ${typeLabel}</div>
          <div class="text-gray-300 mt-2">${node.content}</div>
          ${node.complaint_count ? `<div class="text-gray-400 text-xs mt-2">关联投诉: ${node.complaint_count}条</div>` : ''}
        `;
        tooltipRef.current.style.opacity = '1';
        tooltipRef.current.style.left = (event.pageX + 10) + 'px';
        tooltipRef.current.style.top = (event.pageY + 10) + 'px';
      })
      .on('mouseleave', function() {
        if (tooltipRef.current) {
          tooltipRef.current.style.opacity = '0';
        }
      })
      .on('click', function(_, d) {
        const node = d.data as GraphNode;
        if (node.id !== 'root') {
          onNodeClick(node);
        }
      });
  }, 100), [renderedNodes, onNodeClick]);

  useEffect(() => {
    const rafId = requestAnimationFrame(renderGraph);
    return () => cancelAnimationFrame(rafId);
  }, [renderGraph]);

  if (nodes.length > MAX_NODES_FOR_RENDER) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-gray-500">
        <div className="text-4xl mb-4">📊</div>
        <div className="text-lg font-medium">节点数量过多</div>
        <div className="text-sm mt-2">当前节点数: {nodes.length}，超过最大渲染限制</div>
        <div className="text-sm mt-1">请使用搜索功能筛选特定节点</div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-400">
        暂无数据
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      {showAggregation && (
        <div className="absolute top-2 left-2 px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium z-10">
          已启用节点聚合（{nodes.length} → {renderedNodes.length}）
        </div>
      )}
      <svg
        ref={svgRef}
        className="w-full h-full"
        style={{ backgroundColor: '#fff' }}
      />
    </div>
  );
}