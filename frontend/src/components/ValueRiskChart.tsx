import { useMemo, useState } from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  ReferenceDot,
  Legend,
  ZAxis,
} from 'recharts'

type ChartStory = {
  story_id: string
  title: string
  points: number
  value: number
  risk: number
  selected: boolean
  rejection_reason?: string | null
}

export default function ValueRiskChart({ stories, activeStoryId }: { stories: ChartStory[]; activeStoryId?: string }) {
  const [showSelected, setShowSelected] = useState(true)
  const [showRejected, setShowRejected] = useState(true)
  const [xMetric, setXMetric] = useState<'value' | 'points'>('value')

  const selectedData = stories.filter((s) => s.selected)
  const rejectedData = stories.filter((s) => !s.selected)
  const visibleStories = stories.filter((s) => (showSelected && s.selected) || (showRejected && !s.selected))
  const active = stories.find((s) => s.story_id === activeStoryId)

  const xDomain = useMemo<[number, number]>(() => {
    if (visibleStories.length === 0) return [0, 10]
    const vals = visibleStories.map((s) => (xMetric === 'value' ? s.value : s.points))
    const max = Math.max(...vals)
    return [0, Math.max(10, Math.ceil(max + 1))]
  }, [visibleStories, xMetric])

  return (
    <div className="card" style={{ minHeight: 390 }}>
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
        <strong>Value vs Risk Distribution</strong>
        <span className="muted">Green: selected | Red: rejected | Bubble size: story points</span>
      </div>

      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 10 }}>
        <div className="row">
          <button className={`pill-btn ${xMetric === 'value' ? 'active' : ''}`} onClick={() => setXMetric('value')} type="button">X: Business Value</button>
          <button className={`pill-btn ${xMetric === 'points' ? 'active' : ''}`} onClick={() => setXMetric('points')} type="button">X: Story Points</button>
        </div>
        <div className="row">
          <button className={`pill-btn ${showSelected ? 'active' : ''}`} onClick={() => setShowSelected((v) => !v)} type="button">Selected ({selectedData.length})</button>
          <button className={`pill-btn ${showRejected ? 'active' : ''}`} onClick={() => setShowRejected((v) => !v)} type="button">Rejected ({rejectedData.length})</button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={290}>
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" stroke="#d3e0d7" />
          <XAxis type="number" dataKey={xMetric} name={xMetric === 'value' ? 'Business Value' : 'Story Points'} domain={xDomain} />
          <YAxis type="number" dataKey="risk" name="Risk" domain={[0, 1]} />
          <ZAxis type="number" dataKey="points" range={[45, 260]} />
          <Tooltip
            formatter={(v: number, key: string) => {
              if (key === 'value') return [Number(v).toFixed(2), 'Business Value']
              if (key === 'points') return [Number(v).toFixed(0), 'Story Points']
              if (key === 'risk') return [Number(v).toFixed(2), 'Risk Score']
              return [v, key]
            }}
            labelFormatter={(_, payload) => {
              const row = payload?.[0]?.payload as ChartStory | undefined
              return row ? `${row.title} (${row.story_id})` : ''
            }}
          />
          <Legend />
          {showSelected ? <Scatter name="Selected" data={selectedData} fill="#0f766e" fillOpacity={0.84} /> : null}
          {showRejected ? <Scatter name="Rejected" data={rejectedData} fill="#dc2626" fillOpacity={0.84} /> : null}
          {active ? (
            <ReferenceDot
              x={xMetric === 'value' ? active.value : active.points}
              y={active.risk}
              r={10}
              stroke="#1d4ed8"
              strokeWidth={2}
              fill="none"
            />
          ) : null}
        </ScatterChart>
      </ResponsiveContainer>

      {active ? (
        <div className="alert info" style={{ marginTop: 10 }}>
          Active story: <strong>{active.title}</strong> ({active.story_id}) | Value {active.value.toFixed(2)} | Risk {active.risk.toFixed(2)} | Points {active.points}
        </div>
      ) : null}
    </div>
  )
}
