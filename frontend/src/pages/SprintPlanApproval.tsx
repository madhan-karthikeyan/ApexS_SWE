import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { Plan, Story } from '../types'
import AppLayout from '../components/AppLayout'
import { useState } from 'react'

export default function SprintPlanApproval() {
  const { planId } = useParams()
  const navigate = useNavigate()
  const [exportedAt, setExportedAt] = useState<string | null>(null)

  const planQuery = useQuery({
    queryKey: ['plan', planId],
    queryFn: async () => {
      const { data } = await api.get<Plan>(`/api/v1/plans/${planId}`)
      return data
    },
    enabled: !!planId,
  })

  const storiesQuery = useQuery({
    queryKey: ['planStories', planId],
    queryFn: async () => {
      const { data } = await api.get<Story[]>(`/api/v1/plans/${planId}/stories`)
      return data
    },
    enabled: !!planId,
  })

  const approveMutation = useMutation({
    mutationFn: async () => {
      await api.put(`/api/v1/plans/${planId}/approve`)
    },
    onSuccess: () => {
      planQuery.refetch()
    },
  })

  const exportMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/plans/${planId}/export?format=csv`, null, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `sprint_plan_${planId}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      setExportedAt(new Date().toLocaleTimeString())
    },
  })

  if (!planId) return <div className="app-shell">Invalid plan id.</div>
  if (planQuery.isLoading || storiesQuery.isLoading) return <div className="app-shell">Loading approval view...</div>
  if (planQuery.isError || storiesQuery.isError || !planQuery.data) return <div className="app-shell">Failed to load plan.</div>

  const plan = planQuery.data
  const stories = storiesQuery.data ?? []

  return (
    <AppLayout
      title="Sprint Plan Approval"
      subtitle="Stage 7 and 8: Approve finalized plan and export data"
      actions={<button className="btn ghost" onClick={() => navigate(`/plan/${planId}`)}>Back To Plan</button>}
    >
      <div className="panel">
        <p>Plan {planId} is ready for final approval.</p>
        <p>
          <strong>Status:</strong> {plan.status} | <strong>Stories:</strong> {stories.length} | <strong>Capacity Used:</strong> {plan.capacity_used}
        </p>
        <div className="kpi-grid" style={{ marginTop: 12 }}>
          <div className="kpi"><div className="label">Plan Status</div><div className="value mono" style={{ fontSize: 14 }}>{plan.status}</div></div>
          <div className="kpi"><div className="label">Selected Story Count</div><div className="value">{stories.length}</div></div>
          <div className="kpi"><div className="label">Export Ready</div><div className="value">{stories.length > 0 ? 'Yes' : 'No'}</div></div>
        </div>
        <div className="row">
          <button className="btn" onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending || plan.status === 'approved'}>
            {plan.status === 'approved' ? 'Approved' : approveMutation.isPending ? 'Approving...' : 'Approve'}
          </button>
          <button className="btn secondary" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
            {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
        {approveMutation.isError ? <div className="alert error" style={{ marginTop: 10 }}>Approval failed. Try again.</div> : null}
        {exportMutation.isError ? <div className="alert error" style={{ marginTop: 10 }}>Export failed. Try again.</div> : null}
        {exportedAt ? <div className="alert info" style={{ marginTop: 10 }}>Export completed at {exportedAt}.</div> : null}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Selected Stories Snapshot</h3>
        <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Story</th><th>Points</th><th>Value</th><th>Risk</th></tr>
          </thead>
          <tbody>
            {stories.map((story) => (
              <tr key={story.story_id}>
                <td>{story.title}</td>
                <td>{story.story_points}</td>
                <td>{story.business_value}</td>
                <td>{story.risk_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
    </AppLayout>
  )
}
