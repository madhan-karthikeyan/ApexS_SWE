export type Team = {
  team_id: string
  name: string
  team_size: number
  capacity: number
  skills: string[]
}

export type DatasetPreview = {
  upload_id: string
  rows: number
  preview: Record<string, string>[]
  columns: string[]
  is_valid: boolean
  errors: string[]
}

export type Sprint = {
  sprint_id: string
  team_id: string
  goal: string
  start_date?: string | null
  end_date?: string | null
  capacity: number
  status: string
}

export type Story = {
  story_id: string
  sprint_id: string
  title: string
  description?: string | null
  story_points: number
  business_value: number
  risk_score: number
  required_skill?: string | null
  depends_on: string[]
  status: string
}

export type PlanStatus = {
  status: string
  progress: number
  step: string
  plan_id?: string | null
  error?: string | null
}

export type Plan = {
  plan_id: string
  sprint_id: string
  selected_stories: string[]
  total_value: number
  total_risk: number
  capacity_used: number
  status: string
}

export type Explanation = {
  explanation_id?: string
  plan_id: string
  story_id: string
  is_selected: boolean
  reason: string
  value_weight?: number | null
  risk_impact?: number | null
  alignment_score?: number | null
  confidence_score: number
  rejection_reason?: string | null
}
