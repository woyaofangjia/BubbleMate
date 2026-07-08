'use client';

import { useEffect, useRef } from 'react';
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

const NODE_SHAPES: Record<string, (group: d3.Selection<any, any, any, any>, color: string) => void> = {
  complaint: (group, color) => {
    group.append('polygon')
      .attr('points', '0,-28 24,-14 24,14 0,28 -24,14 -24,-14')
      .attr('fill', color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);
  },
  issue: (group, color) => {
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
  },
  solution: (group, color) => {
    group.append('circle')
      .attr('r', 20)
      .attr('fill', color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);
  },
  compensation: (group, color) => {
    group.append('polygon')
      .attr('points', '0,-22 22,0 0,22 -22,0')
      .attr('fill', color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);
  },
};

export default function KnowledgeGraphAggregated({ nodes, onNodeClick }: KnowledgeGraphAggregatedProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

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

    const rootData = { id: 'root', name: '', type: 'complaint' as GraphNode['type'], content: '', children: nodes };

    const hierarchy = d3.hierarchy<GraphNode>(rootData)
      .sort((a, b) => {
        const typeOrder = { complaint: 0, issue: 1, solution: 2, compensation: 3 };
        return typeOrder[a.data.type] - typeOrder[b.data.type];
      });

    const treeLayout = d3.tree<GraphNode>()
      .size([height - 80, width - 100])
      .nodeSize([50, 120]);

    const root = treeLayout(hierarchy);

    container.append('g')
      .selectAll('path')
      .data(root.links())
      .join('path')
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
      .attr('fill', 'none');

    const nodeGroup = container.append('g')
      .selectAll('g')
      .data(root.descendants())
      .join('g')
      .attr('transform', (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`)
      .style('cursor', 'pointer');

    nodeGroup.each(function(d) {
      const node = d.data as GraphNode;
      if (node.id === 'root') return;
      const group = d3.select(this);
      const color = NODE_COLORS[node.type];
      const drawShape = NODE_SHAPES[node.type];
      drawShape(group, color);
    });

    nodeGroup.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', '#fff')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .attr('pointer-events', 'none')
      .text((d) => {
        const node = d.data as GraphNode;
        if (node.id === 'root') return '';
        return node.name.length > 7 ? node.name.slice(0, 7) + '..' : node.name;
      });

    const tooltip = d3.select('body')
      .append('div')
      .attr('class', 'fixed pointer-events-none z-50 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg text-sm max-w-xs')
      .style('opacity', 0);

    nodeGroup.on('mouseover', function(event, d) {
      const node = d.data as GraphNode;
      if (node.id === 'root') return;
      tooltip.transition().duration(200).style('opacity', 1);
      const typeLabel = node.type === 'complaint' ? '投诉类型' : node.type === 'issue' ? '具体问题' : node.type === 'solution' ? '解决方案' : '补偿策略';
      tooltip.html(`
        <div class="font-semibold text-gray-100">${node.name}</div>
        <div class="text-gray-400 text-xs mt-1">类型: ${typeLabel}</div>
        <div class="text-gray-300 mt-2">${node.content}</div>
        ${node.complaint_count ? `<div class="text-gray-400 text-xs mt-2">关联投诉: ${node.complaint_count}条</div>` : ''}
      `)
      .style('left', (event.pageX + 10) + 'px')
      .style('top', (event.pageY + 10) + 'px');
    })
    .on('mousemove', function(event) {
      tooltip.style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY + 10) + 'px');
    })
    .on('mouseout', function() {
      tooltip.transition().duration(200).style('opacity', 0);
    })
    .on('click', function(_, d) {
      const node = d.data as GraphNode;
      if (node.id !== 'root') {
        onNodeClick(node);
      }
    });

    return () => {
      tooltip.remove();
    };
  }, [nodes, onNodeClick]);

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      style={{ backgroundColor: '#fff' }}
    />
  );
}