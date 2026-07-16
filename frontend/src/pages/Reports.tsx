import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import { CapacityBarChart, VelocityLineChart } from '../components/LineBarCharts'
import AppLayout from '../components/AppLayout'

type Metrics = {
  team_id: string
  sprint_velocity: number[]
  business_value: number[]
  risk_selected: number
  risk_rejected: number
  learning_sample_count: number
  learning_dataset_sources_count: number
  learning_mae: number | null
  learning_r2: number | null
  learning_feature_importance: Record<string, number>
  learning_model_type: string
  weight_evolution: Array<{
    urgency_weight: number
    value_weight: number
    alignment_weight: number
  }>
}

export default function Reports() {
  const { teamId } = useParams()

  const metricsQuery = useQuery({
    queryKey: ['metrics', teamId],
    queryFn: async () => {
      const { data } = await api.get<Metrics>(`/api/v1/reports/${teamId}/metrics`)
      return data
    },
    enabled: !!teamId,
  })

  const latestWeights = useMemo(() => {
    const history = metricsQuery.data?.weight_evolution ?? []
    return history.length > 0 ? history[history.length - 1] : null
  }, [metricsQuery.data])

  if (!teamId) return <div className="app-shell">Invalid team id.</div>
  if (metricsQuery.isLoading) return <div className="app-shell">Loading reports...</div>
  if (metricsQuery.isError || !metricsQuery.data) return <div className="app-shell">Failed to load reports.</div>

  const metrics = metricsQuery.data

  return (
    <AppLayout
      title="Team Reports"
      subtitle="Quality and historical trends for final reporting"
      actions={<button className="btn ghost" onClick={() => window.history.back()}>Back</button>}
    >
      <div className="panel">
        <p>
          <strong>Team:</strong> {metrics.team_id} | <strong>Risk Selected:</strong> {metrics.risk_selected.toFixed(2)} |
          <strong> Risk Rejected:</strong> {metrics.risk_rejected.toFixed(2)}
        </p>
      </div>

      <div className="panel">
        <h2>Sprint Velocity Trend</h2>
        <VelocityLineChart values={metrics.sprint_velocity} />
      </div>

      <div className="panel">
        <h2>Business Value Delivered</h2>
        <CapacityBarChart values={metrics.business_value} />
      </div>

      <div className="panel">
        <h2>Latest Weight Evolution Snapshot</h2>
        {latestWeights ? (
          <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Urgency</th><th>Value</th><th>Alignment</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>{latestWeights.urgency_weight.toFixed(3)}</td>
                <td>{latestWeights.value_weight.toFixed(3)}</td>
                <td>{latestWeights.alignment_weight.toFixed(3)}</td>
              </tr>
            </tbody>
          </table>
          </div>
        ) : (
          <p className="muted">No historical context weights found yet.</p>
        )}
      </div>

      <div className="panel">
        <h2>Learning Evaluation</h2>
        <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Model</th><th>Samples</th><th>Dataset Sources</th><th>MAE</th><th>R2</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>{metrics.learning_model_type}</td>
              <td>{metrics.learning_sample_count}</td>
              <td>{metrics.learning_dataset_sources_count}</td>
              <td>{metrics.learning_mae == null ? '-' : metrics.learning_mae.toFixed(4)}</td>
              <td>{metrics.learning_r2 == null ? '-' : metrics.learning_r2.toFixed(4)}</td>
            </tr>
          </tbody>
        </table>
        </div>
        <h3 style={{ marginTop: 12 }}>Feature Importance</h3>
        <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Feature</th><th>Weight</th></tr></thead>
          <tbody>
            {Object.entries(metrics.learning_feature_importance || {}).map(([feature, value]) => (
              <tr key={feature}><td>{feature}</td><td>{value.toFixed(4)}</td></tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
    </AppLayout>
  )
}
