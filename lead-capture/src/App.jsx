import React, { useState } from 'react'
import { submitLead } from './services/api'
import './App.css'

const INITIAL_FORM = {
  name: '',
  email: '',
  company: '',
  role: '',
  message: '',
}

const DASHBOARD_URL = 'http://localhost:5173'

function App() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [submitted, setSubmitted] = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    setError(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await submitLead({
        source: 'web-form',
        raw_payload: {
          name: form.name,
          email: form.email,
          company: form.company,
          role: form.role,
          message: form.message,
        },
      })
      setSubmitted(true)
      setForm(INITIAL_FORM)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        (Array.isArray(err.response?.data?.detail)
          ? err.response.data.detail.map((d) => d.msg || d).join(', ')
          : null) ||
        err.message ||
        'Failed to submit lead'
      setError(String(msg))
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="lead-capture-wrap">
        <div className="lead-capture-card lead-capture-success-card">
          <p className="lead-capture-success-title">Lead submitted successfully.</p>
          <p className="lead-capture-success-text">
            AI agent is analyzing it.
            <br />
            Check dashboard to see results.
          </p>
          <a
            href={DASHBOARD_URL}
            className="btn-primary btn-go-dashboard"
            rel="noopener noreferrer"
          >
            Go to Dashboard
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="lead-capture-wrap">
      <div className="lead-capture-card">
        <h1 className="lead-capture-title">Submit a Lead</h1>
        <p className="lead-capture-subtitle">
          Fill in the form below. The AI agent will analyze and score the lead.
        </p>

        <form className="lead-capture-form" onSubmit={handleSubmit}>
          {error && (
            <div className="lead-capture-error" role="alert">
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="lead-name">Name</label>
            <input
              id="lead-name"
              type="text"
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="John Doe"
              className="form-input"
              autoComplete="name"
            />
          </div>

          <div className="form-group">
            <label htmlFor="lead-email">Email</label>
            <input
              id="lead-email"
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="john@company.com"
              className="form-input"
              autoComplete="email"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="lead-company">Company</label>
            <input
              id="lead-company"
              type="text"
              name="company"
              value={form.company}
              onChange={handleChange}
              placeholder="Acme Inc."
              className="form-input"
              autoComplete="organization"
            />
          </div>

          <div className="form-group">
            <label htmlFor="lead-role">Role</label>
            <input
              id="lead-role"
              type="text"
              name="role"
              value={form.role}
              onChange={handleChange}
              placeholder="VP of Sales"
              className="form-input"
              autoComplete="organization-title"
            />
          </div>

          <div className="form-group">
            <label htmlFor="lead-message">Message</label>
            <textarea
              id="lead-message"
              name="message"
              value={form.message}
              onChange={handleChange}
              placeholder="I'm interested in AI automation for our sales team..."
              className="form-textarea"
              rows={6}
            />
          </div>

          <button
            type="submit"
            className="btn-primary lead-capture-submit"
            disabled={submitting}
          >
            {submitting ? 'Submitting…' : 'Submit Lead'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default App
