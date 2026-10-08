import React, { useEffect } from 'react'

function getPillClass(priority) {
  if (!priority) return 'pill-none'
  if (priority === 'High') return 'pill-high'
  if (priority === 'Medium') return 'pill-medium'
  if (priority === 'Rejected') return 'pill-rejected'
  if (priority === 'Very Low') return 'pill-very-low'
  return 'pill-low'
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

const rows = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'Name' },
  { key: 'company', label: 'Company' },
  { key: 'company_size', label: 'Company Size' },
  { key: 'industry', label: 'Industry' },
  { key: 'role_level', label: 'Role' },
  { key: 'intent_score', label: 'Intent Score' },
  { key: 'urgency_level', label: 'Urgency Level' },
  { key: 'final_score', label: 'Final Score' },
  { key: 'priority', label: 'Priority' },
  { key: 'confidence_score', label: 'Confidence' },
  { key: 'summary', label: 'Summary' },
  { key: 'created_at', label: 'Created At' },
]

function formatValue(lead, key) {
  const v = lead[key]
  if (key === 'created_at') return formatDate(v)
  if (key === 'priority' && v) return null
  if (key === 'confidence_score') return v != null ? `${Math.min(100, Math.max(0, v))}%` : '—'
  return v ?? '—'
}

export default function LeadDetailModal({ lead, onClose }) {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  if (!lead) return null

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 id="modal-title" className="modal-title">Lead #{lead.id}</h2>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="modal-body">
          {rows.map(({ key, label }) => (
            <div key={key} className="modal-row">
              <span className="modal-label">{label}</span>
              <span className="modal-value">
                {key === 'priority' ? (
                  <span className={`pill ${getPillClass(lead.priority)}`}>
                    {lead.priority ?? '—'}
                  </span>
                ) : key === 'confidence_score' ? (
                  <span className="confidence-badge" title="Confidence score">
                    {formatValue(lead, key)}
                  </span>
                ) : (
                  formatValue(lead, key)
                )}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
