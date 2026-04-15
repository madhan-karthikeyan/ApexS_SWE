import json
from pathlib import Path
import pandas as pd

tex = Path('files/APEX_S_IEEE_Paper.tex').read_text(encoding='utf-8')
metrics = json.loads(Path('files/paper_table_metrics.json').read_text(encoding='utf-8'))

paths = {
    'Spring XD':'files/cleaned_datasets/spring_xd_clean.csv',
    'Usergrid':'files/cleaned_datasets/usergrid_clean.csv',
    'Aurora':'files/cleaned_datasets/aurora_clean.csv',
    'TAWOS':'tawos/paper_datasets/tawos_apex_clean.csv'
}

print('=== DATASET SUMMARY CHECK ===')
total_stories=0
total_sprints=0
for n,p in paths.items():
    df=pd.read_csv(p)
    total_stories += len(df)
    sprint_col='sprint_id' if 'sprint_id' in df.columns else None
    sprint_grps = int(df[sprint_col].nunique(dropna=True)) if sprint_col else 0
    total_sprints += sprint_grps
    dep_rows = 0
    if 'depends_on' in df.columns:
        dep_rows = int(df['depends_on'].astype(str).str.strip().replace({'nan':''}).ne('').sum())
    mean_bv = float(df['business_value'].mean()) if 'business_value' in df.columns else 0.0
    mean_risk = float(df['risk_score'].mean()) if 'risk_score' in df.columns else 0.0
    print(f"{n}: stories={len(df)} sprint_grps={sprint_grps} dep_rows={dep_rows} mean_bv={mean_bv:.2f} mean_risk={mean_risk:.2f}")
print(f"TOTAL: stories={total_stories} sprint_grps={total_sprints}")

print('\n=== PERF TABLE SOURCE (JSON) ===')
for n in ['Spring XD','Usergrid','Aurora','TAWOS']:
    m=metrics[n]['apex']
    print(f"{n}: selected={m['selected']} deliv_bv={m['deliv_bv']:.2f} used_sp={m['used_sp']} avg_risk={m['avg_risk']:.3f} dep_sat={m['dep_sat']*100:.2f}% sprint_compl={m['sprint_compl']:.2f} skill_cov={m['skill_cov']*100:.2f}%")

print('\n=== BASE TABLE SOURCE (JSON) ===')
for n in ['Spring XD','Usergrid','Aurora','TAWOS']:
    m=metrics[n]['baseline']
    print(f"{n}: selected={m['selected']} deliv_bv={m['deliv_bv']:.2f} used_sp={m['used_sp']} avg_risk={m['avg_risk']:.3f} dep_sat={m['dep_sat']*100:.2f}%")

print('\n=== STALE-CLAIM SCAN ===')
needles = [
    'selected stories averaged 3.222 story points and 0.111 risk',
    'rejected stories averaged 5.455 story points and 0.282 risk',
    'selected 8 stories with a delivered value of 70',
    'selected 9 stories, delivered value 73',
    'All 20 automated tests passed',
]
for needle in needles:
    print(f"{needle} -> {needle in tex}")
