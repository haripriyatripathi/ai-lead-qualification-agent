import React, { useState, useEffect, useCallback } from 'react'
import { getScoringRules, patchScoringRule } from '../services/api'

export default function ScoringRulesPage() {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [savingId, setSavingId] = useState(null)

  const fetchRules = useCallback(async () => {
    try {
      setError(null)
      const res = await getScoringRules()
      setRules(res.data)
    } catch (err) {
      setError(err.message || 'Failed to load scoring rules')
      setRules([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRules()
  }, [fetchRules])

  const handleWeightChange = (id, value) => {
    const n = parseInt(value, 10)
    if (Number.isNaN(n) && value !== '') return
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, weight: value === '' ? '' : n } : r))
    )
  }

  const handleActiveChange = (id, checked) => {
    setRules((prev) => prev.map((r) => (r.id === id ? { ...r, active: checked } : r)))
  }

  const handleSave = async (rule) => {
    const raw = rule.weight
    const weight = typeof raw === 'number' ? raw : (raw === '' ? 0 : parseInt(raw, 10))
    if (Number.isNaN(weight) || weight < 0) {
      setError('Weight must be a number >= 0')
      return
    }
    setSavingId(rule.id)
    setError(null)
    try {
      await patchScoringRule(rule.id, { weight, active: rule.active })
      await fetchRules()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save')
    } finally {
      setSavingId(null)
    }
  }

  if (loading) {
    return (
      <div className="loading-wrap">
        <div className="spinner" aria-hidden="true" />
      </div>
    )
  }

  if (error && !rules.length) {
    return <div className="error">{error}</div>
  }

  return (
    <section className="section">
      <h2 className="section-title">Scoring Rules</h2>
      {error && <div className="error">{error}</div>}
      <div className="rules-table-wrap">
        {rules.length === 0 ? (
          <div className="leads-empty">No scoring rules yet.</div>
        ) : (
          <table className="rules-table">
            <thead>
              <tr>
                <th>Rule Type</th>
                <th>Rule Value</th>
                <th>Weight</th>
                <th>Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td>{rule.rule_type}</td>
                  <td>{rule.rule_value}</td>
                  <td>
                    <input
                      type="number"
                      className="rules-weight-input"
                      min={0}
                      value={rule.weight}
                      onChange={(e) => handleWeightChange(rule.id, e.target.value)}
                      aria-label={`Weight for rule ${rule.id}`}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      className="rules-active-checkbox"
                      checked={rule.active}
                      onChange={(e) => handleActiveChange(rule.id, e.target.checked)}
                      aria-label={`Active for rule ${rule.id}`}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="rules-save-btn"
                      onClick={() => handleSave(rule)}
                      disabled={savingId === rule.id}
                    >
                      {savingId === rule.id ? 'Saving…' : 'Save'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
