import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const getLeads = () => api.get('/leads')
export const getAnalytics = () => api.get('/analytics')
export const getScoringRules = () => api.get('/scoring-rules')
export const patchScoringRule = (id, data) => api.patch(`/scoring-rules/${id}`, data)
export const getLeadEmail = (leadId) => api.get(`/leads/${leadId}/email`)
export const sendLeadEmail = (leadId, data) => api.post(`/leads/${leadId}/send-email`, data)

export default api
