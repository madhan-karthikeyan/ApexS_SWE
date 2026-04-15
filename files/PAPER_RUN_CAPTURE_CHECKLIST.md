# Paper Run And Capture Checklist

Use only these four datasets in the paper:

- `files/cleaned_datasets/spring_xd_clean.csv`
- `files/cleaned_datasets/usergrid_clean.csv`
- `files/cleaned_datasets/aurora_clean.csv`
- `tawos/paper_datasets/tawos_apex_clean.csv`

Do not use `tmp/` datasets, Montgomery, or any other corpus in the final paper tables or figures.

## Freeze Step

Before running anything:

- Freeze the exact four CSV files above.
- Record file path, file size, and last modified time.
- Do not regenerate or edit the CSVs after the paper run set starts.
- Use one fixed ApexS configuration sheet for all main runs.

## Run Set A: Dataset Characteristics

Purpose:

- Fill `tab:dataset-summary`
- Produce `fig:dataset-size-distribution`
- Produce the five cross-dataset distribution figures

Run A1: Spring XD dataset stats
- Capture number of stories
- Capture number of sprint groups
- Capture rows with dependencies
- Capture status distribution
- Capture story-point distribution
- Capture mean `business_value`
- Capture mean `risk_score`

Run A2: Usergrid dataset stats
- Capture the same fields as A1

Run A3: Aurora dataset stats
- Capture the same fields as A1

Run A4: TAWOS dataset stats
- Capture the same fields as A1

Artifacts to save for Run Set A:
- one CSV or JSON summary per dataset
- one merged summary table across all four datasets
- one plotting input file for all cross-dataset graphs

## Run Set B: Main ApexS Planning Runs

Purpose:

- Fill `tab:performance-metrics`

Use one fixed main evaluation configuration per dataset.
Recommended to keep these fixed unless a dataset forces a justified exception:

- same risk threshold
- same planning objective mode
- same solver path
- same explanation settings
- same candidate-backlog selection rule

Run B1: Spring XD main ApexS run
- Capture selected stories
- Capture total delivered business value
- Capture total consumed story points
- Capture average selected risk
- Capture dependency satisfaction rate
- Capture sprint completion ratio
- Capture skill coverage rate

Run B2: Usergrid main ApexS run
- Capture the same fields as B1

Run B3: Aurora main ApexS run
- Capture the same fields as B1

Run B4: TAWOS main ApexS run
- Capture the same fields as B1

Artifacts to save for Run Set B:
- exported selected-story list
- full rejected-story list with reasons
- plan-level KPI summary
- run configuration used
- timestamp and dataset name

## Run Set C: Baseline Comparison Runs

Purpose:

- Fill `tab:baseline-comparison`

For every dataset, compare:

- `Baseline`: value-first feasible ranking
- `ApexS`: MILP-based planner

Important:

- use the same candidate backlog for both methods
- use the same risk threshold
- use the same skill availability definition
- use the same capacity

Run C1: Spring XD baseline vs ApexS
- Capture selected stories
- Capture delivered business value
- Capture used story points
- Capture average selected risk
- Capture dependency satisfaction rate

Run C2: Usergrid baseline vs ApexS
- Capture the same fields as C1

Run C3: Aurora baseline vs ApexS
- Capture the same fields as C1

Run C4: TAWOS baseline vs ApexS
- Capture the same fields as C1

Artifacts to save for Run Set C:
- side-by-side result file for each dataset
- one merged comparison sheet for the paper table

## Run Set D: Distribution Plots

Purpose:

- Fill the figure placeholders in the Results section

Run D1: Dataset size distribution
- one bar chart using all four datasets

Run D2: Business value distribution
- one boxplot or violin plot using all four datasets

Run D3: Risk score distribution
- one boxplot or violin plot using all four datasets

Run D4: Required skill distribution
- one stacked bar chart using all four datasets

Run D5: Status distribution
- one grouped or stacked bar chart using all four datasets

Run D6: Story-point histogram
- one grouped histogram or normalized bar chart using all four datasets

Artifacts to save for Run Set D:
- source plotting table
- final figure files in PDF or PNG
- short caption notes for each figure

## Run Set E: Case Study

Purpose:

- Fill `tab:case-study`

Choose one finalized planning run.
Recommended:

- pick a run where both selected and rejected stories are easy to explain
- prefer a dataset that is easy to discuss in prose
- use TAWOS only if the chosen slice remains readable in a compact table

Run E1: Case study extraction
- capture `story_id`
- capture `title`
- capture `story_points`
- capture `business_value`
- capture `risk_score`
- capture `required_skill`
- capture `selected / not selected`
- capture short ApexS explanation

Artifacts to save for Run Set E:
- one compact case-study table
- one raw exported plan file
- one raw explanation export

## Run Set F: Reproducibility Log

Purpose:

- support the methodology and discussion sections

For every paper run, record:

- dataset name
- dataset file path
- exact configuration
- solver used
- timestamp
- output file names

## Minimum Capture Bundle For The Paper

At the end, you should have:

- one frozen dataset summary sheet for all four datasets
- one performance metrics sheet for all four datasets
- one baseline comparison sheet for all four datasets
- six final figure files
- one case-study table
- one reproducibility log

## Direct Mapping To The LaTeX Results Section

- `tab:dataset-summary` <- Run Set A
- `fig:dataset-size-distribution` <- Run D1
- `fig:business-value-distribution` <- Run D2
- `fig:risk-score-distribution` <- Run D3
- `fig:required-skill-distribution` <- Run D4
- `fig:status-distribution` <- Run D5
- `fig:story-point-histogram` <- Run D6
- `tab:performance-metrics` <- Run Set B
- `tab:baseline-comparison` <- Run Set C
- `tab:case-study` <- Run Set E
