/**
 * LoadingState
 * Animated progress indicator shown while the backend pipeline runs.
 * The steps animate in sequence to give the user visual feedback.
 */
import React, { useEffect, useState } from 'react'

const PIPELINE_STEPS = [
  { label: 'Fetching repository tree from GitHub…',    icon: '📥', duration: 4000 },
  { label: 'Generating ASTs with Tree-sitter…',         icon: '🌳', duration: 5000 },
  { label: 'Building dependency graph with NetworkX…', icon: '🔗', duration: 4000 },
  { label: 'Pruning graph & summarising topology…',    icon: '✂️',  duration: 3000 },
  { label: 'LangGraph agent analysing architecture…',  icon: '🤖', duration: 5000 },
  { label: 'Generating Eraser Diagram-as-Code…',       icon: '✍️',  duration: 4000 },
  { label: 'Calling Eraser MCP — creating diagram…',   icon: '🎨', duration: 5000 },
  { label: 'Finalising hosted diagram link…',          icon: '🔗', duration: 2000 },
]

export default function LoadingState() {
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    let step = 0
    const advance = () => {
      if (step < PIPELINE_STEPS.length - 1) {
        step++
        setActiveStep(step)
        setTimeout(advance, PIPELINE_STEPS[step].duration)
      }
    }
    const timer = setTimeout(advance, PIPELINE_STEPS[0].duration)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div style={styles.container}>
      {/* Animated ring */}
      <div style={styles.ringWrapper}>
        <div style={styles.ringOuter}>
          <div style={styles.ringInner}>
            <span style={styles.ringText}>⚙️</span>
          </div>
        </div>
      </div>

      <h2 style={styles.title}>Analysing Architecture</h2>
      <p style={styles.subtitle}>
        This usually takes 30–90 seconds depending on repository size.
      </p>

      {/* Pipeline step list */}
      <div style={styles.stepList}>
        {PIPELINE_STEPS.map((step, idx) => {
          const isDone    = idx < activeStep
          const isActive  = idx === activeStep
          const isPending = idx > activeStep

          return (
            <div key={idx} style={{
              ...styles.step,
              ...(isActive  ? styles.stepActive  : {}),
              ...(isDone    ? styles.stepDone    : {}),
              ...(isPending ? styles.stepPending : {}),
            }}>
              <span style={styles.stepIcon}>
                {isDone ? '✅' : isActive ? step.icon : '⬜'}
              </span>
              <span style={styles.stepLabel}>{step.label}</span>
              {isActive && <span style={styles.dots}><span>.</span><span>.</span><span>.</span></span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  container: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    padding: '48px 24px', gap: '24px',
  },
  ringWrapper: { position: 'relative' },
  ringOuter: {
    width: '80px', height: '80px',
    border: '3px solid var(--border)',
    borderTopColor: 'var(--accent)',
    borderRadius: '50%',
    animation: 'spin 1.2s linear infinite',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  ringInner: {
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  ringText: { fontSize: '28px' },
  title: {
    fontSize: '22px', fontWeight: 700,
    background: 'linear-gradient(135deg, var(--text-primary), var(--accent))',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  subtitle: { color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center' },
  stepList: {
    display: 'flex', flexDirection: 'column', gap: '10px',
    width: '100%', maxWidth: '520px',
  },
  step: {
    display: 'flex', alignItems: 'center', gap: '12px',
    padding: '10px 16px', borderRadius: 'var(--radius-sm)',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    fontSize: '14px', transition: 'all 0.3s ease',
  },
  stepActive: {
    borderColor: 'var(--accent)',
    boxShadow: '0 0 12px var(--accent-glow)',
    background: 'rgba(79,110,247,0.08)',
  },
  stepDone: {
    borderColor: 'var(--success)',
    background: 'rgba(72,187,120,0.05)',
    opacity: 0.8,
  },
  stepPending: { opacity: 0.4 },
  stepIcon: { fontSize: '18px', minWidth: '24px' },
  stepLabel: { flex: 1, color: 'var(--text-primary)' },
  dots: {
    display: 'flex', gap: '2px',
    animation: 'pulse 1.4s infinite',
    color: 'var(--accent)', fontWeight: 700, fontSize: '18px',
  },
}
