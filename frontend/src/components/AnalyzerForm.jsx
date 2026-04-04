/**
 * AnalyzerForm
 * URL input + "Analyze Architecture" submit button.
 * Props:
 *   onSubmit(url: string) => void
 *   loading: boolean
 */
import React, { useState } from 'react'

const EXAMPLES = [
  'https://github.com/tiangolo/fastapi',
  'https://github.com/expressjs/express',
  'https://github.com/django/django',
]

export default function AnalyzerForm({ onSubmit, loading }) {
  const [url, setUrl] = useState('')
  const [urlError, setUrlError] = useState('')

  const validate = (v) => {
    if (!v.trim()) return 'Please enter a GitHub repository URL.'
    if (!v.includes('github.com')) return 'URL must be a GitHub repository (github.com).'
    return ''
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const err = validate(url)
    setUrlError(err)
    if (!err) onSubmit(url.trim())
  }

  const handleExampleClick = (ex) => {
    setUrl(ex)
    setUrlError('')
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      {/* ── Input row ─────────────────────────────────────────────── */}
      <div style={styles.inputRow}>
        <div style={styles.inputWrapper}>
          {/* GitHub icon */}
          <svg style={styles.inputIcon} viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205
              11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235
              -3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23
              -1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845
              1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765
              -1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385
              1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3
              1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56
              3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23
              1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375
              .81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225
              .69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          <input
            type="text"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setUrlError('') }}
            placeholder="https://github.com/owner/repository"
            style={{
              ...styles.input,
              ...(urlError ? styles.inputError : {}),
            }}
            disabled={loading}
            aria-label="GitHub repository URL"
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        <button
          type="submit"
          disabled={loading || !url.trim()}
          style={{
            ...styles.button,
            ...(loading || !url.trim() ? styles.buttonDisabled : {}),
          }}
        >
          {loading ? (
            <span style={styles.btnContent}>
              <span style={styles.spinner} />
              Analysing…
            </span>
          ) : (
            <span style={styles.btnContent}>
              <svg style={styles.btnIcon} viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth={2}>
                <circle cx={11} cy={11} r={8} />
                <line x1={21} y1={21} x2={16.65} y2={16.65} />
              </svg>
              Analyze Architecture
            </span>
          )}
        </button>
      </div>

      {/* ── Validation error ───────────────────────────────────────── */}
      {urlError && (
        <p style={styles.errorText} role="alert">{urlError}</p>
      )}

      {/* ── Example repos ─────────────────────────────────────────── */}
      <div style={styles.examples}>
        <span style={styles.examplesLabel}>Try an example:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => handleExampleClick(ex)}
            disabled={loading}
            style={styles.exampleChip}
          >
            {ex.replace('https://github.com/', '')}
          </button>
        ))}
      </div>
    </form>
  )
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  form: { display: 'flex', flexDirection: 'column', gap: '12px' },
  inputRow: {
    display: 'flex', gap: '12px', flexWrap: 'wrap',
  },
  inputWrapper: {
    position: 'relative', flex: 1, minWidth: '280px',
  },
  inputIcon: {
    position: 'absolute', left: '14px', top: '50%',
    transform: 'translateY(-50%)',
    width: '18px', height: '18px',
    color: 'var(--text-secondary)',
    pointerEvents: 'none',
  },
  input: {
    width: '100%',
    padding: '14px 14px 14px 44px',
    background: 'var(--bg-input)',
    border: '1.5px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--text-primary)',
    fontSize: '15px',
    fontFamily: 'var(--font-mono)',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  },
  inputError: {
    borderColor: 'var(--error)',
  },
  button: {
    padding: '14px 28px',
    background: 'var(--accent)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    fontSize: '15px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.2s, box-shadow 0.2s',
    whiteSpace: 'nowrap',
    boxShadow: '0 0 0 0 var(--accent-glow)',
  },
  buttonDisabled: {
    background: 'var(--bg-input)',
    color: 'var(--text-muted)',
    cursor: 'not-allowed',
    boxShadow: 'none',
  },
  btnContent: {
    display: 'flex', alignItems: 'center', gap: '8px',
  },
  btnIcon: { width: '16px', height: '16px' },
  spinner: {
    display: 'inline-block',
    width: '16px', height: '16px',
    border: '2px solid rgba(255,255,255,0.3)',
    borderTopColor: '#fff',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  errorText: {
    color: 'var(--error)', fontSize: '13px', marginTop: '-4px',
  },
  examples: {
    display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px',
    marginTop: '4px',
  },
  examplesLabel: {
    color: 'var(--text-muted)', fontSize: '13px',
  },
  exampleChip: {
    padding: '4px 12px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: '20px',
    color: 'var(--text-secondary)',
    fontSize: '12px',
    fontFamily: 'var(--font-mono)',
    cursor: 'pointer',
    transition: 'border-color 0.2s, color 0.2s',
  },
}
