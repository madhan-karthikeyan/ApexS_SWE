import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { api } from '../utils/api'
import type { Plan, Story } from '../types'
import AppLayout from '../components/AppLayout'

const COLUMNS: { id: string; title: string }[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'selected', title: 'Selected' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'review', title: 'Review' },
  { id: 'approved', title: 'Approved' },
]

function KanbanCard({ story }: { story: Story }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: story.story_id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`kanban-card ${isDragging ? 'dragging' : ''}`}
      {...attributes}
      {...listeners}
    >
      <div className="kanban-card-title">{story.title}</div>
      <div className="kanban-card-meta">
        <span>{story.story_points}pts</span>
        <span className="kanban-card-value">{story.business_value}v</span>
        {story.risk_score > 0.5 ? (
          <span className="kanban-card-risk">{story.risk_score.toFixed(1)}r</span>
        ) : (
          <span>{story.risk_score.toFixed(1)}r</span>
        )}
        {story.required_skill ? <span>{story.required_skill}</span> : null}
      </div>
    </div>
  )
}

function Column({ id, title, stories }: { id: string; title: string; stories: Story[] }) {
  const storyIds = useMemo(() => stories.map((s) => s.story_id), [stories])

  return (
    <div className="kanban-column">
      <div className="kanban-column-header">
        {title}
        <span className="kanban-column-count">{stories.length}</span>
      </div>
      <SortableContext items={storyIds} strategy={verticalListSortingStrategy}>
        {stories.map((story) => (
          <KanbanCard key={story.story_id} story={story} />
        ))}
      </SortableContext>
    </div>
  )
}

