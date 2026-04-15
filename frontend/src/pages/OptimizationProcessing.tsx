import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { usePlanStatus } from '../hooks/usePlanStatus'
import ProgressStepper from '../components/ProgressStepper'
import { useSprintStore } from '../store/sprintStore'
import AppLayout from '../components/AppLayout'

const steps = ['loading', 'extracting', 'learning', 'optimizing', 'explaining', 'done']

export default function OptimizationProcessing() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const setPlanId = useSprintStore((s) => s.setPlanId)
  const { data } = usePlanStatus(jobId ?? null)

  useEffect(() => {
    if (data?.status === 'complete' && data.plan_id) {
      setPlanId(data.plan_id)
      navigate(`/plan/${data.plan_id}`)
    }
  }, [data, navigate, setPlanId])

  if (!jobId) return <div className="app-shell">Missing job id.</div>

  const step = (data?.step ?? 'loading').toLowerCase()

  return (
    <AppLayout title="Optimization Processing" subtitle="Stage 3: Polling async optimization pipeline">
      <div className="panel">
        <div className="progress"><div style={{ width: `${data?.progress ?? 0}%` }} /></div>
        <p className="mono" style={{ marginBottom: 4 }}>Job ID: {jobId}</p>
        <p style={{ marginTop: 8 }}>
          Step: <strong>{data?.step ?? 'Queued'}</strong> | Progress: <strong>{data?.progress ?? 0}%</strong>
        </p>
        {data?.status === 'failed' ? <div className="alert error">{data.error ?? 'Optimization failed.'}</div> : null}
        {data?.status !== 'failed' ? <div className="alert info" style={{ marginTop: 8 }}>Do not close this page while optimization is running. You will be redirected automatically once complete.</div> : null}
      </div>
      <ProgressStepper current={step} steps={steps} />
    </AppLayout>
  )
}
