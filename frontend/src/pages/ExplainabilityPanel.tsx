import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import ExplainCard from '../components/ExplainCard'
import ValueRiskChart from '../components/ValueRiskChart'
import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { Explanation, Plan, Story } from '../types'
import AppLayout from '../components/AppLayout'

export default function ExplainabilityPanel() {
  const { planId } = useParams()
  const [storyId, setStoryId] = useState('')
  const [rejectedOffset, setRejectedOffset] = useState(0)
  const rejectedPageSize = 200

  const selectedExplanationsQuery = useQuery({
    queryKey: ['explanations', planId, 'selected'],
    queryFn: async () => {
      const { data } = await api.get<Explanation[]>(`/api/v1/plans/${planId}/explain`, {
        params: { selected: true, limit: 2000, offset: 0 },
      })
      return data
    },
    enabled: !!planId,
  })

  const rejectedExplanationsQuery = useQuery({
    queryKey: ['explanations', planId, 'rejected', rejectedOffset],
    queryFn: async () => {
      const { data } = await api.get<Explanation[]>(`/api/v1/plans/${planId}/explain`, {
        params: { selected: false, limit: rejectedPageSize, offset: rejectedOffset },
      })
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

  const planQuery = useQuery({
    queryKey: ['plan', planId],
    queryFn: async () => {
      const { data } = await api.get<Plan>(`/api/v1/plans/${planId}`)
      return data
    },
    enabled: !!planId,
  })

  const sprintStoriesQuery = useQuery({
    queryKey: ['sprintStories', planQuery.data?.sprint_id],
    queryFn: async () => {
      const { data } = await api.get<Story[]>(`/api/v1/sprints/${planQuery.data?.sprint_id}/stories`)
      return data
    },
    enabled: !!planQuery.data?.sprint_id,
  })

  const selectedExplanations = selectedExplanationsQuery.data ?? []
  const rejectedExplanations = rejectedExplanationsQuery.data ?? []
  const explanations = useMemo(
    () => [...selectedExplanations, ...rejectedExplanations],
    [selectedExplanations, rejectedExplanations],
  )
  const stories = storiesQuery.data ?? []
  const allStories = sprintStoriesQuery.data ?? stories
  const averageConfidence =
    selectedExplanations.length > 0
      ? selectedExplanations.reduce((sum, e) => sum + (e.confidence_score ?? 0), 0) / selectedExplanations.length
      : 0

  useEffect(() => {
    if (!storyId && explanations.length > 0) {
      setStoryId(explanations[0].story_id)
    }
  }, [explanations, storyId])

  const explanation = explanations.find((e) => e.story_id === storyId) ?? null

  const storyByIdMap = useMemo(() => new Map(allStories.map((s) => [s.story_id, s])), [allStories])
  const labelByStoryId = useMemo(() => new Map(stories.map((s) => [s.story_id, s.title])), [stories])
  const storyById = storyByIdMap.get(storyId)

  if (!planId) return <div className="app-shell">Invalid plan id.</div>
  if (selectedExplanationsQuery.isLoading || rejectedExplanationsQuery.isLoading || storiesQuery.isLoading || planQuery.isLoading || sprintStoriesQuery.isLoading) {
    return <div className="app-shell">Loading explanations...</div>
  }
  if (selectedExplanationsQuery.isError || rejectedExplanationsQuery.isError || storiesQuery.isError || planQuery.isError || sprintStoriesQuery.isError) {
    return <div className="app-shell">Failed to load explanations.</div>
  }

  const chartStories = explanations.map((e) => {
    const s = storyByIdMap.get(e.story_id)
    return {
      story_id: e.story_id,
      title: s?.title ?? e.story_id,
      points: s?.story_points ?? 0,
      value: s?.business_value ?? 0,
      risk: s?.risk_score ?? 0,
      selected: e.is_selected,
      rejection_reason: e.rejection_reason ?? e.reason,
    }
  })

  return (
    <AppLayout
      title="Explainability Panel"
      subtitle="Stage 6: Inspect selected and rejected story reasoning"
      actions={<button className="btn" onClick={() => window.history.back()}>Back</button>}
    >
      <div className="panel kpi-grid">
        <div className="kpi"><div className="label">Selected Explanations</div><div className="value">{selectedExplanations.length}</div></div>
        <div className="kpi"><div className="label">Rejected Explanations (loaded)</div><div className="value">{rejectedExplanations.length}</div></div>
        <div className="kpi"><div className="label">Average Confidence</div><div className="value">{Math.round(averageConfidence * 100)}%</div></div>
        <div className="kpi"><div className="label">Coverage</div><div className="value">{explanations.length > 0 ? 'Partial (paged)' : 'Empty'}</div></div>
      </div>

      <div className="panel">
        <div className="field">
          <label>Story</label>
          <select value={storyId} onChange={(e) => setStoryId(e.target.value)}>
            {explanations.map((e) => {
              const label = labelByStoryId.get(e.story_id) ?? e.story_id
              return (
                <option key={e.story_id} value={e.story_id}>
                  {label} {e.is_selected ? '(selected)' : '(rejected)'}
                </option>
              )
            })}
          </select>
        </div>
        {storyById ? <p className="muted">Story: {storyById.title}</p> : <p className="muted">Story metadata unavailable (rejected in optimization before selection).</p>}
      </div>
      <ExplainCard explanation={explanation} />
      <ValueRiskChart stories={chartStories} activeStoryId={storyId} />
      <div className="panel">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Rejected Stories (paged)</h2>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn secondary" disabled={rejectedOffset === 0} onClick={() => setRejectedOffset((v) => Math.max(0, v - rejectedPageSize))}>Prev</button>
            <span className="muted">Offset {rejectedOffset}</span>
            <button className="btn secondary" disabled={rejectedExplanations.length < rejectedPageSize} onClick={() => setRejectedOffset((v) => v + rejectedPageSize)}>Next</button>
          </div>
        </div>
        {rejectedExplanations.length === 0 ? (
          <p className="muted">No rejected stories in this page.</p>
        ) : (
          <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Story</th><th>Points</th><th>Risk</th><th>Reason</th></tr></thead>
            <tbody>
              {rejectedExplanations.map((e) => {
                const s = storyByIdMap.get(e.story_id)
                return (
                  <tr key={e.story_id}>
                    <td className="mono" style={{ fontSize: 12 }}>{e.story_id}</td>
                    <td>{s?.story_points ?? '-'}</td>
                    <td>{s?.risk_score != null ? s.risk_score.toFixed(2) : '-'}</td>
                    <td>{e.rejection_reason || e.reason}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
