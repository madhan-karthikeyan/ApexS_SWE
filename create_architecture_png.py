#!/usr/bin/env python3
"""Generate a clean architecture diagram as PNG using matplotlib."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

fig, ax = plt.subplots(figsize=(12, 8), dpi=150)
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Colors for each layer
colors = {
    'client': '#E1F5FE',
    'presentation': '#FFF3E0',
    'gateway': '#F3E5F5',
    'logic': '#E8F5E9',
    'workers': '#FCE4EC',
    'data': '#E0F2F1',
    'storage': '#FFF9C4'
}

# Title
ax.text(5, 9.6, 'ApexS Five-Layer Architecture', fontsize=16, fontweight='bold', ha='center')

# Layer 1: Client (top)
client_box = FancyBboxPatch((3.5, 8.5), 3, 0.8, boxstyle="round,pad=0.05", 
                            edgecolor='black', facecolor=colors['client'], linewidth=2)
ax.add_patch(client_box)
ax.text(5, 8.9, 'CLIENT: Web Browser', fontsize=10, ha='center', fontweight='bold')

# Layer 2: Presentation
pres_box = FancyBboxPatch((3, 7.2), 4, 1, boxstyle="round,pad=0.05",
                          edgecolor='black', facecolor=colors['presentation'], linewidth=2)
ax.add_patch(pres_box)
ax.text(5, 7.9, 'PRESENTATION LAYER', fontsize=10, ha='center', fontweight='bold')
ax.text(5, 7.5, 'React 18 + Vite | Pages, Components, Hooks', fontsize=8, ha='center')

# Layer 3: API Gateway
gw_box = FancyBboxPatch((2.5, 5.9), 5, 1, boxstyle="round,pad=0.05",
                        edgecolor='black', facecolor=colors['gateway'], linewidth=2)
ax.add_patch(gw_box)
ax.text(5, 6.6, 'API GATEWAY - FastAPI', fontsize=10, ha='center', fontweight='bold')
ax.text(5, 6.2, '8 Route Groups: auth, teams, datasets, sprints, stories, plans, reports', fontsize=8, ha='center')

# Layer 4: Application Logic (split into 4 components)
logic_y = 3.8
logic_h = 1.5
ax.text(5, logic_y + 1.7, 'APPLICATION LOGIC LAYER', fontsize=10, ha='center', fontweight='bold')

# 4 components
components = [
    ('Optimization\nPuLP/CBC', 1),
    ('Explainability\nDecision Reasoning', 3),
    ('Context\nExtractor', 5),
    ('Weight\nLearning', 7)
]

for label, x in components:
    box = FancyBboxPatch((x-0.9, logic_y-0.4), 1.8, 0.8, boxstyle="round,pad=0.03",
                         edgecolor='black', facecolor=colors['logic'], linewidth=1.5)
    ax.add_patch(box)
    ax.text(x, logic_y, label, fontsize=7, ha='center', va='center')

# Layer 5: Workers
workers_box = FancyBboxPatch((0.5, 2.2), 3, 1, boxstyle="round,pad=0.05",
                             edgecolor='black', facecolor=colors['workers'], linewidth=2)
ax.add_patch(workers_box)
ax.text(2, 2.9, 'WORKER LAYER', fontsize=9, ha='center', fontweight='bold')
ax.text(2, 2.5, 'Celery: Async Job Queue', fontsize=8, ha='center')

# Layer 6: Data ORM
orm_box = FancyBboxPatch((6, 2.2), 3, 1, boxstyle="round,pad=0.05",
                         edgecolor='black', facecolor=colors['data'], linewidth=2)
ax.add_patch(orm_box)
ax.text(7.5, 2.9, 'DATA LAYER', fontsize=9, ha='center', fontweight='bold')
ax.text(7.5, 2.5, 'SQLAlchemy ORM Models', fontsize=8, ha='center')

# Layer 7: Storage
storage_y = 0.3
ax.text(5, storage_y + 1, 'STORAGE LAYER', fontsize=10, ha='center', fontweight='bold')

storage_components = [
    ('PostgreSQL 15\nRelational Data', 1.5),
    ('Redis 7\nCache/Broker', 5),
    ('MinIO\nCSV/JSON', 8.5)
]

for label, x in storage_components:
    box = FancyBboxPatch((x-0.9, storage_y-0.2), 1.8, 0.7, boxstyle="round,pad=0.03",
                         edgecolor='black', facecolor=colors['storage'], linewidth=1.5)
    ax.add_patch(box)
    ax.text(x, storage_y+0.15, label, fontsize=7, ha='center', va='center')

# Draw arrows showing data flow
arrow_props = dict(arrowstyle='->', lw=2, color='darkblue')

# Client to Presentation
ax.annotate('', xy=(5, 8.2), xytext=(5, 8.5), arrowprops=arrow_props)

# Presentation to Gateway
ax.annotate('', xy=(5, 6.9), xytext=(5, 7.2), arrowprops=arrow_props)

# Gateway to Logic
ax.annotate('', xy=(5, 5.3), xytext=(5, 5.9), arrowprops=arrow_props)

# Logic to Workers
ax.annotate('', xy=(2.5, 3.2), xytext=(3.5, 3.8), arrowprops=arrow_props)

# Workers to Data
ax.annotate('', xy=(6.5, 3.2), xytext=(5.5, 3.8), arrowprops=arrow_props)

# Data to Storage
ax.annotate('', xy=(7.5, 1.3), xytext=(7.5, 2.2), arrowprops=arrow_props)

plt.tight_layout()
plt.savefig(r'd:\SE\files\figs\architecture.png', dpi=150, bbox_inches='tight', facecolor='white')
print("[OK] Architecture diagram created: d:\\SE\\files\\figs\\architecture.png")
