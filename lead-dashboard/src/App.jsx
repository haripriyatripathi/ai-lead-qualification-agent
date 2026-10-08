import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { getLeads, getAnalytics } from './services/api'
import AnalyticsCards from './components/AnalyticsCards'
import LeadDetailModal from './components/LeadDetailModal'
import LeadsTable from './components/LeadsTable'
import EmailModal from './components/EmailModal'
import ScoringRulesPage from './components/ScoringRulesPage'
import './App.css'

const REFRESH_INTERVAL_MS = 10000

function applyFiltersAndSort(leads, searchQuery, selectedPriority, sortOrder) {
  let result = [...leads]

  // 1. Search filter (industry or role_level, case insensitive)
  const q = (searchQuery || '').trim().toLowerCase()
  if (q) {
    result = result.filter(
      (lead) =>
        (lead.industry && lead.industry.toLowerCase().includes(q)) ||
        (lead.role_level && lead.role_level.toLowerCase().includes(q))
    )
  }

  // 2. Priority filter
  if (selectedPriority && selectedPriority !== 'All') {
    result = result.filter((lead) => (lead.priority || '') === selectedPriority)
  }

  // 3. Sort by final_score
  result.sort((a, b) => {
    const scoreA = a.final_score != null ? a.final_score : -1
    const scoreB = b.final_score != null ? b.final_score : -1
    if (sortOrder === 'desc') return scoreB - scoreA
    return scoreA - scoreB
  })

  return result
}

function App() {
  const [analytics, setAnalytics] = useState(null)
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedPriority, setSelectedPriority] = useState('All')
  const [sortOrder, setSortOrder] = useState('desc')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedLead, setSelectedLead] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [emailModalLead, setEmailModalLead] = useState(null)
  const [toast, setToast] = useState(null)
  const [view, setView] = useState('dashboard')

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(t)
  }, [toast])

  const openModal = (lead) => {
    setSelectedLead(lead)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setSelectedLead(null)
  }

  const openEmailModal = (lead) => setEmailModalLead(lead)
  const closeEmailModal = () => setEmailModalLead(null)
  const handleEmailSent = () => {
    fetchData()
  }
  const handleEmailError = (msg) => setToast(msg)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const [analyticsRes, leadsRes] = await Promise.all([
        getAnalytics(),
        getLeads(),
      ])
      setAnalytics(analyticsRes.data)
      setLeads(leadsRes.data)
    } catch (err) {
      setError(err.message || 'Failed to load data')
      setAnalytics(null)
      setLeads([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    const id = setInterval(fetchData, REFRESH_INTERVAL_MS)
    return () => clearInterval(id)
  }, [fetchData])

  const filteredLeads = useMemo(
    () => applyFiltersAndSort(leads, searchQuery, selectedPriority, sortOrder),
    [leads, searchQuery, selectedPriority, sortOrder]
  )

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Revenue Automation Dashboard</h1>
        <nav className="app-nav">
          <button
            type="button"
            className={`app-nav-btn ${view === 'dashboard' ? 'active' : ''}`}
            onClick={() => setView('dashboard')}
          >
            Dashboard
          </button>
          <button
            type="button"
            className={`app-nav-btn ${view === 'scoring-rules' ? 'active' : ''}`}
            onClick={() => setView('scoring-rules')}
          >
            Scoring Rules
          </button>
        </nav>
      </header>

      {view === 'scoring-rules' && <ScoringRulesPage />}

      {view === 'dashboard' && (
        <>
          {loading && (
            <div className="loading-wrap">
              <div className="spinner" aria-hidden="true" />
            </div>
          )}

          {error && (
            <div className="error">{error}</div>
          )}

          {!loading && !error && (
            <>
              <section className="section">
                <h2 className="section-title">Analytics</h2>
                <AnalyticsCards data={analytics} />
              </section>

              <section className="section">
                <h2 className="section-title">Leads</h2>
                <div className="leads-toolbar">
                  <input
                    type="search"
                    className="leads-search"
                    placeholder="Search by industry or role..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    aria-label="Search by industry or role level"
                  />
                  <select
                    className="leads-filter-select"
                    value={selectedPriority}
                    onChange={(e) => setSelectedPriority(e.target.value)}
                    aria-label="Filter by priority"
                  >
                    <option value="All">All</option>
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                    <option value="Very Low">Very Low</option>
                    <option value="Rejected">Rejected</option>
                  </select>
                  <button
                    type="button"
                    className="leads-sort-btn"
                    onClick={() => setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))}
                    aria-label={`Sort by final score ${sortOrder === 'desc' ? 'ascending' : 'descending'}`}
                  >
                    Sort by Final Score {sortOrder === 'desc' ? '↓' : '↑'}
                  </button>
                </div>
                <LeadsTable
                  leads={filteredLeads}
                  onRowClick={openModal}
                  onViewEmail={openEmailModal}
                  onSendEmail={openEmailModal}
                />
              </section>

              {isModalOpen && selectedLead && (
                <LeadDetailModal lead={selectedLead} onClose={closeModal} />
              )}
              {emailModalLead && (
                <EmailModal
                  lead={emailModalLead}
                  onClose={closeEmailModal}
                  onSent={handleEmailSent}
                  onError={handleEmailError}
                />
              )}
              {toast && (
                <div className="toast" role="alert">
                  {toast}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}

export default App
