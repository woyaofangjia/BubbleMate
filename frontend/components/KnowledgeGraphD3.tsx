'use client';

import { useEffect, useRef, useCallback } from 'react';
import { select, zoom, hierarchy, tree } from 'd3';

interface KnowledgeNode {
  id: number;
  node_type: string;
  content: string;
  reviewed: number;
  parent_id: number | null;
  children: KnowledgeNode[];
}

interface Props {
  data: KnowledgeNode[];
  selectedNode: KnowledgeNode | null;
  onNodeClick: (node: KnowledgeNode | null) => void;
}

const getColor = (type: string) => {
  if (type.includes('complaint') || type.includes('口味') || type.includes('服务') || type.includes('其他')) return '#FF6B6B';
  if (type.includes('solution') || type.includes('解决')) return '#4ECDC4';
  if (type.includes('compensation') || type.includes('补偿')) return '#FFE66D';
  return '#45B7D1';
};

const getNodeWidth = (content: string) => {
  return Math.max(content.length * 10, 60);
};

export default function KnowledgeGraphD3({ data, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  const renderGraph = useCallback(() => {
    if (!data || data.length === 0 || !containerRef.current) return;

    const container = select(containerRef.current);
    if (!container.node()) return;

    container.selectAll('*').remove();

    const width = container.node()?.clientWidth || 800;
    const height = container.node()?.clientHeight || 560;

    if (width === 0 || height === 0) return;

    const svg = container.append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('overflow', 'auto');

    const g = svg.append('g')
      .attr('transform', 'translate(50, 30)');

    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 2])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoomBehavior);

    const idMap = new Map<number, KnowledgeNode>();
    const buildHierarchy = (nodes: KnowledgeNode[]): { name: string; children: any[]; data: KnowledgeNode }[] => {
      const result: any[] = [];
      const nodeMap = new Map<number, any>();

      nodes.forEach(node => {
        idMap.set(node.id, node);
        nodeMap.set(node.id, {
          name: node.content,
          children: [],
          data: node,
        });
      });

      nodes.forEach(node => {
        const item = nodeMap.get(node.id)!;
        if (node.parent_id === null || node.parent_id === undefined) {
          result.push(item);
        } else {
          const parent = nodeMap.get(node.parent_id);
          if (parent) parent.children.push(item);
        }
      });

      return result;
    };

    const hierarchyData = buildHierarchy(data);

    const root = hierarchy({
      name: '投诉',
      children: hierarchyData,
      data: { id: 0, node_type: 'complaint_type', content: '投诉', reviewed: 1, parent_id: null, children: [] } as KnowledgeNode,
    });

    const treeLayout = tree<any>()
      .size([height - 60, width - 100])
      .nodeSize([40, 180]);

    treeLayout(root);

    const links = root.links();
    const linkPaths = links.map(link => {
      const sourceX = link.source.y ?? 0;
      const sourceY = link.source.x ?? 0;
      const targetX = link.target.y ?? 0;
      const targetY = link.target.x ?? 0;
      const midX = (sourceX + targetX) / 2;
      return `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`;
    });

    const linkGroup = g.append('g').attr('class', 'links');
    linkGroup.selectAll('path')
      .data(links)
      .enter().append('path')
      .attr('d', (d, i) => linkPaths[i])
      .style('stroke', '#9CA3AF')
      .style('stroke-width', 2)
      .style('fill', 'none');

    const nodeGroup = g.append('g').attr('class', 'nodes');
    const node = nodeGroup.selectAll<SVGGElement, any>('g')
      .data(root.descendants())
      .enter().append('g')
      .attr('transform', (d: any) => `translate(${d.y}, ${d.x})`)
      .attr('cursor', 'pointer');

    const nodeWidths = new Map<any, number>();

    node.append('rect')
      .attr('x', (d: any) => {
        const w = getNodeWidth(d.data.name);
        nodeWidths.set(d, w);
        return -w / 2;
      })
      .attr('y', -15)
      .attr('width', (d: any) => nodeWidths.get(d) || 60)
      .attr('height', 30)
      .attr('rx', 8)
      .attr('fill', (d: any) => {
        const nodeData = (d.data as any).data || d.data;
        return getColor(nodeData.node_type || '');
      })
      .attr('stroke', (d: any) => {
        const nodeData = (d.data as any).data || d.data;
        return (nodeData.reviewed === 1) ? '#FFD700' : '#9CA3AF';
      })
      .attr('stroke-width', 2);

    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 5)
      .attr('font-size', 12)
      .attr('fill', '#374151')
      .text((d: any) => d.data.name);

    node.filter((d: any): boolean => !!d.children && d.children.length > 0)
      .append('circle')
      .attr('r', 6)
      .attr('cx', (d: any) => (nodeWidths.get(d) || 60) / 2 + 8)
      .attr('cy', 0)
      .attr('fill', '#374151')
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', 10)
      .attr('fill', 'white')
      .text('-');

    const tooltip = select('body').append('div')
      .attr('class', 'd3-tooltip')
      .style('position', 'absolute')
      .style('background', 'rgba(0,0,0,0.8)')
      .style('color', 'white')
      .style('padding', '8px 12px')
      .style('border-radius', '4px')
      .style('font-size', '14px')
      .style('pointer-events', 'none')
      .style('opacity', 0);

    tooltipRef.current = tooltip.node() as HTMLDivElement;

    node.on('mouseenter', function(event: any, d: any) {
      select(this).select('rect').transition().duration(200).attr('rx', 12);
      tooltip.transition().duration(200).style('opacity', 1);
      const nodeData = d.data.data || d.data;
      tooltip.html(`
        <div style="font-weight:bold">${d.data.name}</div>
        <div>状态: ${(nodeData.reviewed === 1) ? '已审核' : '待审核'}</div>
      `).style('left', (event.pageX + 10) + 'px').style('top', (event.pageY - 10) + 'px');
    });

    node.on('mouseleave', function(_: any, d: any) {
      select(this).select('rect').transition().duration(200).attr('rx', 8);
      tooltip.transition().duration(200).style('opacity', 0);
    });

    node.on('click', function(event: any, d: any) {
      event.stopPropagation();
      const nodeData = d.data.data || d.data;
      if (nodeData && nodeData.id !== undefined) {
        const original = idMap.get(nodeData.id);
        if (original) {
          onNodeClick(original);
        }
      }
    });

    return () => {
      tooltip.remove();
      tooltipRef.current = null;
      container.selectAll('*').remove();
    };
  }, [data, onNodeClick]);

  useEffect(() => {
    if (!data || data.length === 0) return;

    let scheduled: number | undefined;
    const scheduleRender = () => {
      if (typeof requestIdleCallback === 'function') {
        scheduled = requestIdleCallback(renderGraph, { timeout: 1000 });
      } else {
        scheduled = window.setTimeout(renderGraph, 100);
      }
    };

    scheduleRender();

    return () => {
      if (scheduled !== undefined) {
        if (typeof requestIdleCallback === 'function') {
          cancelIdleCallback(scheduled);
        } else {
          clearTimeout(scheduled);
        }
      }
      if (tooltipRef.current) {
        tooltipRef.current.remove();
        tooltipRef.current = null;
      }
    };
  }, [data, onNodeClick, renderGraph]);

  return (
    <div ref={containerRef} className="w-full h-full">
      {!data || data.length === 0 ? (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          暂无数据
        </div>
      ) : null}
    </div>
  );
}