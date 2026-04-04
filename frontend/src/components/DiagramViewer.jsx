import React, { useState, useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Handle,
  Position,
  Panel,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Monitor, Server, Database, Zap, Mail,
  Globe, Layers, HardDrive, Box,
} from 'lucide-react'

/* ══════════════════════════════════════════════════════════════════
   LLD — layer config (x-position → colour + label + icon)
═══════════════════════════════════════════════════════════════════ */
const LLD_LAYERS = [
  { minX: 0,    maxX: 175,  color: '#a78bfa', bg: 'rgba(167,139,250,0.12)', label: 'Entry Points',   icon: '⚡' },
  { minX: 176,  maxX: 425,  color: '#60a5fa', bg: 'rgba(96,165,250,0.12)',  label: 'Routes / API',   icon: '🔀' },
  { minX: 426,  maxX: 675,  color: '#34d399', bg: 'rgba(52,211,153,0.12)',  label: 'Services',       icon: '⚙️' },
  { minX: 676,  maxX: 925,  color: '#f59e0b', bg: 'rgba(245,158,11,0.12)',  label: 'Models / Data',  icon: '🗄️' },
  { minX: 926,  maxX: 1175, color: '#f87171', bg: 'rgba(248,113,113,0.12)', label: 'Database / Ext', icon: '🔌' },
  { minX: 1176, maxX: 9999, color: '#94a3b8', bg: 'rgba(148,163,184,0.12)', label: 'Utilities',      icon: '🔧' },
]

function getLldLayer(x = 0) {
  return LLD_LAYERS.find(l => x >= l.minX && x <= l.maxX) || LLD_LAYERS[LLD_LAYERS.length - 1]
}

/* ══════════════════════════════════════════════════════════════════
   HLD — system type config
═══════════════════════════════════════════════════════════════════ */
const HLD_TYPES = {
  client:       { color: '#60a5fa', bg: 'rgba(96,165,250,0.13)',   Icon: Monitor,   label: 'Client' },
  server:       { color: '#a78bfa', bg: 'rgba(167,139,250,0.13)',  Icon: Server,    label: 'Server' },
  service:      { color: '#34d399', bg: 'rgba(52,211,153,0.13)',   Icon: Layers,    label: 'Service' },
  database:     { color: '#f59e0b', bg: 'rgba(245,158,11,0.13)',   Icon: Database,  label: 'Database' },
  cache:        { color: '#f97316', bg: 'rgba(249,115,22,0.13)',   Icon: Zap,       label: 'Cache' },
  queue:        { color: '#e879f9', bg: 'rgba(232,121,249,0.13)',  Icon: Mail,      label: 'Queue' },
  external_api: { color: '#f87171', bg: 'rgba(248,113,113,0.13)', Icon: Globe,     label: 'External API' },
  cdn:          { color: '#94a3b8', bg: 'rgba(148,163,184,0.13)', Icon: HardDrive, label: 'CDN' },
}

function getHldType(systemType) {
  return HLD_TYPES[systemType] || { color: '#94a3b8', bg: 'rgba(148,163,184,0.13)', Icon: Box, label: 'System' }
}

/* ══════════════════════════════════════════════════════════════════
   Custom Nodes
═══════════════════════════════════════════════════════════════════ */

/** LLD Node — coloured by x-position layer */
function LldNode({ data, selected }) {
  const layer = getLldLayer(data.x)
  return (
    <div style={{
      minWidth: 150, maxWidth: 210,
      padding: '10px 14px',
      borderRadius: 10,
      background: layer.bg,
      border: `2px solid ${selected ? '#fff' : layer.color}`,
      boxShadow: selected
        ? `0 0 0 3px ${layer.color}55, 0 4px 20px rgba(0,0,0,0.5)`
        : '0 2px 12px rgba(0,0,0,0.4)',
      cursor: 'grab',
      transition: 'box-shadow 0.15s, border-color 0.15s',
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: layer.color, width: 8, height: 8, border: 'none' }} />
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4,
        fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
        color: layer.color, marginBottom: 6, textTransform: 'uppercase' }}>
        <span>{layer.icon}</span><span>{layer.label}</span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9',
        lineHeight: 1.35, wordBreak: 'break-word' }}>
        {data.label}
      </div>
      <Handle type="source" position={Position.Right}
        style={{ background: layer.color, width: 8, height: 8, border: 'none' }} />
    </div>
  )
}

