# 🚀 ApexS: Context-Aware Sprint Planner

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB.svg?style=for-the-badge&logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?style=for-the-badge&logo=postgresql)
![Celery](https://img.shields.io/badge/Celery-Async-37814A.svg?style=for-the-badge&logo=celery)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=for-the-badge&logo=docker)

**ApexS** is an advanced, AI-assisted sprint planning platform. Instead of relying on manual point estimation and gut-feeling backlog grooming, ApexS uses **Integer Linear Programming (ILP)** to mathematically optimize sprint backlogs based on developer capacity, risk thresholds, required skills, and business value. 

Crucially, it features an **Explainability Engine** that translates complex ILP constraints into human-readable explanations, telling you exactly *why* a story was accepted or rejected.

---

## ✨ Key Features

- 🎯 **Constrained Optimization**: Solves the multidimensional knapsack problem to maximize business value while strictly respecting team capacity and risk tolerance.
- 🧠 **Explainable Decisions**: Transparent reasoning engine provides exact explanations for exclusions (e.g., *"Rejected: Exceeds backend skill capacity by 3 points"*).
- ⚡ **Decoupled Worker Architecture**: Heavy ILP optimization tasks are offloaded to a robust Celery + Redis pipeline.
- 📊 **Interactive Kanban Board**: A beautiful React-based interface to review generated plans, inspect explanations, manually adjust boundaries, and approve the sprint.
- 🐳 **Microservice Containerization**: Fully dockerized stack (6 isolated services) for one-click local execution.

---

## 🏗 Architecture & Tech Stack

ApexS is built on a modern, decoupled architecture designed for scalability and responsiveness.

| Component | Technology | Description |
|-----------|------------|-------------|
| **Frontend UI** | React, TypeScript, Vite, Zustand | Interactive planner interface and explainability dashboard. |
| **Backend API** | FastAPI, Python 3.11+ | High-performance async REST API routing. |
| **Data Layer** | PostgreSQL, SQLAlchemy, Alembic | Async relational persistence with schema versioning. |
| **Task Queue** | Celery, Redis | Decouples long-running ILP optimizations from the HTTP layer. |
| **Object Storage** | MinIO | S3-compatible local storage for raw dataset uploads. |
| **Optimization** | PuLP / CBC Solver | Mathematical constrained optimization engine. |

### System Data Flow
1. **Upload**: User uploads a backlog CSV to MinIO via FastAPI.
2. **Configure**: User defines the sprint constraints (capacity, max risk).
3. **Dispatch**: FastAPI enqueues a generation job to Redis.
4. **Optimize**: Celery worker runs ILP optimization and explainability extraction.
5. **Review**: React frontend polls for completion and visualizes the results.

---

## 🚀 Quick Start (Docker)

The easiest way to run the entire cluster is via Docker Compose.

### 1. Start the Cluster
```bash
# Clone the repository
git clone https://github.com/madhan-karthikeyan/ApexS_SWE.git
cd ApexS_SWE

# Setup environment variables
cp .env.example .env

# Spin up all 6 microservices
docker compose up --build -d
```

### 2. Access the Services
Once the cluster is healthy, access the platform locally:
- **Frontend App**: [http://localhost:5173](http://localhost:5173)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001)

### 3. Graceful Shutdown
```bash
docker compose down
```

---

## 📂 Project Structure

```text
ApexS_SWE/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # REST Endpoints
│   │   ├── models/           # SQLAlchemy ORM Models
│   │   ├── services/         # ILP Optimization & Explainability logic
│   │   └── workers/          # Celery Task Definitions
│   └── alembic/              # Database Migrations
├── frontend/                 # React Application
│   ├── src/
│   │   ├── components/       # Reusable UI & Kanban
│   │   ├── pages/            # View Routing
│   │   └── store/            # Zustand State
├── tests/                    # Pytest Suite (Unit & Integration)
├── tmp/                      # Sample datasets for testing
└── docker-compose.yml        # Infrastructure Definition
```

---

## 🧪 Testing

The platform includes a comprehensive Pytest suite that covers API integrations, ILP optimization correctness, and context extraction.

To run the tests locally (requires Python virtual environment):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

pytest tests/ -v
```

---

## 📊 Uploading Datasets

The platform expects CSV uploads with specific columns. You can use the provided converter script to transform a standard Jira export into an ApexS compatible format:

```bash
python scripts/convert_dataset.py jira_export.csv ready_for_apex.csv
```

**Required Columns:** `story_id`, `title`, `description`, `story_points`, `business_value`, `risk_score`, `required_skill`, `depends_on`.


