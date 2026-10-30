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
| `/careers`, `/careers/:id` | Public | Jobs inside their open/close dates, filters (department, location, type, remote), apply form (CV PDF/DOCX/TXT max 5 MB, LinkedIn, short intro) |
| `/` | Recruiter (login) | Pipeline by stage with search, filters, drag-and-drop, archived view; create / edit jobs (dates, type, salary, hired / target, recruiter, manager, tags); applicant panel: CV, attachments, stars, tags, notes, salaries, owner, next step, refuse with reason, archive / restore, copy to job, talent pools, interviews, activity |
| `/` → Interviews | Recruiter | Upcoming interviews with status |
| `/` → Reports | Recruiter | Per job: by stage, hired vs target, days to hire, source, refuse reason |
| `/` → Talent pools | Recruiter | Named groups of applicants to contact later |
| `/` → Users | Admin | Create users (admin / recruiter / interviewer), edit role, deactivate, reset password |
| `/` | Interviewer | Only their own interviews, with the Feedback action |

Interviews: length comes from the job, past times and interviewer double-booking are rejected, early-stage
applicants move to `interview`, candidate and interviewer get an `.ics` invite. Reschedule and cancel send an
update / cancel with the same UID, so Gmail/Outlook replace the event. After the interview: status done / no-show,
score 1–5, recommendation, notes.

Candidate emails: received (after apply), refusal (optional, with reason; "sorry to see you go" when the
applicant declined), congratulations (hired).
A mail failure never undoes the action; it is shown and written to the activity log.

## Project layout

```
docker-compose.yml           Postgres 16 + Mailpit
backend/app/
  main.py                    wires routers, maps service errors to HTTP
  config/                    settings (env), database
  modules/                   one folder per feature: jobs, applicants, interviews, users, auth, reports, talent_pools
    <module>/                  controller -> service -> repository -> models (+ schemas)
  integrations/              CV files + text extraction, SMTP + .ics
  utils/                     errors, UTC helpers
  seed.py                    demo jobs
backend/tests/               API tests + service tests (no HTTP)
frontend/src/
  api.ts                     types, fetch helpers, token
  App.tsx                    /careers (public) vs recruiter area
  pages/                     Careers, Login, Board (pipeline), Interviews, Users, Reports, Talent pools
  components/                ApplyForm, ApplicantDrawer, InterviewDialog, JobDialog
docs/PLAN.md                 decisions, progress, what is left
```

Layer rules and "where to change what": [backend/README.md](backend/README.md).

## Run

Before deploying to a real domain, go through the deploy checklist in [docs/PLAN.md](docs/PLAN.md) (section 4b):
Google redirect URI, `FRONTEND_URL`, `SECRET_KEY`, SMTP, CORS.

```bash
docker compose up -d                       # Postgres + Mailpit

cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env                       # set SECRET_KEY and RECRUITER_PASSWORD (first admin)
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
First admin comes from `.env`; more users on the Users page. Login is rate limited in memory: fine for a
localhost demo, not for a public deployment.