/** HLD Node — icon + systemType badge + description */
function HldNode({ data, selected }) {
  const cfg = getHldType(data.systemType)
  const { Icon } = cfg
  return (
    <div style={{
      width: 200,
      padding: '16px 18px',
      borderRadius: 14,
      background: cfg.bg,
      border: `2px solid ${selected ? '#fff' : cfg.color}`,
      boxShadow: selected
        ? `0 0 0 3px ${cfg.color}55, 0 6px 28px rgba(0,0,0,0.55)`
        : `0 4px 20px rgba(0,0,0,0.45)`,
      cursor: 'grab',
      transition: 'box-shadow 0.15s, border-color 0.15s',
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: cfg.color, width: 10, height: 10, border: 'none' }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: `${cfg.color}22`,
          border: `1.5px solid ${cfg.color}55`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Icon size={20} color={cfg.color} />
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: cfg.color,
            textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            {cfg.label}
          </div>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9', lineHeight: 1.3 }}>
            {data.label}
          </div>
        </div>
      </div>

      {data.description && (
        <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.55,
          borderTop: `1px solid ${cfg.color}30`, paddingTop: 8 }}>
          {data.description}
        </div>
      )}

      <Handle type="source" position={Position.Right}
        style={{ background: cfg.color, width: 10, height: 10, border: 'none' }} />
    </div>
  )
}

/** ERD Node — database table look with field rows */
function ErdNode({ data, selected }) {
  const fields = data.fields || []
  const headerColor = '#1e3a5f'
  const borderColor = selected ? '#60a5fa' : '#2563eb'

  return (
    <div style={{
      minWidth: 220, maxWidth: 280,
      borderRadius: 10,
      border: `2px solid ${borderColor}`,
      overflow: 'hidden',
      boxShadow: selected
        ? `0 0 0 3px rgba(37,99,235,0.45), 0 6px 28px rgba(0,0,0,0.55)`
        : '0 4px 20px rgba(0,0,0,0.5)',
      cursor: 'grab',
      transition: 'box-shadow 0.15s, border-color 0.15s',
      fontFamily: 'var(--font-mono, monospace)',
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: '#60a5fa', width: 10, height: 10, border: 'none' }} />

      {/* Table header */}
      <div style={{
        background: headerColor,
        padding: '8px 12px',
        display: 'flex', alignItems: 'center', gap: 8,
        borderBottom: '1px solid #2563eb',
      }}>
        <span style={{ fontSize: 14 }}>🗄️</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#93c5fd', letterSpacing: '0.02em' }}>
          {data.modelName || data.label}
        </span>
      </div>

      {/* Field rows */}
      <div style={{ background: '#0d1a2d' }}>
        {fields.map((field, i) => (
          <div key={field.name || i} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '5px 12px',
            borderBottom: i < fields.length - 1 ? '1px solid #1e2d45' : 'none',
            background: field.isPrimaryKey ? 'rgba(37,99,235,0.12)' : 'transparent',
          }}>
            <span style={{
              fontSize: 12, color: field.isPrimaryKey ? '#fbbf24' : '#cbd5e1',
              fontWeight: field.isPrimaryKey ? 700 : 400,
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              {field.isPrimaryKey && <span title="Primary Key">🔑</span>}
              {field.name}
            </span>
            <span style={{
              fontSize: 11, color: '#64748b',
              background: 'rgba(100,116,139,0.15)',
              padding: '1px 6px', borderRadius: 4,
              marginLeft: 8, flexShrink: 0,
            }}>
              {field.type}
            </span>
          </div>
        ))}
        {fields.length === 0 && (
          <div style={{ padding: '8px 12px', fontSize: 12, color: '#475569', fontStyle: 'italic' }}>
            No fields
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right}
        style={{ background: '#60a5fa', width: 10, height: 10, border: 'none' }} />
    </div>
  )
}

const nodeTypes = { lldNode: LldNode, custom: HldNode, erd: ErdNode }

/* ══════════════════════════════════════════════════════════════════
   Node / edge enrichment
═══════════════════════════════════════════════════════════════════ */

function enrichLldNodes(raw) {
  return raw.map(n => ({
    ...n,
    type: 'lldNode',
    data: { ...n.data, x: n.position?.x ?? 0 },
  }))
}

function enrichHldNodes(raw) {
  return raw.map(n => ({ ...n, type: 'custom' }))
}

function enrichErdNodes(raw) {
  return raw.map(n => ({ ...n, type: 'erd' }))
}

function enrichEdges(raw, color = '#4f6ef7', animated = true) {
  return raw.map(e => ({
    ...e,
    type: 'smoothstep',
    animated,
    style: { stroke: color, strokeWidth: 2, opacity: 0.8 },
    labelStyle: { fill: '#94a3b8', fontSize: 11, fontWeight: 600 },
    labelBgStyle: { fill: '#0d1220', fillOpacity: 0.85 },
    labelBgPadding: [4, 6],
    labelBgBorderRadius: 4,
    markerEnd: { type: 'arrowclosed', color, width: 14, height: 14 },
  }))
}

/* ══════════════════════════════════════════════════════════════════
   Legend panels
═══════════════════════════════════════════════════════════════════ */

function LldLegend() {
  return (
    <div style={legendWrap}>
      <div style={legendTitle}>Architecture Layers</div>
      {LLD_LAYERS.map(l => (
        <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 11, height: 11, borderRadius: 3, background: l.color, flexShrink: 0 }} />
          <span style={{ fontSize: 12, color: '#cbd5e1' }}>{l.icon} {l.label}</span>
        </div>
      ))}
    </div>
  )
}

