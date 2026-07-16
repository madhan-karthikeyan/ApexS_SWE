# TAWOS Pipeline For ApexS

This folder keeps the TAWOS workflow separate from the current cleaned CSV datasets.

It supports two ways to build the ApexS dataset:

1. direct from the downloaded `TAWOS.sql` dump
2. from an imported MySQL database

## Folder Layout

```text
tawos/
  .env.example
  requirements.txt
  import_tawos.ps1
  build_tawos_apex_dataset.py
  raw/
  exports/
  paper_datasets/
```

## Expected Inputs

- Put the downloaded TAWOS SQL dump in `tawos/raw/`
- Default example path: `tawos/raw/TAWOS.sql`

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r tawos\requirements.txt
Copy-Item tawos\.env.example tawos\.env
```

Update `tawos/.env` with your MySQL connection details.

## Fastest Path: Build Directly From The SQL Dump

This path does not require a local MySQL installation.

```powershell
python tawos\build_tawos_apex_dataset.py `
  --source sql-dump `
  --project-keys XD USERGRID MESOS
```

This will:

- read `tawos/raw/TAWOS.sql`
- export filtered raw slices into `tawos/exports/`
- generate the final ApexS dataset at `tawos/paper_datasets/tawos_apex_clean.csv`

## Optional Path: Import The SQL Dump Into MySQL

```powershell
powershell -ExecutionPolicy Bypass -File tawos\import_tawos.ps1 `
  -DumpPath tawos\raw\TAWOS.sql `
  -Database TAWOS_DB `
  -User root
```

If `mysql.exe` is not in `PATH`, pass `-MySqlExe "C:\Path\To\mysql.exe"`.

## Build From MySQL After Import

Default target projects are:

- `XD`
- `USERGRID`
- `MESOS`

Run:

```powershell
python tawos\build_tawos_apex_dataset.py `
  --source mysql `
  --project-keys XD USERGRID MESOS
```

This will export filtered raw slices into `tawos/exports/` and generate the final ApexS dataset at `tawos/paper_datasets/tawos_apex_clean.csv`.

## Optional Supporting Tables

If you also want filtered `Comment` and `Change_Log` exports for later feature engineering:

```powershell
python tawos\build_tawos_apex_dataset.py `
  --project-keys XD USERGRID MESOS `
  --include-supporting-tables
```

## Main Outputs

- `tawos/exports/selected_projects.csv`
- `tawos/exports/selected_issues.csv`
- `tawos/exports/selected_issue_links.csv`
- `tawos/exports/selected_comments.csv` when `--include-supporting-tables` is used
- `tawos/exports/selected_change_log.csv` when `--include-supporting-tables` is used
- `tawos/paper_datasets/tawos_apex_clean.csv`

## Notes

- The build script supports `--source auto`, which tries MySQL first and falls back to the SQL dump.
- The build script assumes the official TAWOS table names described in the official repository: `Project`, `Issue`, `Issue_Link`, `Comment`, and `Change_Log`.
- The final ApexS CSV is produced through the repo's existing `scripts/convert_tawos_export.py` converter so it stays aligned with the app's upload schema.
- If your local dump uses a different database name, keep the name in `tawos/.env` consistent with the imported database.

## Sources

- Official repository: <https://github.com/SOLAR-group/TAWOS>
- Download DOI: <https://doi.org/10.5522/04/21308124>
