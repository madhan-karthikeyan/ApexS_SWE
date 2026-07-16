import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import DatasetUpload from './pages/DatasetUpload'
import SprintConfiguration from './pages/SprintConfiguration'
import OptimizationProcessing from './pages/OptimizationProcessing'
import GeneratedSprintPlan from './pages/GeneratedSprintPlan'
import ExplainabilityPanel from './pages/ExplainabilityPanel'
import SprintPlanApproval from './pages/SprintPlanApproval'
import Reports from './pages/Reports'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/upload" element={<DatasetUpload />} />
      <Route path="/configure" element={<SprintConfiguration />} />
      <Route path="/optimizing/:jobId" element={<OptimizationProcessing />} />
      <Route path="/plan/:planId" element={<GeneratedSprintPlan />} />
      <Route path="/explain/:planId" element={<ExplainabilityPanel />} />
      <Route path="/approve/:planId" element={<SprintPlanApproval />} />
      <Route path="/reports/:teamId" element={<Reports />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
