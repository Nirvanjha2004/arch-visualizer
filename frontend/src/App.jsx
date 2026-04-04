/**
 * App — Root component
 * Orchestrates three states:
 *   1. IDLE     — show AnalyzerForm
 *   2. LOADING  — show LoadingState
 *   3. RESULT   — show DiagramViewer
 *   4. ERROR    — show error message with retry
 */
import React, { useState } from 'react'
import AnalyzerForm  from './components/AnalyzerForm.jsx'
import LoadingState  from './components/LoadingState.jsx'
import DiagramViewer from './components/DiagramViewer.jsx'

// Backend URL from env (Vite proxy handles it in dev)
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || ''

export default function App() {
  const [phase, setPhase]   = useState('idle')   // idle | loading | result | error
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  const handleAnalyze = async (repoUrl) => {
    setPhase('loading')
    setResult(null)
    setErrorMsg('')

    try {
      const resp = await fetch(`${BACKEND_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      })

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error ${resp.status}`)
      }

      const data = await resp.json()
      setResult(data)
      setPhase('result')
    } catch (err) {
      setErrorMsg(err.message || 'An unexpected error occurred.')
      setPhase('error')
    }
  }

  const handleReset = () => {
    setPhase('idle')
    setResult(null)
    setErrorMsg('')
  }

  return (
    <div style={styles.page}>
      {/* ── Header ──────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <span style={styles.logoIcon}>⬡</span>
          <span style={styles.logoText}>ArchViz</span>
        </div>
        <nav style={styles.nav}>
          <a href="https://github.com" target="_blank" rel="noreferrer"
            style={styles.navLink}>GitHub</a>
          <a href="https://eraser.io" target="_blank" rel="noreferrer"
            style={styles.navLink}>Eraser.io</a>
        </nav>
      </header>

      {/* ── Main content ────────────────────────────────────────────── */}
      <main style={styles.main}>
        {/* Hero section (always visible in idle/error) */}
        {(phase === 'idle' || phase === 'error') && (
          <section style={styles.hero}>
            <div style={styles.badge}>Powered by LangGraph + Eraser.io MCP</div>
            <h1 style={styles.heroTitle}>
              Visualise Any<br />
              <span style={styles.heroAccent}>GitHub Codebase</span>
            </h1>
            <p style={styles.heroSubtitle}>
              Paste a GitHub repository URL. We'll parse ASTs, build a dependency
              graph, and generate a beautiful architecture diagram — automatically.
            </p>

            {/* How it works steps */}
            <div style={styles.stepsRow}>
              {[
                { n: '01', label: 'Fetch',  desc: 'GitHub API pulls all source files' },
                { n: '02', label: 'Parse',  desc: 'Tree-sitter builds ASTs per file'  },
                { n: '03', label: 'Graph',  desc: 'NetworkX maps the dependency graph' },
                { n: '04', label: 'Diagram',desc: 'Eraser MCP renders the architecture' },
              ].map(({ n, label, desc }) => (
                <div key={n} style={styles.step}>
                  <span style={styles.stepNum}>{n}</span>
                  <span style={styles.stepLabel}>{label}</span>
                  <span style={styles.stepDesc}>{desc}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Card container */}
        <div style={styles.card}>
          {phase === 'idle' && (
            <AnalyzerForm onSubmit={handleAnalyze} loading={false} />
          )}

          {phase === 'loading' && (
            <>
              <AnalyzerForm onSubmit={() => {}} loading={true} />
              <div style={styles.divider} />
              <LoadingState />
            </>
          )}

          {phase === 'result' && result && (
            <DiagramViewer result={result} onReset={handleReset} />
          )}

          {phase === 'error' && (
            <div style={styles.errorBox} role="alert">
              <span style={styles.errorIcon}>❌</span>
              <div>
                <p style={styles.errorTitle}>Analysis Failed</p>
                <p style={styles.errorDetail}>{errorMsg}</p>
              </div>
              <button onClick={handleReset} style={styles.retryBtn}>
                Try Again
              </button>
            </div>
          )}
        </div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer style={styles.footer}>
        <p>
          Built with FastAPI · LangGraph · Tree-sitter · NetworkX · Eraser.io MCP
          · Groq Llama 3 70B · React + Vite
        </p>
        <p style={{ marginTop: '4px', color: 'var(--text-muted)', fontSize: '11px' }}>
          All free tiers · No credit card required
        </p>
      </footer>

      {/* ── Global keyframes (injected into <head> via style tag) ──── */}
      <style>{`
        @keyframes spin    { to { transform: rotate(360deg); } }
        @keyframes pulse   { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
        @keyframes fadeIn  { from { opacity:0; transform:translateY(8px); }
                             to   { opacity:1; transform:translateY(0); } }
        input:focus { border-color: var(--border-focus) !important;
                      box-shadow: 0 0 0 3px var(--accent-glow) !important; }
        a:hover, button:hover:not(:disabled) { opacity: 0.85; }
      `}</style>
    </div>
  )
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex', flexDirection: 'column',
    background: 'var(--bg-page)',
  },
  /* Header */
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '16px 32px',
    borderBottom: '1px solid var(--border)',
    position: 'sticky', top: 0, zIndex: 100,
    background: 'rgba(13,15,20,0.85)',
    backdropFilter: 'blur(12px)',
  },
  logo: { display: 'flex', alignItems: 'center', gap: '10px' },
  logoIcon: { fontSize: '24px', color: 'var(--accent)' },
  logoText: {
    fontSize: '18px', fontWeight: 800,
    background: 'linear-gradient(135deg, var(--text-primary), var(--accent))',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  nav: { display: 'flex', gap: '20px' },
  navLink: { color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '14px' },
  /* Main */
  main: {
    flex: 1,
    maxWidth: '900px', width: '100%',
    margin: '0 auto',
    padding: '48px 24px',
    display: 'flex', flexDirection: 'column', gap: '40px',
  },
  /* Hero */
  hero: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    textAlign: 'center', gap: '20px',
    animation: 'fadeIn 0.5s ease',
  },
  badge: {
    padding: '6px 16px',
    background: 'rgba(79,110,247,0.15)',
    border: '1px solid rgba(79,110,247,0.3)',
    borderRadius: '20px',
    color: 'var(--accent)',
    fontSize: '12px', fontWeight: 600, letterSpacing: '0.05em',
    textTransform: 'uppercase',
  },
  heroTitle: {
    fontSize: 'clamp(36px, 6vw, 56px)',
    fontWeight: 800, lineHeight: 1.15,
    color: 'var(--text-primary)',
  },
  heroAccent: {
    background: 'linear-gradient(135deg, var(--accent), #a78bfa)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  heroSubtitle: {
    maxWidth: '560px',
    color: 'var(--text-secondary)', fontSize: '16px', lineHeight: 1.7,
  },
  stepsRow: {
    display: 'flex', gap: '16px', flexWrap: 'wrap',
    justifyContent: 'center', width: '100%',
  },
  step: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
    padding: '16px 20px', minWidth: '140px',
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)', flex: '1 1 130px',
  },
  stepNum: { color: 'var(--accent)', fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700 },
  stepLabel: { color: 'var(--text-primary)', fontWeight: 700, fontSize: '15px' },
  stepDesc: { color: 'var(--text-secondary)', fontSize: '12px', textAlign: 'center' },
  /* Card */
  card: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '32px',
    boxShadow: 'var(--shadow-card)',
    animation: 'fadeIn 0.4s ease',
  },
  divider: { height: '1px', background: 'var(--border)', margin: '24px 0' },
  /* Error */
  errorBox: {
    display: 'flex', alignItems: 'flex-start', gap: '16px',
    padding: '20px',
    background: 'rgba(252,129,129,0.08)',
    border: '1px solid var(--error)',
    borderRadius: 'var(--radius)',
  },
  errorIcon: { fontSize: '24px', flexShrink: 0 },
  errorTitle: { fontWeight: 700, color: 'var(--error)', marginBottom: '4px' },
  errorDetail: { color: 'var(--text-secondary)', fontSize: '14px' },
  retryBtn: {
    marginLeft: 'auto', padding: '10px 20px',
    background: 'var(--accent)', color: '#fff',
    border: 'none', borderRadius: 'var(--radius-sm)',
    cursor: 'pointer', fontSize: '14px', fontWeight: 600,
    whiteSpace: 'nowrap', flexShrink: 0,
  },
  /* Footer */
  footer: {
    padding: '24px',
    borderTop: '1px solid var(--border)',
    textAlign: 'center',
    color: 'var(--text-secondary)',
    fontSize: '12px',
  },
}
