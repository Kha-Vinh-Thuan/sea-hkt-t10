# PLAN: HR System

Internal recruitment app. This repo owns jobs, applicants, CVs and interviews. Later, the AI pipeline
(jobhunter-platform: Filter → Schedule → Interview agents) plugs in on top through the service layer.

Update in place as work moves. Section 3 tracks progress.

## 1. Decisions so far

| Decision | Why |
|---|---|
| Rebuild instead of customizing Odoo | Odoo's UI is server-rendered XML per module, so a React UI meant running it headless behind an API key. We only need a small slice of it, so we own the code and the data model instead |
| Odoo kept as reference only | Git tag `odoo-reference` has the full Odoo code; database `db-hr-sys` is still in the Postgres volume |
| Removed `t10_ai_interview`, `rag_interview_agent`, `ml/` | Teammate experiments, not viable. The AI pipeline lives in jobhunter-platform |
| Stack: FastAPI + SQLModel + Postgres, React + Vite + MUI | Same stack as jobhunter-platform; one backend, no extra service |
| Backend split by feature module (`modules/jobs`, `applicants`, `interviews`, `auth`), each with controller → service → repository → models | Everything about one feature sits in one folder; services never import FastAPI, so AI agents can call the same rules later. Shared code in `config/`, `integrations/`, `utils/`. See `backend/README.md` |
| Fixed stages in code: new → screening → interview → offer → hired / rejected | No admin screen needed for an MVP |
| Interview invite = email with `.ics` | Gmail/Outlook add it to the calendar with no OAuth. Google Calendar sync later |
| Mailpit in docker-compose for dev mail | Invitations can be tested without reaching real inboxes |
| One recruiter account from `.env`, HMAC-signed token | Enough for a localhost demo, no user table yet |
| No inbound mail (CV by email to an alias) | Needs a real mailbox and domain; the public apply form replaces it |

## 2. What Odoo gave for free and how it is covered

| Odoo feature | Status here |
|---|---|
| Jobs, applicants, stages | Done |
| Careers site + apply form | Done |
| CV storage + text extraction | Done (PDF/DOCX/TXT, 5 MB, random file names) |
| Outgoing mail | Done (SMTP; Mailpit in dev, Gmail app password for real) |
| Calendar invite | Done as `.ics` attachment |
| Activity log on applicants | Done (`activity` table) |
| Login and access rights | Partial: one recruiter account, no roles |
| Accept/Decline, reminders | Not done |
| Google Calendar two-way sync | Not done (was never enabled on our Odoo either) |
| Inbound mail gateway | Dropped |
| Admin CRUD for departments, skills, degrees | Dropped: plain text fields |

## 3. Progress

| # | Work | Status |
|---|---|---|
| 1 | Clean Odoo repo: remove AI addons and `ml/`, plain Odoo image | done |
| 2 | Remove Odoo, keep reference tag, Postgres-only compose | done |
| 3 | Backend: Job / Applicant / Activity tables, seed, careers + recruiter API | done |
| 4 | Apply flow: validation (file type/size, email, duplicate per job), CV text extraction | done |
| 5 | Frontend: careers list + job detail + apply form; recruiter board by stage; applicant panel; create job | done |
| 6 | Recruiter login (token), all recruiter routes require it | done |
| 7 | Interviews: book with job length, reject past times and interviewer clashes, auto move to `interview`, email `.ics` to candidate + interviewer, mail failure keeps booking | done |
| 8 | Interviews tab (upcoming list) | done |
| 9 | Backend restructured into feature modules (controller / service / repository / models), config + integrations + utils, service-level tests. Replaces the `api/` + `services/` layout of commit 194f4a2 | done (not committed yet) |
| 10 | Edit job screen (API `PUT /api/jobs/{id}` exists, UI missing) | next |
| 11 | Reschedule / cancel interview (update + cancel `.ics` with same UID) | todo |
| 12 | Migrations with Alembic (today a column change means dropping tables) | todo |
| 13 | Users table: several recruiters/interviewers, hashed passwords, roles | todo |
| 14 | Interviewer list per job (pick from users instead of typing an email) | todo |
| 15 | Search / filter applicants, drag-and-drop between stages | todo |
| 16 | Rejection email to candidates | todo |
| 17 | Google Calendar: read interviewer busy times (freebusy), create event with Meet link | later |
| 18 | Hook for jobhunter-platform agents: expose services as the provider the agents call | later, after harness specs |

Verified 2026-10-30: 10 backend tests pass (8 API, 2 service); frontend build and lint clean; full flow run
in a real browser (apply → login → schedule → invite with `interview.ics` received in Mailpit → Interviews tab);
live smoke test on Postgres + Mailpit after the module restructure.

## 4. Known limits (accepted for the demo)

- Recruiter API is protected by one shared account. Do not expose beyond localhost.
- Token is stored in `localStorage`. Move to an httpOnly cookie before going public.
- No rate limit on login or apply.
- Upload folder is local disk (`backend/uploads/`, gitignored). Use object storage if deployed.
- Times are stored in UTC; display uses the browser's timezone, emails use `TIMEZONE` from `.env`.

## 5. How to run

See the root `README.md`. In short: `docker compose up -d`, then `uvicorn app.main:app --reload --port 8000`
in `backend/`, then `npm run dev` in `frontend/`. Invitations show up at http://localhost:8025.
