/**
 * DiagramViewer
 * Renders the final Eraser.io hosted diagram in an iframe,
 * plus graph statistics and architecture summary.
 *
 * Props:
 *   result: {
 *     diagram_url: string,
 *     arch_summary: string,
 *     dac_syntax: string,
 *     graph_stats: { files_analysed, nodes, edges, hubs, clusters },
 *     processing_time_seconds: number,
 *     warning: string,
 *   }
 *   onReset: () => void
 */
import React, { useState } from 'react'

export default function DiagramViewer({ result, onReset }) {
  const [showDac, setShowDac] = useState(false)
  const [iframeFailed, setIframeFailed] = useState(false)

  const { diagram_url, arch_summary, dac_syntax, graph_stats,
          processing_time_seconds, warning } = result

  return (
    <div style={styles.container}>
      {/* ── Header row ─────────────────────────────────────────────── */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Architecture Diagram</h2>
          <p style={styles.subtitle}>
            Analysed in {processing_time_seconds}s ·{' '}
            {graph_stats.files_analysed} files ·{' '}
            {graph_stats.nodes} nodes · {graph_stats.edges} edges
          </p>
        </div>
        <div style={styles.headerActions}>
          <a href={diagram_url} target="_blank" rel="noreferrer"
            style={styles.openBtn}>
            Open in Eraser ↗
          </a>
          <button onClick={onReset} style={styles.resetBtn}>
            ← New Analysis
          </button>
        </div>
      </div>

      {/* ── Warning banner (non-fatal errors) ─────────────────────── */}
      {warning && (
        <div style={styles.warning} role="alert">
          ⚠️ {warning}
        </div>
      )}

      {/* ── Architecture summary ───────────────────────────────────── */}
      {arch_summary && (
        <div style={styles.summaryCard}>
          <h3 style={styles.sectionTitle}>🤖 AI Architecture Summary</h3>
          <p style={styles.summaryText}>{arch_summary}</p>
        </div>
      )}

      {/* ── Stats row ──────────────────────────────────────────────── */}
      <div style={styles.statsRow}>
        <StatChip label="Files Analysed" value={graph_stats.files_analysed} icon="📄" />
        <StatChip label="Graph Nodes"    value={graph_stats.nodes}           icon="🔵" />
        <StatChip label="Edges"          value={graph_stats.edges}           icon="🔗" />
        <StatChip label="Clusters"       value={graph_stats.clusters?.length ?? 0} icon="📦" />
      </div>

      {/* ── Hubs ───────────────────────────────────────────────────── */}
      {graph_stats.hubs?.length > 0 && (
        <div style={styles.hubsCard}>
          <span style={styles.hubsLabel}>Core Hubs (most depended-upon):</span>
          {graph_stats.hubs.map((h) => (
            <code key={h} style={styles.hubChip}>{h}</code>
          ))}
        </div>
      )}

      {/* ── Eraser diagram iframe ──────────────────────────────────── */}
      <div style={styles.iframeCard}>
        <h3 style={styles.sectionTitle}>🎨 Visual Architecture Diagram</h3>
        {iframeFailed ? (
          <div style={styles.iframeFallback}>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>
              The diagram cannot be embedded directly. Click the button below
              to view it on Eraser.io.
            </p>
            <a href={diagram_url} target="_blank" rel="noreferrer"
              style={styles.openBtn}>
              View Diagram on Eraser.io ↗
            </a>
          </div>
        ) : (
          <iframe
            src={diagram_url}
            title="Architecture Diagram"
            style={styles.iframe}
            onError={() => setIframeFailed(true)}
            allow="fullscreen"
            sandbox="allow-same-origin allow-scripts allow-popups"
          />
        )}
      </div>

      {/* ── DaC toggle ─────────────────────────────────────────────── */}
      <div style={styles.dacSection}>
        <button
          style={styles.dacToggle}
          onClick={() => setShowDac((v) => !v)}
        >
          {showDac ? '▲ Hide' : '▼ Show'} Eraser Diagram-as-Code
        </button>
        {showDac && dac_syntax && (
          <pre style={styles.dacCode}>{dac_syntax}</pre>
        )}
      </div>
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
  headerActions: { display: 'flex', gap: '12px', flexWrap: 'wrap' },
  openBtn: {
    padding: '10px 20px',
    background: 'var(--accent)',
    color: '#fff',
    borderRadius: 'var(--radius-sm)',
    textDecoration: 'none',
    fontSize: '14px', fontWeight: 600,
    display: 'inline-block',
  },
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
  statsRow: {
    display: 'flex', gap: '12px', flexWrap: 'wrap',
  },
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
  iframeCard: {
    padding: '20px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
  },
  iframe: {
    width: '100%', height: '540px',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    background: '#fff',
  },
  iframeFallback: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    padding: '40px', textAlign: 'center',
  },
  dacSection: { display: 'flex', flexDirection: 'column', gap: '8px' },
  dacToggle: {
    alignSelf: 'flex-start',
    background: 'none', border: 'none',
    color: 'var(--text-secondary)',
    fontSize: '13px', cursor: 'pointer',
    padding: '4px 0',
  },
  dacCode: {
    padding: '16px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--text-secondary)',
    fontSize: '12px',
    fontFamily: 'var(--font-mono)',
    overflowX: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
}