function HldLegend() {
  return (
    <div style={legendWrap}>
      <div style={legendTitle}>System Types</div>
      {Object.entries(HLD_TYPES).map(([key, cfg]) => {
        const { Icon } = cfg
        return (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon size={13} color={cfg.color} />
            <span style={{ fontSize: 12, color: '#cbd5e1' }}>{cfg.label}</span>
          </div>
        )
      })}
    </div>
  )
}

function ErdLegend() {
  return (
    <div style={legendWrap}>
      <div style={legendTitle}>ERD Legend</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 13 }}>🔑</span>
        <span style={{ fontSize: 12, color: '#fbbf24' }}>Primary Key</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 11, height: 11, borderRadius: 3, background: '#2563eb', flexShrink: 0 }} />
        <span style={{ fontSize: 12, color: '#cbd5e1' }}>Entity / Model</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 12, color: '#64748b', fontFamily: 'monospace' }}>1:N</span>
        <span style={{ fontSize: 12, color: '#cbd5e1' }}>Relationship</span>
      </div>
    </div>
  )
}

const legendWrap = {
  background: 'rgba(8,12,24,0.92)',
  border: '1px solid #1e2535',
  borderRadius: 10,
  padding: '12px 14px',
  display: 'flex', flexDirection: 'column', gap: 6,
  backdropFilter: 'blur(8px)',
  minWidth: 170,
}
const legendTitle = {
  fontSize: 10, fontWeight: 700, color: '#475569',
  letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 4,
}

/* ══════════════════════════════════════════════════════════════════
   Inner flow canvas — isolated state per tab
═══════════════════════════════════════════════════════════════════ */

function FlowCanvas({ rawNodes, rawEdges, enrichNodesFn, edgeColor, edgeAnimated = true, Legend }) {
  const enriched = useMemo(() => enrichNodesFn(rawNodes), [rawNodes])
  const styled   = useMemo(() => enrichEdges(rawEdges, edgeColor, edgeAnimated), [rawEdges, edgeColor, edgeAnimated])

  const [nodes, , onNodesChange] = useNodesState(enriched)
  const [edges, , onEdgesChange] = useEdgesState(styled)

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.28 }}
      nodesDraggable
      nodesConnectable={false}
      elementsSelectable
      minZoom={0.15}
      maxZoom={2.5}
      attributionPosition="bottom-right"
      style={{ width: '100%', height: '100%' }}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#1a2236" />
      <Controls style={{ background: '#0d1220', border: '1px solid #1e2535', borderRadius: 8 }}
        showInteractive={false} />
      <MiniMap
        style={{ background: '#0d1220', border: '1px solid #1e2535', borderRadius: 8 }}
        nodeColor={n => {
          if (n.type === 'custom') return getHldType(n.data?.systemType).color
          if (n.type === 'erd')    return '#2563eb'
          return getLldLayer(n.data?.x ?? 0).color
        }}
        maskColor="rgba(8,12,20,0.75)"
      />
      <Panel position="top-left"><Legend /></Panel>
    </ReactFlow>
  )
}

