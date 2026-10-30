# HR System

Own recruitment app: public careers site + recruiter board. Odoo was used only as a reference
(git tag `odoo-reference` keeps that code).

```
React + Vite + MUI (5173) --/api--> FastAPI (8000) --> Postgres "hr" (5432, docker)
```

- `/careers`, `/careers/:id`: public job board and apply form (CV: PDF/DOCX/TXT, max 5 MB, text extracted)
- `/`: recruiter board: jobs, applicants by stage, CV text, activity log, create job

## Run

```bash
docker compose up -d                       # Postgres

cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python -m pytest -q                        # SQLite in memory, no Postgres needed
python -m app.seed                         # 3 demo jobs (skips if jobs exist)
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev                                # http://localhost:5173
```

The old Odoo database `db-hr-sys` is still in the same Postgres volume for reference.
Recruiter endpoints have no login yet: keep it on localhost.
