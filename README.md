# HR System

Own recruitment app: public careers site + recruiter workspace. Plan and progress: [docs/PLAN.md](docs/PLAN.md).
Backend layers: [backend/README.md](backend/README.md). Odoo was used only as a reference
(git tag `odoo-reference` keeps that code).

```
React + Vite + MUI (5173) --/api--> FastAPI (8000) --> Postgres "hr" (5432)
                                            └--SMTP--> Mailpit (dev inbox, 8025) or real SMTP
```

| Page | Who | What |
|---|---|---|
| `/careers`, `/careers/:id` | Public | Open jobs, apply form (CV: PDF/DOCX/TXT, max 5 MB, text extracted) |
| `/` | Recruiter (login) | Pipeline by stage, applicant panel (CV, stage, activity), create jobs |
| `/` → Interviews | Recruiter | Upcoming interviews |

Scheduling an interview: length comes from the job, past times and interviewer double-booking are
rejected, early-stage applicants move to `interview`, and both candidate and interviewer get an email
with an `.ics` invite (adds to Gmail/Outlook calendar). A mail failure keeps the booking and is shown.

## Project layout

```
docker-compose.yml           Postgres 16 + Mailpit
backend/app/
  main.py                    wires routers, maps service errors to HTTP
  config/                    settings (env), database
  modules/                   one folder per feature: jobs, applicants, interviews, auth
    <module>/                  controller -> service -> repository -> models (+ schemas)
  integrations/              CV files + text extraction, SMTP + .ics
  utils/                     errors, UTC helpers
  seed.py                    demo jobs
backend/tests/               API tests + service tests (no HTTP)
frontend/src/
  api.ts                     types, fetch helpers, token
  App.tsx                    /careers (public) vs recruiter area
  pages/                     Careers, Login, Board (pipeline), Interviews
  components/                ApplyForm, ApplicantDrawer, InterviewDialog, JobDialog
docs/PLAN.md                 decisions, progress, what is left
```

Layer rules and "where to change what": [backend/README.md](backend/README.md).

## Run

```bash
docker compose up -d                       # Postgres + Mailpit

cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env                       # set SECRET_KEY and RECRUITER_PASSWORD
python -m pytest -q                        # SQLite in memory, mail stubbed
python -m app.seed                         # runs migrations, then 3 demo jobs (skips if jobs exist)
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev                                # http://localhost:5173
```

Invitation emails land in Mailpit: http://localhost:8025. For real delivery set the Gmail SMTP values
in `backend/.env` (see comments in `.env.example`).

Database made before Alembic (tables already exist): run `alembic stamp 0001` once in `backend/`.
New column: edit the model, `alembic revision --autogenerate -m "..."`, then restart (startup upgrades).

The old Odoo database `db-hr-sys` is still in the same Postgres volume for reference.
Single recruiter account from `.env`: fine for a localhost demo, not for a public deployment.