/* ══════════════════════════════════════════════════════════════════
   StatChip
═══════════════════════════════════════════════════════════════════ */

function StatChip({ label, value, icon, color = 'var(--accent)' }) {
  return (
    <div style={{ flex: '1 1 120px', display: 'flex', alignItems: 'center', gap: 12,
      padding: '14px 16px', background: 'var(--bg-input)',
      border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
      <span style={{ fontSize: 22 }}>{icon}</span>
      <div>
        <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════
   Main component
═══════════════════════════════════════════════════════════════════ */

const TABS = [
  { key: 'HLD', label: '🏗️  High-Level Design',    hint: 'System overview' },
  { key: 'LLD', label: '🔬  Detailed Architecture', hint: 'Module dependencies' },
  { key: 'ERD', label: '🗃️  Database Schema',       hint: 'Entity-relationship diagram' },
]

export default function DiagramViewer({ result, onReset }) {
  const {
    lld = { nodes: [], edges: [] },
    hld = { nodes: [], edges: [] },
    erd = { nodes: [], edges: [] },
    arch_summary,
    graph_stats,
    processing_time_seconds,
    warning,
  } = result

  const [activeTab, setActiveTab] = useState('HLD')

  const activeData = { HLD: hld, LLD: lld, ERD: erd }[activeTab]

  const tabHint = {
    HLD: 'system-level infrastructure blocks',
    LLD: 'module-level dependencies',
    ERD: 'data models and their relationships',
  }[activeTab]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>
            {{ HLD: 'High-Level Design', LLD: 'Detailed Architecture', ERD: 'Database Schema (ERD)' }[activeTab]}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 4 }}>
            Analysed in {processing_time_seconds}s · {graph_stats.files_analysed} files ·{' '}
            {activeData.nodes.length} components · {activeData.edges.length} connections
          </p>
        </div>
        <button onClick={onReset} style={{
          padding: '10px 20px', background: 'var(--bg-input)',
          color: 'var(--text-secondary)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 14,
        }}>← New Analysis</button>
      </div>

      {/* ── Tab toggle ──────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 0,
        background: '#0d1220',
        border: '1px solid #1e2535',
        borderRadius: 12,
        padding: 4,
        width: 'fit-content',
      }}>
        {TABS.map(({ key, label }) => (
          <button key={key} onClick={() => setActiveTab(key)} style={{
            padding: '10px 22px',
            borderRadius: 9,
            border: 'none',
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 600,
            transition: 'all 0.18s',
            background: activeTab === key
              ? 'linear-gradient(135deg, #4f6ef7, #7c3aed)'
              : 'transparent',
            color: activeTab === key ? '#fff' : '#64748b',
            boxShadow: activeTab === key
              ? '0 2px 12px rgba(79,110,247,0.35)'
              : 'none',
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* ── Warning ─────────────────────────────────────────────────── */}
      {warning && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(246,173,85,0.1)', border: '1px solid var(--warning)',
          borderRadius: 'var(--radius-sm)', color: 'var(--warning)', fontSize: 13,
        }}>⚠️ {warning}</div>
      )}

      {/* ── AI Summary (HLD only) ────────────────────────────────────── */}
      {activeTab === 'HLD' && arch_summary && (
        <div style={{
          padding: 20,
          background: 'linear-gradient(135deg, rgba(79,110,247,0.08), rgba(167,139,250,0.06))',
          border: '1px solid rgba(79,110,247,0.25)',
          borderRadius: 'var(--radius)',
          borderLeft: '4px solid var(--accent)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 18 }}>🤖</span>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)',
              textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              AI Architecture Summary
            </h3>
          </div>
          <p style={{ color: '#cbd5e1', fontSize: 14, lineHeight: 1.75 }}>{arch_summary}</p>
        </div>
      )}

      {/* ── ERD info banner ──────────────────────────────────────────── */}
      {activeTab === 'ERD' && (
        <div style={{
          padding: '12px 18px',
          background: 'linear-gradient(135deg, rgba(37,99,235,0.10), rgba(30,58,95,0.12))',
          border: '1px solid rgba(37,99,235,0.3)',
          borderRadius: 'var(--radius)',
          borderLeft: '4px solid #2563eb',
          fontSize: 13, color: '#93c5fd', lineHeight: 1.6,
        }}>
          {erd.nodes.length > 0
            ? '🗄️ \u00a0Showing data models extracted from ORM classes and schemas found in the codebase. Relationships are derived from foreign keys and field references.'
            : '🗄️ \u00a0No database models were detected in this repository. This codebase appears to be stateless — no ORM, SQL, or schema definitions were found.'}
        </div>
      )}

      {/* ── Stats ───────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <StatChip label="Files Analysed"  value={graph_stats.files_analysed}       icon="📄" color="#60a5fa" />
        <StatChip label="Graph Nodes"     value={graph_stats.nodes}                 icon="🔵" color="#a78bfa" />
        <StatChip label="Edges"           value={graph_stats.edges}                 icon="🔗" color="#34d399" />
        <StatChip label="Clusters"        value={graph_stats.clusters?.length ?? 0} icon="📦" color="#f59e0b" />
      </div>

      {/* ── Core hubs ───────────────────────────────────────────────── */}
      {graph_stats.hubs?.length > 0 && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8,
          padding: '10px 16px',
          background: 'rgba(167,139,250,0.08)',
          border: '1px solid rgba(167,139,250,0.2)',
          borderRadius: 'var(--radius-sm)',
        }}>
          <span style={{ fontSize: 12, color: '#94a3b8', marginRight: 4 }}>🌟 Core Hubs:</span>
          {graph_stats.hubs.map(h => (
            <code key={h} style={{
              padding: '3px 10px',
              background: 'rgba(167,139,250,0.15)',
              border: '1px solid rgba(167,139,250,0.3)',
              borderRadius: 4, color: '#a78bfa', fontSize: 12,
              fontFamily: 'var(--font-mono)',
            }}>{h}</code>
          ))}
        </div>
      )}

      {/* ── React Flow canvas ───────────────────────────────────────── */}
      <div style={{
        height: 580,
        border: '1px solid #1e2535',
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        background: '#080c14',
      }}>
        {activeTab === 'HLD' && (
          <FlowCanvas
            key="hld"
            rawNodes={hld.nodes}
            rawEdges={hld.edges}
            enrichNodesFn={enrichHldNodes}
            edgeColor="#a78bfa"
            edgeAnimated
            Legend={HldLegend}
          />
        )}
        {activeTab === 'LLD' && (
          <FlowCanvas
            key="lld"
            rawNodes={lld.nodes}
            rawEdges={lld.edges}
            enrichNodesFn={enrichLldNodes}
            edgeColor="#4f6ef7"
            edgeAnimated
            Legend={LldLegend}
          />
        )}
        {activeTab === 'ERD' && (
          erd.nodes.length === 0
            ? (
              <div style={{
                height: '100%', display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: 12,
                color: '#475569',
              }}>
                <span style={{ fontSize: 48 }}>🗄️</span>
                <p style={{ fontSize: 15, fontWeight: 600, color: '#64748b' }}>No Data Models Found</p>
                <p style={{ fontSize: 13, color: '#475569', textAlign: 'center', maxWidth: 340 }}>
                  This repository has no ORM models, database schemas, or persistent data layer.
                </p>
              </div>
            )
            : (
              <FlowCanvas
                key="erd"
                rawNodes={erd.nodes}
                rawEdges={erd.edges}
                enrichNodesFn={enrichErdNodes}
                edgeColor="#2563eb"
                edgeAnimated={false}
                Legend={ErdLegend}
              />
            )
        )}
      </div>

      {/* ── Hint ────────────────────────────────────────────────────── */}
      <p style={{ textAlign: 'center', color: '#475569', fontSize: 12, marginTop: -8 }}>
        💡 Drag nodes · Scroll to zoom · Drag background to pan · Shows {tabHint}
      </p>
    </div>
  )
}
