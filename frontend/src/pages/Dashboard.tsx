import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '../components/AppLayout'
import { useSprintStore } from '../store/sprintStore'
import { api } from '../utils/api'

const DEFAULT_TEAM_ID = '00000000-0000-0000-0000-000000000001'

const cards = [
  { to: '/upload', title: 'Upload Dataset', desc: 'Import sprint history' },
  { to: '/configure', title: 'Configure Sprint', desc: 'Set goal and capacity' },
  { to: '/configure', title: 'Generate Plan', desc: 'Start optimization workflow' },
  { to: `/reports/${DEFAULT_TEAM_ID}`, title: 'Team Reports', desc: 'Velocity, value, and risk metrics' },
]

export default function Dashboard() {
  const resetWorkflow = useSprintStore((s) => s.resetWorkflow)
  const uploadId = useSprintStore((s) => s.uploadId)
  const planId = useSprintStore((s) => s.planId)

  const teamId = DEFAULT_TEAM_ID
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health')
      return data as { status: string; checks: Record<string, boolean>; request_count: number }
    },
    refetchInterval: 15000,
  })

  const metricsQuery = useQuery({
    queryKey: ['dashboardMetrics', teamId],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/reports/${teamId}/metrics`)
      return data as {
        sprint_velocity: number[]
        business_value: number[]
        risk_selected: number
        learning_sample_count: number
      }
    },
  })

  const health = healthQuery.data
  const velocitySeries = metricsQuery.data?.sprint_velocity ?? []
  const valueSeries = metricsQuery.data?.business_value ?? []
  const latestVelocity = velocitySeries.length > 0 ? velocitySeries[velocitySeries.length - 1] : 0
  const latestValue = valueSeries.length > 0 ? valueSeries[valueSeries.length - 1] : 0

  const optimizationBadgeClass = healthQuery.isLoading
    ? 'info'
    : healthQuery.isError
      ? 'danger'
      : health?.checks?.celery_enabled
        ? 'success'
        : 'danger'
  const optimizationLabel = healthQuery.isLoading
    ? 'Loading'
    : healthQuery.isError
      ? 'Error'
      : health?.checks?.celery_enabled
        ? 'Celery'
        : 'Unavailable'

  return (
    <AppLayout
      title="Dashboard"
      subtitle="Use this flow: upload dataset -> configure sprint -> optimize -> review explainability -> approve and export"
      actions={<button className="btn ghost" onClick={resetWorkflow}>Reset Workflow</button>}
    >
      <div className="panel hero-panel">
        <h2 style={{ marginTop: 0 }}>What To Do Next</h2>
        <div className="helper-grid">
          <div className="helper-item"><strong>Step 1</strong><p className="muted">Upload a CSV dataset for your team.</p></div>
          <div className="helper-item"><strong>Step 2</strong><p className="muted">Set sprint goal, capacity, risk, and skills.</p></div>
          <div className="helper-item"><strong>Step 3</strong><p className="muted">Run optimization and review quality checks.</p></div>
          <div className="helper-item"><strong>Step 4</strong><p className="muted">Approve plan and export CSV/JSON.</p></div>
        </div>
      </div>

      <div className="row">
        <span className="badge success">System Ready</span>
        {uploadId ? <span className="badge success">Dataset Uploaded</span> : <span className="badge info">Dataset Pending</span>}
        {planId ? <span className="badge success">Plan Available</span> : <span className="badge info">Plan Pending</span>}
      </div>
      <div className="grid cards">
        {cards.map((card) => (
          <Link key={`${card.to}-${card.title}`} to={card.to} className="card">
            <h3>{card.title}</h3>
            <p className="muted">{card.desc}</p>
          </Link>
        ))}
      </div>
      <div className="panel">
        <h2>System Overview</h2>
        <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Module</th><th>Status</th><th>Notes</th></tr></thead>
          <tbody>
            <tr>
              <td>API Health</td>
              <td>
                <span className={`badge ${health?.status === 'ok' ? 'success' : health ? 'danger' : 'info'}`}>
                  {health?.status ?? 'Loading'}
                </span>
              </td>
              <td>Live from /health endpoint</td>
            </tr>
            <tr>
              <td>Optimization Engine</td>
              <td><span className={`badge ${optimizationBadgeClass}`}>{optimizationLabel}</span></td>
              <td>Celery + Redis execution path</td>
            </tr>
            <tr>
              <td>Learning Dataset</td>
              <td><span className="badge info">{metricsQuery.data?.learning_sample_count ?? 0} rows</span></td>
              <td>Samples used for context/weight learning</td>
            </tr>
            <tr>
              <td>Latest Team Metrics</td>
              <td><span className="badge success">Live</span></td>
              <td>Velocity {latestVelocity.toFixed(1)} | Value {latestValue.toFixed(1)} | Risk {((metricsQuery.data?.risk_selected ?? 0) * 100).toFixed(0)}%</td>
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </AppLayout>
  )
}
