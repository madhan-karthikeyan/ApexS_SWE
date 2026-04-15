param(
    [string]$CsvPath = "D:\SE\tests\fixtures\sample_sprint_data.csv",
    [int]$Capacity = 30,
    [double]$RiskThreshold = 0.7,
    [string[]]$Skills = @("Backend", "Frontend", "Database", "Testing")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-Json {
    param([string]$Url)
    return Invoke-RestMethod -Uri $Url -Method GET
}

function Post-Json {
    param([string]$Url, [hashtable]$Body)
    return Invoke-RestMethod -Uri $Url -Method POST -ContentType "application/json" -Body ($Body | ConvertTo-Json)
}

$base = "http://localhost:8000"
$teams = Get-Json "$base/api/v1/teams/"
if (-not $teams -or $teams.Count -lt 1) {
    throw "No team found. Start backend first and verify startup completed."
}
$teamId = $teams[0].team_id

if (-not (Test-Path $CsvPath)) {
    throw "CSV file not found: $CsvPath"
}

$upload = Invoke-RestMethod -Uri "$base/api/v1/datasets/upload" -Method POST -Form @{
    team_id = $teamId
    file = Get-Item $CsvPath
}

$sprint = Post-Json "$base/api/v1/sprints/" @{
    team_id = $teamId
    goal = "paper-metrics-run"
    capacity = $Capacity
    status = "planning"
}

$gen = Post-Json "$base/api/v1/plans/generate" @{
    sprint_id = $sprint.sprint_id
    capacity = $Capacity
    risk_threshold = $RiskThreshold
    available_skills = $Skills
}

$jobId = $gen.job_id
$status = $null
for ($i = 0; $i -lt 120; $i++) {
    $status = Get-Json "$base/api/v1/plans/status/$jobId"
    if ($status.status -eq "complete" -or $status.status -eq "failed") {
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $status -or $status.status -ne "complete") {
    throw "Plan generation failed or timed out: $($status | ConvertTo-Json -Compress)"
}

$planId = $status.plan_id
$plan = Get-Json "$base/api/v1/plans/$planId"
$selectedStories = Get-Json "$base/api/v1/plans/$planId/stories"
$allExplanations = Get-Json "$base/api/v1/plans/$planId/explain"
$selectedExplanations = Get-Json "$base/api/v1/plans/$planId/explain?selected=true"
$rejectedExplanations = Get-Json "$base/api/v1/plans/$planId/explain?selected=false"

$avgSelectedRisk = 0.0
if ($selectedStories.Count -gt 0) {
    $avgSelectedRisk = ($selectedStories | Measure-Object -Property risk_score -Average).Average
}

$result = [ordered]@{
    team_id = $teamId
    upload_id = $upload.upload_id
    sprint_id = $sprint.sprint_id
    job_id = $jobId
    plan_id = $planId
    selected_count = $selectedStories.Count
    explanation_count = $allExplanations.Count
    selected_explanations = $selectedExplanations.Count
    rejected_explanations = $rejectedExplanations.Count
    total_value = $plan.total_value
    total_risk = $plan.total_risk
    capacity_used = $plan.capacity_used
    avg_selected_risk = [Math]::Round($avgSelectedRisk, 4)
}

$result | ConvertTo-Json -Depth 4
