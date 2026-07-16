import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import StoryTable from '../components/StoryTable'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { Plan, Story } from '../types'
import AppLayout from '../components/AppLayout'
import { useSprintStore } from '../store/sprintStore'

export default function GeneratedSprintPlan() {
  const { planId } = useParams()
  const navigate = useNavigate()
  const sprintConfig = useSprintStore((s) => s.sprintConfig)
  const setCurrentJobId = useSprintStore((s) => s.setCurrentJobId)
  const [modCapacity, setModCapacity] = useState(sprintConfig.capacity)
  const [modRisk, setModRisk] = useState(sprintConfig.riskThreshold)
  const [modSkills, setModSkills] = useState<string>(sprintConfig.selectedSkills.join(','))

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

  const plan = planQuery.data
  const stories = storiesQuery.data ?? []
  const duplicateCount = new Set(stories.map((s) => s.story_id)).size !== stories.length
  const riskViolations = stories.filter((s) => s.risk_score > sprintConfig.riskThreshold).length
  const skillViolations =
    sprintConfig.selectedSkills.length === 0
      ? 0
      : stories.filter((s) => s.required_skill && !sprintConfig.selectedSkills.includes(s.required_skill)).length
  const dependencyViolations = stories.filter((s) => (s.depends_on ?? []).some((dep) => !stories.some((item) => item.story_id === dep))).length
  const constraintViolations = (duplicateCount ? 1 : 0) + riskViolations + skillViolations + dependencyViolations

  const modifyMutation = useMutation({
    mutationFn: async () => {
      const skills = modSkills
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      const { data } = await api.put<{ job_id: string }>(`/api/v1/plans/${planId}/modify`, {
        capacity: modCapacity,
        risk_threshold: modRisk,
        available_skills: skills,
      })
      return data
    },
    onSuccess: (data) => {
      setCurrentJobId(data.job_id)
      navigate(`/optimizing/${data.job_id}`)
    },
  })

  if (!planId) return <div className="app-shell">Invalid plan id.</div>
  if (planQuery.isLoading || storiesQuery.isLoading) return <div className="app-shell">Loading plan...</div>
  if (planQuery.isError || storiesQuery.isError || !plan) return <div className="app-shell">Failed to load plan.</div>

  return (
    <AppLayout
      title="Generated Sprint Plan"
      subtitle="Stage 4 and 5: Review selected stories and quality checks"
      actions={<button className="btn secondary" onClick={() => navigate(`/explain/${planId}`)}>View Explainability</button>}
    >
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div className="row">
          <button className="btn" onClick={() => navigate(`/approve/${planId}`)}>Approve</button>
          <button className="btn ghost" onClick={() => modifyMutation.mutate()} disabled={modifyMutation.isPending}>
            {modifyMutation.isPending ? 'Re-running...' : 'Modify and Re-run'}
          </button>
        </div>
      </div>
      <div className="panel">
        <h2>Modify Inputs</h2>
        <div className="grid two-col">
          <div className="field">
            <label>Capacity</label>
            <input type="number" min={1} value={modCapacity} onChange={(e) => setModCapacity(Number(e.target.value) || 1)} />
          </div>
          <div className="field">
            <label>Risk Threshold</label>
            <input type="number" min={0} max={1} step={0.05} value={modRisk} onChange={(e) => setModRisk(Number(e.target.value))} />
          </div>
        </div>
        <div className="field" style={{ marginTop: 10 }}>
          <label>Available Skills (comma-separated)</label>
          <input value={modSkills} onChange={(e) => setModSkills(e.target.value)} />
        </div>
        {modifyMutation.isError ? <div className="alert error" style={{ marginTop: 10 }}>Failed to modify and re-run plan.</div> : null}
      </div>
      <div className="panel">
        <div className="kpi-grid">
          <div className="kpi"><div className="label">Total Value</div><div className="value">{plan.total_value.toFixed(2)}</div></div>
          <div className="kpi"><div className="label">Capacity Used</div><div className="value">{plan.capacity_used}</div></div>
          <div className="kpi"><div className="label">Selected Stories</div><div className="value">{stories.length}</div></div>
          <div className="kpi"><div className="label">Plan Status</div><div className="value mono" style={{ fontSize: 14 }}>{plan.status}</div></div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          {plan.capacity_used <= sprintConfig.capacity ? <span className="badge success">Capacity within limit</span> : <span className="badge danger">Capacity exceeded</span>}
          {stories.length > 0 ? <span className="badge success">Stories selected</span> : <span className="badge danger">No selected stories</span>}
        </div>
      </div>
      <div className="panel">
        <h2>Plan Quality Checks</h2>
        <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Check</th><th>Result</th></tr>
          </thead>
          <tbody>
            <tr><td>Risk threshold compliance</td><td>{riskViolations === 0 ? 'Pass' : `Fail (${riskViolations} violations)`}</td></tr>
            <tr><td>Skill compatibility</td><td>{skillViolations === 0 ? 'Pass' : `Fail (${skillViolations} violations)`}</td></tr>
            <tr><td>Dependency satisfaction</td><td>{dependencyViolations === 0 ? 'Pass' : `Fail (${dependencyViolations} violations)`}</td></tr>
            <tr><td>Duplicate story IDs</td><td>{duplicateCount ? 'Fail (duplicates present)' : 'Pass'}</td></tr>
            <tr><td>Constraint violations</td><td>{constraintViolations === 0 ? '0 (Pass)' : `${constraintViolations} (Fail)`}</td></tr>
          </tbody>
        </table>
        </div>
      </div>
      <div className="panel">
        <StoryTable stories={stories} />
      </div>
    </AppLayout>
  )
}
