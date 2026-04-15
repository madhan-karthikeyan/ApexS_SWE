import type { Explanation } from '../types'

export default function ExplainCard({ explanation }: { explanation: Explanation | null }) {
  if (!explanation) return <div className="card">Select a story to view explanation.</div>

  const confidencePct = Math.max(0, Math.min(100, Math.round((explanation.confidence_score ?? 0) * 100)))

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <strong>{explanation.is_selected ? 'Selected' : 'Rejected'}</strong>
        <span className="badge info">Confidence {confidencePct}%</span>
      </div>
      <p style={{ marginBottom: 8 }}>{explanation.reason}</p>
      {explanation.rejection_reason ? <p className="muted">{explanation.rejection_reason}</p> : null}
      <div className="table-wrap" style={{ marginBottom: 10 }}>
      <table className="table">
        <tbody>
          <tr><td>Value Contribution</td><td>{explanation.value_weight ?? '-'}</td></tr>
          <tr><td>Risk Impact</td><td>{explanation.risk_impact ?? '-'}</td></tr>
          <tr><td>Alignment Score</td><td>{explanation.alignment_score ?? '-'}</td></tr>
        </tbody>
      </table>
      </div>
      <div className="progress"><div style={{ width: `${confidencePct}%` }} /></div>
    </div>
  )
}