export default function SprintPlanApproval() {
  const { planId } = useParams()
  const navigate = useNavigate()
  const [exportedAt, setExportedAt] = useState<string | null>(null)
  const [columns, setColumns] = useState<Record<string, Story[]>>({
    backlog: [],
    selected: [],
    in_progress: [],
    review: [],
    approved: [],
  })
  const [activeStory, setActiveStory] = useState<Story | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor)
  )

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

  const allStoriesQuery = useQuery({
    queryKey: ['sprintStories', planQuery.data?.sprint_id],
    queryFn: async () => {
      const { data } = await api.get<Story[]>(
        `/api/v1/sprints/${planQuery.data?.sprint_id}/stories`
      )
      return data
    },
    enabled: !!planQuery.data?.sprint_id,
  })

  useEffect(() => {
    if (!allStoriesQuery.data) return
    const plan = planQuery.data
    const selectedIds = new Set(plan?.selected_stories ?? [])

    const grouped: Record<string, Story[]> = {
      backlog: [],
      selected: [],
      in_progress: [],
      review: [],
      approved: [],
    }

    for (const story of allStoriesQuery.data) {
      const status = story.status || 'backlog'
      if (grouped[status]) {
        grouped[status].push(story)
      } else if (selectedIds.has(story.story_id)) {
        grouped.selected.push(story)
      } else {
        grouped.backlog.push(story)
      }
    }

    setColumns(grouped)
  }, [allStoriesQuery.data, planQuery.data])

  const findColumn = useCallback(
    (storyId: string): string | null => {
      for (const [colId, stories] of Object.entries(columns)) {
        if (stories.some((s) => s.story_id === storyId)) return colId
      }
      return null
    },
    [columns]
  )

  function handleDragStart(event: DragStartEvent) {
    const storyId = String(event.active.id)
    for (const stories of Object.values(columns)) {
      const story = stories.find((s) => s.story_id === storyId)
      if (story) {
        setActiveStory(story)
        break
      }
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveStory(null)
    const { active, over } = event
    if (!over) return

    const storyId = String(active.id)
    const sourceCol = findColumn(storyId)

    let targetCol: string | null = null
    if (COLUMNS.some((c) => c.id === String(over.id))) {
      targetCol = String(over.id)
    } else {
      targetCol = findColumn(String(over.id))
    }

    if (!sourceCol || !targetCol || sourceCol === targetCol) return

    setColumns((prev) => {
      const source = [...prev[sourceCol]]
      const target = [...prev[targetCol]]
      const idx = source.findIndex((s) => s.story_id === storyId)
      if (idx === -1) return prev
      const [moved] = source.splice(idx, 1)
      if (!moved) return prev
      target.push(moved)

      return { ...prev, [sourceCol]: source, [targetCol]: target }
    })
  }

  const approveMutation = useMutation({
    mutationFn: async () => {
      await api.put(`/api/v1/plans/${planId}/approve`)
    },
    onSuccess: () => {
      planQuery.refetch()
    },
  })

  const exportMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(
        `/api/v1/plans/${planId}/export?format=csv`,
        null,
        { responseType: 'blob' }
      )
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `sprint_plan_${planId}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      setExportedAt(new Date().toLocaleTimeString())
    },
  })

  const statusMutation = useMutation({
    mutationFn: async (updates: { story_id: string; status: string }[]) => {
      await Promise.all(
        updates.map((u) =>
          api.put(`/api/v1/stories/${u.story_id}`, { status: u.status })
        )
      )
    },
  })

  async function handleApproveWithStatus() {
    const updates: { story_id: string; status: string }[] = []
    for (const [colId, stories] of Object.entries(columns)) {
      for (const story of stories) {
        if (story.status !== colId) {
          updates.push({ story_id: story.story_id, status: colId })
        }
      }
    }
    if (updates.length > 0) {
      await statusMutation.mutateAsync(updates)
    }
    approveMutation.mutate()
  }

  if (!planId) return <div className="app-shell">Invalid plan id.</div>
  if (planQuery.isLoading || storiesQuery.isLoading)
    return <div className="app-shell">Loading approval view...</div>
  if (planQuery.isError || !planQuery.data)
    return <div className="app-shell">Failed to load plan.</div>

  const plan = planQuery.data
  const totalItems = Object.values(columns).reduce((s, arr) => s + arr.length, 0)

  return (
    <AppLayout
      title="Sprint Plan Kanban"
      subtitle="Drag stories between columns to organize your sprint"
      actions={
        <button className="btn ghost" onClick={() => navigate(`/plan/${planId}`)}>
          Back To Plan
        </button>
      }
    >
      <div className="panel" style={{ marginBottom: 12 }}>
        <div className="kpi-grid">
          <div className="kpi">
            <div className="label">Plan Status</div>
            <div className="value mono" style={{ fontSize: 14 }}>
              {plan.status}
            </div>
          </div>
          <div className="kpi">
            <div className="label">Total Stories</div>
            <div className="value">{totalItems}</div>
          </div>
          <div className="kpi">
            <div className="label">Capacity Used</div>
            <div className="value">{plan.capacity_used}</div>
          </div>
          <div className="kpi">
            <div className="label">Total Value</div>
            <div className="value">{plan.total_value.toFixed(1)}</div>
          </div>
        </div>

        <div className="row" style={{ marginTop: 12 }}>
          <button
            className="btn"
            onClick={handleApproveWithStatus}
            disabled={
              approveMutation.isPending ||
              statusMutation.isPending ||
              plan.status === 'approved'
            }
          >
            {plan.status === 'approved'
              ? 'Approved'
              : approveMutation.isPending
                ? 'Approving...'
                : 'Approve & Sync Status'}
          </button>
          <button
            className="btn secondary"
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
          >
            {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
        {approveMutation.isError ? (
          <div className="alert error" style={{ marginTop: 10 }}>
            Approval failed. Try again.
          </div>
        ) : null}
        {statusMutation.isError ? (
          <div className="alert error" style={{ marginTop: 10 }}>
            Status sync failed. Try again.
          </div>
        ) : null}
        {exportedAt ? (
          <div className="alert info" style={{ marginTop: 10 }}>
            Export completed at {exportedAt}.
          </div>
        ) : null}
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="kanban-board">
          {COLUMNS.map((col) => (
            <Column
              key={col.id}
              id={col.id}
              title={col.title}
              stories={columns[col.id] || []}
            />
          ))}
        </div>
        <DragOverlay>
          {activeStory ? (
            <div className="kanban-card" style={{ cursor: 'grabbing' }}>
              <div className="kanban-card-title">{activeStory.title}</div>
              <div className="kanban-card-meta">
                <span>{activeStory.story_points}pts</span>
                <span className="kanban-card-value">
                  {activeStory.business_value}v
                </span>
              </div>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </AppLayout>
  )
}