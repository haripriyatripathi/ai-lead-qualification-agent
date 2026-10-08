import React from 'react'

export default function AnalyticsCards({ data }) {
  if (!data) return null

  const cards = [
    { label: 'Total Leads', value: data.total_leads, key: 'total_leads' },
    { label: 'High Priority', value: data.high_priority, key: 'high_priority' },
    { label: 'Medium Priority', value: data.medium_priority, key: 'medium_priority' },
    { label: 'Low Priority', value: data.low_priority, key: 'low_priority' },
    { label: 'Average Score', value: data.average_score ?? 0, key: 'average_score' },
  ]

  return (
    <div className="analytics-cards">
      {cards.map(({ label, value, key }) => (
        <div key={key} className="analytics-card">
          <div className="analytics-card-label">{label}</div>
          <div className="analytics-card-value">{value}</div>
        </div>
      ))}
    </div>
  )
}
