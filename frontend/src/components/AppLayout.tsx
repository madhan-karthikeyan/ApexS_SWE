import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useSprintStore } from '../store/sprintStore'

type Props = {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}

export default function AppLayout({ title, subtitle, actions, children }: Props) {
  const location = useLocation()
  const uploadId = useSprintStore((s) => s.uploadId)
  const sprintId = useSprintStore((s) => s.sprintId)
  const currentJobId = useSprintStore((s) => s.currentJobId)
  const planId = useSprintStore((s) => s.planId)
  const teamId = useSprintStore((s) => s.teamId)

  const navItems = [
    { label: 'Dashboard', to: '/' },
    { label: 'Upload', to: '/upload' },
    { label: 'Configure', to: '/configure' },
    { label: 'Optimizing', to: currentJobId ? `/optimizing/${currentJobId}` : '/configure', disabled: !currentJobId },
    { label: 'Plan', to: planId ? `/plan/${planId}` : '/configure', disabled: !planId },
    { label: 'Explain', to: planId ? `/explain/${planId}` : '/configure', disabled: !planId },
    { label: 'Approve', to: planId ? `/approve/${planId}` : '/configure', disabled: !planId },
  ]

  return (
    <div className="app-shell grid" style={{ gap: 18 }}>
      <div className="app-topbar">
        <div className="brand">
          <div className="brand-mark" />
          <div>
            <div className="brand-title">Apex Sprint Planner</div>
            <div className="muted" style={{ fontSize: 13 }}>
              End-to-end planning workflow
            </div>
          </div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <a className="navlink" href="http://localhost:8000" target="_blank" rel="noreferrer">
            API
          </a>
          <a className="navlink" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
            Docs
          </a>
          <a className="navlink" href="http://localhost:9001" target="_blank" rel="noreferrer">
            MinIO
          </a>
        </div>
      </div>

      <div className="nav-pills">
        {navItems.map((item) => {
          const active = location.pathname === item.to || location.pathname.startsWith(`${item.to}/`)
          return (
            <Link
              key={item.label}
              to={item.to}
              className={`navlink ${active ? 'active' : ''}`}
              style={item.disabled ? { opacity: 0.55 } : undefined}
            >
              {item.label}
            </Link>
          )
        })}
      </div>

      <div className="page-title">
        <div>
          <h1 style={{ margin: 0 }}>{title}</h1>
          {subtitle ? <p className="muted" style={{ marginBottom: 0 }}>{subtitle}</p> : null}
        </div>
        {actions ? <div className="row">{actions}</div> : null}
      </div>

      <div className="workflow-strip">
        <span className={`workflow-pill ${uploadId ? '' : 'current'}`}>1. Upload</span>
        <span className={`workflow-pill ${uploadId && !sprintId ? 'current' : ''}`}>2. Configure</span>
        <span className={`workflow-pill ${currentJobId && !planId ? 'current' : ''}`}>3. Optimize</span>
        <span className={`workflow-pill ${planId ? 'current' : ''}`}>4. Plan + Explain + Approve</span>
      </div>

      <div className="status-board">
        <span className="status-chip">Team <code>{teamId ? `${teamId.slice(0, 8)}...` : 'Not selected'}</code></span>
        <span className="status-chip">Upload <code>{uploadId ? 'Ready' : 'Pending'}</code></span>
        <span className="status-chip">Sprint <code>{sprintId ? 'Created' : 'Pending'}</code></span>
        <span className="status-chip">Plan <code>{planId ? 'Generated' : 'Pending'}</code></span>
      </div>

      {children}
    </div>
  )
}
