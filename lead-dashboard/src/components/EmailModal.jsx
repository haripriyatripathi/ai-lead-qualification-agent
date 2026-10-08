import React, { useState, useEffect } from 'react'
import { getLeadEmail, sendLeadEmail } from '../services/api'

export default function EmailModal({ lead, onClose, onSent, onError }) {
  const [draft, setDraft] = useState(lead?.ai_email_draft ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sent, setSent] = useState(lead?.email_sent ?? false)

  useEffect(() => {
    if (!lead) return
    setDraft(lead.ai_email_draft ?? '')
    setSent(lead.email_sent ?? false)
    setError(null)
    if (!lead.ai_email_draft) {
      getLeadEmail(lead.id)
        .then((res) => {
          setDraft(res.data.draft_email || '')
        })
        .catch(() => setDraft(''))
    }
  }, [lead])

  const handleSend = async () => {
    if (!lead || sent) return
    setError(null)
    setLoading(true)
    try {
      await sendLeadEmail(lead.id, { edited_email: draft || undefined })
      setSent(true)
      onSent?.()
      onClose()
    } catch (err) {
      const raw = err.response?.data?.detail
      const msg = Array.isArray(raw) ? raw[0]?.msg || raw[0] : (typeof raw === 'string' ? raw : null) || err.message || 'Failed to send email'
      setError(msg)
      onError?.(msg)
    } finally {
      setLoading(false)
    }
  }

  if (!lead) return null

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="email-modal-title"
    >
      <div className="modal-card email-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 id="email-modal-title" className="modal-title">
            Email – Lead #{lead.id}
          </h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          {error && (
            <div className="email-modal-error" role="alert">
              {error}
            </div>
          )}
          <label className="email-modal-label" htmlFor="email-draft">
            Draft (edit if needed)
          </label>
          <textarea
            id="email-draft"
            className="email-modal-textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            readOnly={sent}
            rows={10}
          />
        </div>
        <div className="modal-footer">
          <button type="button" className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-send-email-primary"
            onClick={handleSend}
            disabled={loading || sent}
          >
            {sent ? 'Email Sent ✔' : loading ? 'Sending…' : 'Send Email'}
          </button>
        </div>
      </div>
    </div>
  )
}
