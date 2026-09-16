"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";

interface GraphNode { id: string; label: string; call_count: number }
interface GraphEdge { source: string; target: string; count: number; deviated: boolean }

/**
 * Deviation from build spec §5.7 (React Flow): this MVP renders the graph
 * as a static circular-layout SVG rather than an interactive/draggable
 * React Flow canvas, to avoid the extra dependency for a v1 — see
 * docs/SCOPE_DECISIONS.md. Node positions, edge counts, and "deviated"
 * highlighting (red, dashed) are all real data from the backend.
 */
export default function GraphPage() {
  const params = useParams<{ sessionId: string }>();
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);

  useEffect(() => {
    api.getGraph(params.sessionId).then((res) => {
      setNodes(res.nodes as GraphNode[]);
      setEdges(res.edges as GraphEdge[]);
    });
  }, [params.sessionId]);

  const size = 480;
  const center = size / 2;
  const radius = size / 2 - 70;

  const positions: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1) - Math.PI / 2;
    positions[n.id] = {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Tool-call graph</h1>
        <p className="text-xs text-muted-foreground mono">session {params.sessionId.slice(0, 8)}</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Observed tool transitions</CardTitle>
        </CardHeader>
        <CardContent>
          {nodes.length === 0 ? (
            <div className="text-sm text-muted-foreground py-12 text-center">
              No tool calls recorded for this session yet.
            </div>
          ) : (
            <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-xl mx-auto">
              <defs>
                <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" fill="hsl(var(--muted-foreground))" />
                </marker>
                <marker id="arrow-red" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" fill="hsl(var(--danger))" />
                </marker>
              </defs>
              {edges.map((e, i) => {
                const s = positions[e.source];
                const t = positions[e.target];
                if (!s || !t) return null;
                return (
                  <g key={i}>
                    <line
                      x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                      stroke={e.deviated ? "hsl(var(--danger))" : "hsl(var(--muted-foreground))"}
                      strokeWidth={Math.min(1 + e.count, 5)}
                      strokeDasharray={e.deviated ? "4 3" : undefined}
                      markerEnd={e.deviated ? "url(#arrow-red)" : "url(#arrow)"}
                      opacity={0.8}
                    />
                    <text
                      x={(s.x + t.x) / 2} y={(s.y + t.y) / 2}
                      fontSize={10} fill="hsl(var(--muted-foreground))" textAnchor="middle"
                    >
                      ×{e.count}
                    </text>
                  </g>
                );
              })}
              {nodes.map((n) => {
                const p = positions[n.id];
                return (
                  <g key={n.id}>
                    <circle cx={p.x} cy={p.y} r={28} fill="hsl(var(--surface))" stroke="hsl(var(--primary))" strokeWidth={2} />
                    <text x={p.x} y={p.y - 2} textAnchor="middle" fontSize={11} fill="hsl(var(--foreground))" fontWeight={600}>
                      {n.label}
                    </text>
                    <text x={p.x} y={p.y + 12} textAnchor="middle" fontSize={9} fill="hsl(var(--muted-foreground))">
                      ×{n.call_count}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
          <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-block w-4 h-0.5 bg-muted-foreground" /> expected transition
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-4 h-0.5 bg-danger" style={{ borderTop: "2px dashed hsl(var(--danger))" }} /> flagged by behavioral anomaly detector
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
