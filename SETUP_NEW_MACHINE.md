# ApexS System Setup Instructions (for new machine)

# 1. (Optional) Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install Python dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r tawos/requirements.txt

# 3. Install Node.js dependencies for frontend
cd frontend
npm install
cd ..

# 3b. Install Node.js dependencies at workspace root (if needed)
npm install

# 4. (Optional) Install Docker if you want to use Docker Compose stack
# Download and install Docker Desktop from https://www.docker.com/products/docker-desktop

# 5. (Optional) Start the full stack with Docker Compose
# docker compose up --build

# 6. (Optional) If using git, set up remote and pull latest changes
# git remote set-url origin https://github.com/MidhulKiruthik/Apex_Sprint.git
# git pull

# 7. (Optional) If using Jupyter or notebooks
# pip install notebook jupyterlab

# 8. (Optional) If using database migrations
# cd backend
# alembic upgrade head
# cd ..

# 9. (Optional) If using Celery worker
# cd backend/app
# celery -A workers.celery worker --loglevel=info
# cd ../..

# 10. (Optional) If using MinIO or other storage, ensure it is running

# 11. (Optional) If using pytest for tests
# pytest

# 11b. Quick local run (without Docker) for backend + frontend
# Terminal 1:
# powershell -ExecutionPolicy Bypass -File .\scripts\start_backend_local.ps1
#
# Terminal 2:
# powershell -ExecutionPolicy Bypass -File .\scripts\start_frontend_local.ps1
#
# Backend health:  http://localhost:8000/health
# Frontend:        http://localhost:5173
# API docs:        http://localhost:8000/docs

# 11c. Collect plan metrics for paper tables (backend must be running)
# powershell -ExecutionPolicy Bypass -File .\scripts\collect_plan_metrics.ps1
#
# Optional custom dataset:
# powershell -ExecutionPolicy Bypass -File .\scripts\collect_plan_metrics.ps1 -CsvPath "D:\SE\files\cleaned_datasets\spring_xd_clean.csv" -Capacity 30 -RiskThreshold 0.7

# 12. (Optional) If using VS Code, open the folder
# code .

# 13. (Optional) If you need to install additional system dependencies, do so as required

# End of setup instructions
