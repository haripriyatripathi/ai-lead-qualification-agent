import React from 'react'

function getScoreBarClass(score) {
  if (score == null) return 'none'
  if (score >= 80) return 'green'
  if (score >= 60) return 'yellow'
  if (score >= 40) return 'gray'
  return 'gray'
}

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

function ScoreBar({ score }) {
  const pct = score != null ? Math.min(100, Math.max(0, score)) : 0
  const barClass = getScoreBarClass(score)
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-track">
        <div
          className={`score-bar-fill ${barClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="score-bar-text">{score != null ? score : '—'}</div>
    </div>
  )
}

export default function LeadsTable({ leads, onRowClick, onViewEmail, onSendEmail }) {
  if (!leads || !leads.length) {
    return (
      <div className="leads-table-wrap">
        <div className="leads-empty">No leads yet.</div>
      </div>
    )
  }

  return (
    <div className="leads-table-wrap">
      <table className="leads-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Company</th>
            <th>Summary</th>
            <th>Company Size</th>
            <th>Industry</th>
            <th>Role Level</th>
            <th>Intent Score</th>
            <th>Final Score</th>
            <th>Priority</th>
            <th>Confidence</th>
            <th>Email</th>
            <th>Email Actions</th>
            <th>Created At</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr
              key={lead.id}
              className={onRowClick ? 'leads-table-row-clickable' : ''}
              onClick={onRowClick ? () => onRowClick(lead) : undefined}
              role={onRowClick ? 'button' : undefined}
            >
              <td>{lead.id}</td>
              <td>{lead.name ?? '—'}</td>
              <td>{lead.company ?? '—'}</td>
              <td className="leads-table-summary">{lead.message_summary ?? '—'}</td>
              <td>{lead.company_size ?? '—'}</td>
              <td>{lead.industry ?? '—'}</td>
              <td>{lead.role_level ?? '—'}</td>
              <td>{lead.intent_score ?? '—'}</td>
              <td>
                <ScoreBar score={lead.final_score} />
              </td>
              <td>
                <span className={`pill ${getPillClass(lead.priority)}`}>
                  {lead.priority ?? '—'}
                </span>
              </td>
              <td>
                <span className="confidence-badge" title="Confidence score">
                  {lead.confidence_score != null ? `${Math.min(100, Math.max(0, lead.confidence_score))}%` : '—'}
                </span>
              </td>
              <td>
                <span className={`email-status-badge ${lead.email_sent ? 'email-status-sent' : 'email-status-pending'}`}>
                  {lead.email_sent ? 'Sent ✔' : 'Pending'}
                </span>
              </td>
              <td className="leads-table-actions" onClick={(e) => e.stopPropagation()}>
                {lead.priority === 'High' && (
                  <>
                    <button
                      type="button"
                      className="btn-view-email"
                      onClick={() => onViewEmail && onViewEmail(lead)}
                    >
                      View Email
                    </button>
                    <button
                      type="button"
                      className="btn-send-email"
                      onClick={() => onSendEmail && onSendEmail(lead)}
                      disabled={lead.email_sent}
                    >
                      Send Email
                    </button>
                  </>
                )}
                {lead.priority !== 'High' && '—'}
              </td>
              <td>{formatDate(lead.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
