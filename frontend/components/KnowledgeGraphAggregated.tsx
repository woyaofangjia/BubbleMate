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

export default function KnowledgeGraphAggregated({ nodes, links, onNodeClick }: KnowledgeGraphAggregatedProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const container = svg.append('g')
      .attr('transform', `translate(${width / 2}, ${height / 2})`);

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 2])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);

    const rootData = { id: 'root', name: 'root', type: 'complaint' as const, content: 'root', children: nodes };

    const hierarchy = d3.hierarchy(rootData)
      .sort((a, b) => {
        const aType = (a.data as GraphNode).type;
        const bType = (b.data as GraphNode).type;
        return aType === 'complaint' ? -1 : 0;
      });

    const treeLayout = d3.tree()
      .size([width, height - 100])
      .nodeSize([100, 150]);

    const root = treeLayout(hierarchy);

    const linkGenerator = d3.linkHorizontal<d3.HierarchyNode<GraphNode>>()
      .x((d) => (d.x ?? 0) as number)
      .y((d) => (d.y ?? 0) as number);

    container.append('g')
      .selectAll('path')
      .data(root.links())
      .join('path')
      .attr('d', linkGenerator as unknown as d3.LinkHorizontal<d3.HierarchyNode<GraphNode>>)
      .attr('stroke', '#ddd')
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

      if (node.type === 'complaint') {
        group.append('polygon')
          .attr('points', '0,-30 26,-15 26,15 0,30 -26,15 -26,-15')
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      } else if (node.type === 'issue') {
        group.append('rect')
          .attr('width', 60)
          .attr('height', 36)
          .attr('x', -30)
          .attr('y', -18)
          .attr('rx', 8)
          .attr('ry', 8)
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      } else if (node.type === 'solution') {
        group.append('circle')
          .attr('r', 22)
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      } else if (node.type === 'compensation') {
        group.append('polygon')
          .attr('points', '0,-25 25,0 0,25 -25,0')
          .attr('fill', color)
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);
      }
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
        return node.name.length > 8 ? node.name.slice(0, 8) + '..' : node.name;
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
  }, [nodes, links, onNodeClick]);

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      style={{ backgroundColor: '#fff' }}
    />
  );
}