import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useDatasetUpload } from '../hooks/useDatasetUpload'
import { useSprintStore } from '../store/sprintStore'
import AppLayout from '../components/AppLayout'
import { api } from '../utils/api'
import type { Team } from '../types'

type DatasetEntry = {
  upload_id: string
  filename?: string | null
  row_count?: number | null
  uploaded_at?: string | null
  is_valid?: boolean | null
}

export default function DatasetUpload() {
  const [preview, setPreview] = useState<Record<string, string>[]>([])
  const [status, setStatus] = useState<string>('No file selected')
  const [error, setError] = useState<string | null>(null)
  const [columns, setColumns] = useState<string[]>([])
  const [rows, setRows] = useState<number>(0)
  const [filename, setFilename] = useState<string>('')
  const upload = useDatasetUpload()
  const teamId = useSprintStore((s) => s.teamId) ?? '00000000-0000-0000-0000-000000000001'
  const setUploadId = useSprintStore((s) => s.setUploadId)
  const setTeamId = useSprintStore((s) => s.setTeamId)
  const navigate = useNavigate()

  const teamsQuery = useQuery({
    queryKey: ['teams'],
    queryFn: async () => {
      const { data } = await api.get<Team[]>('/api/v1/teams/')
      return data
    },
  })

  const datasetsQuery = useQuery({
    queryKey: ['datasets', teamId],
    queryFn: async () => {
      const { data } = await api.get<DatasetEntry[]>(`/api/v1/datasets/${teamId}`)
      return data
    },
    enabled: !!teamId,
  })

  const parseCsvLine = (line: string): string[] => {
    const values: string[] = []
    let current = ''
    let inQuotes = false
    for (let i = 0; i < line.length; i += 1) {
      const char = line[i]
      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"'
          i += 1
        } else {
          inQuotes = !inQuotes
        }
        continue
      }
      if (char === ',' && !inQuotes) {
        values.push(current)
        current = ''
        continue
      }
      current += char
    }
    values.push(current)
    return values.map((v) => v.trim())
  }

  const onDrop = async (files: File[]) => {
    const file = files[0]
    if (!file) return
    setError(null)
    setFilename(file.name)
    setStatus('Uploading...')
    setTeamId(teamId)

    try {
      const text = await file.text()
      const fileRows = text.trim().split(/\r?\n/).filter(Boolean)
      const headers = fileRows.length > 0 ? parseCsvLine(fileRows[0]) : []
      setColumns(headers)
      setRows(Math.max(fileRows.length - 1, 0))
      setPreview(
        fileRows.slice(1, 11).map((row) => {
          const parts = parseCsvLine(row)
          return Object.fromEntries(headers.map((h, i) => [h, parts[i] ?? '']))
        }),
      )

      const formData = new FormData()
      formData.append('file', file)
      formData.append('team_id', teamId)
      const result = await upload.mutateAsync(formData)
      setUploadId(result.upload_id)
      setRows(result.rows)
      setColumns(result.columns)
      setPreview(result.preview ?? [])
      setStatus(result.is_valid ? 'Valid dataset' : 'Invalid dataset')
      navigate('/configure')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setStatus('Upload failed')
      setError(typeof detail === 'string' ? detail : 'Unable to upload dataset. Check CSV format and required columns.')
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { 'text/csv': ['.csv'] } })
  const statusClass = status === 'Valid dataset' ? 'success' : status === 'Upload failed' ? 'danger' : 'info'

  return (
    <AppLayout
      title="Dataset Upload"
      subtitle="Stage 1: Upload a team dataset and validate before configuration"
      actions={<button className="btn" onClick={() => navigate('/configure')} disabled={!upload.data?.upload_id && !filename}>Continue</button>}
    >
      <div className="grid two-col">
        <div {...getRootProps()} className={`card dropzone ${isDragActive ? 'active' : ''}`} style={{ padding: 28 }}>
          <input {...getInputProps()} />
          <h3 style={{ marginTop: 0 }}>Drop CSV Here</h3>
          <p>{isDragActive ? 'Release to upload this file' : 'Drag and drop CSV file here, or click to select.'}</p>
          <p className="muted">{filename || 'Required: story_id, story_points, business_value, risk_score'}</p>
        </div>
        <div className="panel">
          <div className="field" style={{ marginBottom: 10 }}>
            <label>Team</label>
            <select value={teamId} onChange={(e) => setTeamId(e.target.value)}>
              {(teamsQuery.data ?? []).map((team) => (
                <option key={team.team_id} value={team.team_id}>{team.name}</option>
              ))}
            </select>
          </div>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <strong>Status</strong>
            <span className={`badge ${statusClass}`}>{status}</span>
          </div>
          <div className="progress" style={{ marginTop: 12 }}>
            <div style={{ width: upload.isPending ? '55%' : status === 'Valid dataset' ? '100%' : '25%' }} />
          </div>
          <div className="kpi-grid" style={{ marginTop: 14 }}>
            <div className="kpi"><div className="label">Team</div><div className="value mono" style={{ fontSize: 13 }}>{teamId.slice(0, 8)}...</div></div>
            <div className="kpi"><div className="label">Rows</div><div className="value">{rows}</div></div>
            <div className="kpi"><div className="label">Columns</div><div className="value">{columns.length}</div></div>
          </div>
          {error ? <div className="alert error" style={{ marginTop: 12 }}>{error}</div> : null}
        </div>
      </div>

      <div className="panel">
        <h2>Preview</h2>
        <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>{preview[0] ? Object.keys(preview[0]).map((col) => <th key={col}>{col}</th>) : <th>Upload a file</th>}</tr>
          </thead>
          <tbody>
            {preview.map((row, idx) => <tr key={idx}>{Object.values(row).map((val, j) => <td key={j}>{String(val)}</td>)}</tr>)}
          </tbody>
        </table>
        </div>
      </div>

      <div className="panel">
        <h2>Datasets For Team</h2>
        {datasetsQuery.isLoading ? <p className="muted">Loading datasets...</p> : null}
        {!datasetsQuery.isLoading && (datasetsQuery.data ?? []).length === 0 ? <p className="muted">No uploads yet.</p> : null}
        {(datasetsQuery.data ?? []).length > 0 ? (
          <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Upload ID</th><th>File</th><th>Rows</th><th>Valid</th></tr>
            </thead>
            <tbody>
              {(datasetsQuery.data ?? []).map((entry) => (
                <tr key={entry.upload_id}>
                  <td className="mono" style={{ fontSize: 12 }}>{entry.upload_id.slice(0, 8)}...</td>
                  <td>{entry.filename ?? '-'}</td>
                  <td>{entry.row_count ?? 0}</td>
                  <td>{entry.is_valid ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : null}
      </div>
    </AppLayout>
  )
}
