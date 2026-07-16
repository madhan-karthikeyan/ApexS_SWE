import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../utils/api'
import { useSprintStore } from '../store/sprintStore'
import AppLayout from '../components/AppLayout'

const skills = ['Backend', 'Frontend', 'Database', 'Testing', 'DevOps']

export default function SprintConfiguration() {
  const navigate = useNavigate()
  const uploadId = useSprintStore((s) => s.uploadId)
  const sprintId = useSprintStore((s) => s.sprintId)
  const teamId = useSprintStore((s) => s.teamId) ?? '00000000-0000-0000-0000-000000000001'
  const sprintConfig = useSprintStore((s) => s.sprintConfig)
  const setSprintId = useSprintStore((s) => s.setSprintId)
  const setCurrentJobId = useSprintStore((s) => s.setCurrentJobId)
  const setSprintConfig = useSprintStore((s) => s.setSprintConfig)
  const [goal, setGoal] = useState(sprintConfig.goal)
  const [capacity, setCapacity] = useState(sprintConfig.capacity)
  const [riskThreshold, setRiskThreshold] = useState(sprintConfig.riskThreshold)
  const [selectedSkills, setSelectedSkills] = useState<string[]>(sprintConfig.selectedSkills)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const estimatedRiskLabel = riskThreshold <= 0.35 ? 'Strict (low-risk only)' : riskThreshold <= 0.7 ? 'Balanced' : 'Flexible'

  const createSprintAndGenerate = async () => {
    if (!uploadId) {
      setError('Please upload a dataset first.')
      return
    }
    setError(null)
    setLoading(true)
    setSprintConfig({ goal, capacity, riskThreshold, selectedSkills })

    try {
      const sprintResp = await api.post('/api/v1/sprints/', {
        team_id: teamId,
        goal,
        capacity,
        status: 'planning',
      })
      const newSprintId = sprintResp.data.sprint_id as string
      setSprintId(newSprintId)

      const planResp = await api.post('/api/v1/plans/generate', {
        sprint_id: newSprintId,
        capacity,
        risk_threshold: riskThreshold,
        available_skills: selectedSkills,
      })
      const nextJobId = planResp.data.job_id as string
      setCurrentJobId(nextJobId)
      navigate(`/optimizing/${nextJobId}`)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to create sprint and start optimization.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout
      title="Sprint Configuration"
      subtitle="Stage 2: Set constraints and trigger optimization"
      actions={<button className="btn" onClick={createSprintAndGenerate} disabled={uploadId == null || loading}>{loading ? 'Generating...' : 'Generate Plan'}</button>}
    >
      <div className="panel grid">
        <div className="field"><label>Sprint Goal</label><textarea rows={4} value={goal} onChange={(e) => setGoal(e.target.value)} /></div>
        <div className="field"><label>Capacity: {capacity}</label><input type="range" min={5} max={100} value={capacity} onChange={(e) => setCapacity(Number(e.target.value))} /></div>
        <div className="field">
          <label>Risk Threshold: {riskThreshold.toFixed(2)} <span className="muted">({estimatedRiskLabel})</span></label>
          <input type="range" min={0} max={1} step={0.05} value={riskThreshold} onChange={(e) => setRiskThreshold(Number(e.target.value))} />
        </div>
        <div className="row">
          {skills.map((skill) => (
            <button
              key={skill}
              type="button"
              className={`pill-btn ${selectedSkills.includes(skill) ? 'active' : ''}`}
              onClick={() => setSelectedSkills((prev) => prev.includes(skill) ? prev.filter((item) => item !== skill) : [...prev, skill])}
            >
              {skill}
            </button>
          ))}
        </div>
        {uploadId == null ? <div className="alert info">Upload dataset before generating a sprint plan.</div> : null}
        {selectedSkills.length === 0 ? <div className="alert info">No skill filter selected, all skills are treated as allowed.</div> : null}
        {error ? <div className="alert error">{error}</div> : null}
      </div>
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Current Inputs</h3>
        <div className="kpi-grid">
          <div className="kpi"><div className="label">Team</div><div className="value mono" style={{ fontSize: 13 }}>{teamId.slice(0, 8)}...</div></div>
          <div className="kpi"><div className="label">Dataset</div><div className="value" style={{ fontSize: 14 }}>{uploadId ? 'Linked' : 'Missing'}</div></div>
          <div className="kpi"><div className="label">Sprint ID</div><div className="value" style={{ fontSize: 14 }}>{sprintId ? `${sprintId.slice(0, 8)}...` : 'Not created'}</div></div>
          <div className="kpi"><div className="label">Skills</div><div className="value" style={{ fontSize: 14 }}>{selectedSkills.length || 'All'}</div></div>
        </div>
      </div>
    </AppLayout>
  )
}
