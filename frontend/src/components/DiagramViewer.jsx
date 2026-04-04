/**
 * DiagramViewer
 * Renders the architecture diagram 100% client-side using @xyflow/react.
 * No iframes, no external URLs — React Flow takes nodes + edges directly.
 *
 * Props:
 *   result: {
 *     react_flow_nodes: ReactFlowNode[],
 *     react_flow_edges: ReactFlowEdge[],
 *     arch_summary: string,
 *     graph_stats: { files_analysed, nodes, edges, hubs, clusters },
 *     processing_time_seconds: number,
 *     warning: string,
 *   }
 *   onReset: () => void
 */
import React, { useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

export default function DiagramViewer({ result, onReset }) {
  const {
    react_flow_nodes = [],
    react_flow_edges = [],
    arch_summary,
    graph_stats,
    processing_time_seconds,
    warning,
  } = result

  // React Flow needs local state so nodes are draggable
  const [nodes, , onNodesChange] = useNodesState(react_flow_nodes)
  const [edges, , onEdgesChange] = useEdgesState(react_flow_edges)

  return (
    <div style={styles.container}>
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Architecture Diagram</h2>
          <p style={styles.subtitle}>
            Analysed in {processing_time_seconds}s ·{' '}
            {graph_stats.files_analysed} files ·{' '}
            {nodes.length} nodes · {edges.length} edges
          </p>
        </div>
        <button onClick={onReset} style={styles.resetBtn}>
          ← New Analysis
        </button>
      </div>

      {/* ── Warning banner ─────────────────────────────────────────── */}
      {warning && (
        <div style={styles.warning} role="alert">⚠️ {warning}</div>
      )}

      {/* ── AI summary ─────────────────────────────────────────────── */}
      {arch_summary && (
        <div style={styles.summaryCard}>
          <h3 style={styles.sectionTitle}>🤖 AI Architecture Summary</h3>
          <p style={styles.summaryText}>{arch_summary}</p>
        </div>
      )}

      {/* ── Stats chips ────────────────────────────────────────────── */}
      <div style={styles.statsRow}>
        <StatChip label="Files Analysed" value={graph_stats.files_analysed} icon="📄" />
        <StatChip label="Graph Nodes"    value={graph_stats.nodes}           icon="🔵" />
        <StatChip label="Edges"          value={graph_stats.edges}           icon="🔗" />
        <StatChip label="Clusters"       value={graph_stats.clusters?.length ?? 0} icon="📦" />
      </div>

      {/* ── Core hubs ──────────────────────────────────────────────── */}
      {graph_stats.hubs?.length > 0 && (
        <div style={styles.hubsCard}>
          <span style={styles.hubsLabel}>Core Hubs:</span>
          {graph_stats.hubs.map((h) => (
            <code key={h} style={styles.hubChip}>{h}</code>
          ))}
        </div>
      )}

      {/* ── React Flow canvas ──────────────────────────────────────── */}
      <div style={styles.flowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-right"
          style={styles.flow}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={16}
            size={1}
            color="#2a3347"
          />
          <Controls
            style={styles.controls}
            showInteractive={false}
          />
          <MiniMap
            style={styles.minimap}
            nodeColor="#4f6ef7"
            maskColor="rgba(13,15,20,0.7)"
          />
        </ReactFlow>
      </div>

      {/* ── Hint ───────────────────────────────────────────────────── */}
      <p style={styles.hint}>
        💡 Drag nodes to rearrange · Scroll to zoom · Drag background to pan
      </p>
    </div>
  )
}

/* ── Sub-component ──────────────────────────────────────────────────────── */
function StatChip({ label, value, icon }) {
  return (
    <div style={styles.statChip}>
      <span style={styles.statIcon}>{icon}</span>
      <div>
        <div style={styles.statValue}>{value}</div>
        <div style={styles.statLabel}>{label}</div>
      </div>
    </div>
  )
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  container: { display: 'flex', flexDirection: 'column', gap: '20px' },
  header: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px',
  },
  title: { fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)' },
  subtitle: { color: 'var(--text-secondary)', fontSize: '13px', marginTop: '4px' },
  resetBtn: {
    padding: '10px 20px',
    background: 'var(--bg-input)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    fontSize: '14px',
  },
  warning: {
    padding: '12px 16px',
    background: 'rgba(246,173,85,0.1)',
    border: '1px solid var(--warning)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--warning)',
    fontSize: '13px',
  },
  summaryCard: {
    padding: '20px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
  },
  sectionTitle: {
    fontSize: '15px', fontWeight: 600,
    color: 'var(--text-primary)', marginBottom: '10px',
  },
  summaryText: { color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.7 },
  statsRow: { display: 'flex', gap: '12px', flexWrap: 'wrap' },
  statChip: {
    flex: '1 1 120px',
    display: 'flex', alignItems: 'center', gap: '12px',
    padding: '14px 16px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
  },
  statIcon: { fontSize: '24px' },
  statValue: { fontSize: '22px', fontWeight: 700, color: 'var(--accent)' },
  statLabel: { fontSize: '12px', color: 'var(--text-muted)' },
  hubsCard: {
    display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px',
    padding: '12px 16px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
  },
  hubsLabel: { color: 'var(--text-secondary)', fontSize: '13px', marginRight: '4px' },
  hubChip: {
    padding: '3px 10px',
    background: 'rgba(79,110,247,0.12)',
    border: '1px solid rgba(79,110,247,0.3)',
    borderRadius: '4px',
    color: 'var(--accent)',
    fontSize: '12px',
    fontFamily: 'var(--font-mono)',
  },
  /* React Flow canvas */
  flowWrapper: {
    height: '560px',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    overflow: 'hidden',
    background: '#0d0f14',
  },
  flow: { width: '100%', height: '100%' },
  controls: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
  },
  minimap: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
  },
  hint: {
    textAlign: 'center',
    color: 'var(--text-muted)',
    fontSize: '12px',
    marginTop: '-8px',
  },
}
