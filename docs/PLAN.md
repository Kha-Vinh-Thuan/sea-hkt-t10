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

## 2. Gap vs Odoo

Checked against Odoo source: `hr`, `hr_recruitment`, `hr_recruitment_skills`, `hr_recruitment_survey`,
`hr_recruitment_sms` (git tag `odoo-reference`) and `website_hr_recruitment` (inside the `odoo` docker image).
Every Odoo recruitment feature is listed here with a decision, so nothing is lost silently.
Decision: **done**, **#N** (planned, see section 3), **later** (wanted, after the demo), **dropped** (with reason).

### Job (`hr.job`)

| Odoo | Here | Decision |
|---|---|---|
| name, description, requirements, department | title, description, requirements, department (text) | done |
| address (work location) | location (text) | done |
| `no_of_recruitment` "Target" | `openings`, hired / target on the board | done (#19) |
| `no_of_hired_employee`, application counts | yes | done (#19) |
| open / close recruitment (`active`, `website_published`) | `is_open` | done |
| open and close dates (Odoo has none; our own) | yes | done (#19: `opens_on`, `closes_on`, apply blocked outside the window) |
| `employee_type_id` (full-time, intern...) | yes | done (#19) |
| `salary_min`, `salary_max`, `payment_interval` | salary range, monthly VND | done (#19); payment interval dropped (always monthly) |
| `expected_degree` | yes | done (#19, plain text) |
| `recruiter_id`, `manager_id`, `interviewer_ids` | none | #13 + #14 (needs users) |
| `tag_ids` (job tags) | none | later |
| `website_description`, `job_details` (rich public page) | plain text description | later: Markdown rendering |
| `survey_id` (interview form per job) | yes | done (#21, own scorecard instead of a survey) |
| `job_source_ids`, email alias per job | none | dropped: no inbound mail |
| `industry_id`, `company_id`, multi-company, currency | none | dropped: one company |
| color, favorite, sequence, documents on job | none | dropped: UI sugar |

### Applicant (`hr.applicant`)

| Odoo | Here | Decision |
|---|---|---|
| partner_name, email_from, partner_phone | name, email, phone | done |
| CV attachment | one CV file + extracted text | done; more attachments later |
| `stage_id`, `date_last_stage_update`, `last_stage_id` | `stage` + activity log + `stage_changed_at` | done (#20) |
| chatter (messages, tracking) | auto activity log + recruiter notes | done (#20) |
| `applicant_notes` | yes | done (#20) |
| `priority` (0–3 stars) | yes | done (#20) |
| `categ_ids` (tags) | yes | done (#20) |
| `linkedin_profile`, `availability` (start date) | yes | done (#20) |
| `type_id` (degree) | yes | done (#20, plain text) |
| `salary_expected`, `salary_proposed` (+ extra) | yes | done (#20) |
| `refuse_reason_id`, `refuse_date`, refuse email template | yes | done (#16) |
| refuse wizard: reason list (does not fit, refused by applicant: job fit / salary, job filled, duplicate, spam), optional mail | yes | done (#16: same reason list, mail optional) |
| mail templates: refuse, interest, congratulations (hired), not interested | yes | done (#16 refuse; #22 interest + congratulations); "not interested" template: later |
| `archive_applicant` / `reset_applicant` (restore to first stage) | yes | done (#20) |
| `action_job_add_applicants` (copy applicant to another job) | none | later |
| scheduled activities (to-do with deadline and owner, `mail.activity`) | none | later: "next step + due date" on applicant |
| attachments other than the CV (`attachment_ids`) | one CV | later |
| `application_status` (ongoing / hired / refused / archived), `active` | yes | done (#20: archive flag) |
| `kanban_state` (blocked / ready), stage `rotting_threshold_days` | none | later: "stuck for N days" badge |
| `recruiter_id`, `interviewer_ids` per applicant | none | #13 + #14 |
| `date_closed` (hire date), days to open / close, delay | none | later: simple reporting |
| duplicates by email / phone (`application_count`) | duplicate blocked per job only | later: "also applied to" in the panel |
| `skill_ids`, matching / missing skills, `matching_score` | CV text only | later: the Filter agent produces the score |
| talent pool (`talent_pool_ids`) | none | later |
| source / medium / campaign (UTM) | none | later: one `source` text field |
| `employee_id` (create employee on hire) | none | dropped: we stop at hired, no HR core |
| SMS (`hr_recruitment_sms`) | none | dropped: email only |
| `probability`, color, sequence, properties | none | dropped |

### Stages (`hr.recruitment.stage`)

| Odoo | Here | Decision |
|---|---|---|
| configurable stages, `fold`, `hired_stage`, per-job stages | fixed enum in code | dropped for MVP: no admin screen |
| default stages: New, Qualification, First Interview, Second Interview, Contract Proposal, Contract Signed | new, screening, interview, offer, hired, rejected | done; several interview rounds = several interviews in one `interview` stage |
| stage `requirements` text, email template on stage enter | none | later (rejection mail is #16) |

### Interviews (`calendar.event` + `hr_recruitment_survey`)

| Odoo | Here | Decision |
|---|---|---|
| meeting linked to applicant, attendees, invite mail | interview + `.ics` mail | done |
| reschedule / cancel with update mail | yes | done (#11) |
| attendee Accept / Decline, reminders | none | later |
| interview survey per applicant (scores, answers) | yes | done (#21: scorecard (score 1–5, verdict, notes) per interview) |
| interview status (done / no-show) | yes | done (#21) |
| Google / Outlook calendar sync | none | #17 |

### Platform features

| Odoo | Here | Decision |
|---|---|---|
| users, groups (officer / manager / interviewer) | one recruiter from `.env` | #13 |
| inbound mail gateway (CV to an alias) | public apply form | dropped: needs a real mailbox and domain |
| reporting, digest emails | none | later |
| multi-language website, i18n | English UI | dropped |
| careers list filters: country, department, office, remote, employment type | yes | done (#23: filter by department, location, remote, type) |
| job page: department, location, remote flag, employment type, publish toggle | yes | done (#19 adds remote + type; #23 shows them) |
| apply form: name, email, phone, LinkedIn, short introduction, CV | yes | done (#23: LinkedIn + short introduction) |
| `/jobs/add` (create job from the website) | recruiter board "New job" | done |
| job platforms (parse LinkedIn / Indeed / JobsDB mails) | none | dropped: needs inbound mail |
| CV OCR to fill applications (`hr_recruitment_extract`, paid) | text extraction only | dropped: Filter agent reads the CV text |
| talent pool (`hr.talent.pool`: name, manager, talents, tags) | none | later |
| department dashboard (new applicants, expected hires) | none | later: reporting |
| digest emails, guided tour, demo scenario | seed data | dropped |

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
| 9 | Backend restructured into feature modules (controller / service / repository / models), config + integrations + utils, service-level tests. Replaces the `api/` + `services/` layout of commit 194f4a2 | done (fe079a4) |
| 10 | Edit job screen (API `PUT /api/jobs/{id}` exists, UI missing) | done |
| 11 | Reschedule / cancel interview (update + cancel `.ics` with same UID) | done |
| 12 | Migrations with Alembic: `migrations/`, revision 0001 = current schema, app upgrades on startup, test checks models == migrations | done |
| 13 | Users table: several recruiters/interviewers, hashed passwords, roles | todo |
| 14 | Interviewer list per job (pick from users instead of typing an email) | todo |
| 15 | Search / filter applicants, drag-and-drop between stages | todo |
| 16 | Rejection email to candidates | done |
| 17 | Google Calendar: read interviewer busy times (freebusy), create event with Meet link | later |
| 18 | Hook for jobhunter-platform agents: expose services as the provider the agents call | later, after harness specs |
| 19 | Job fields: open/close dates (apply blocked outside), target vs hired, employment type, salary range, degree; edit job UI (#10) shows them | done |
| 20 | Applicant fields: notes, priority stars, tags, LinkedIn, start date, degree, expected/proposed salary, archive, last stage change date | done |
| 21 | Interview scorecard: score, verdict, notes per interview; status done / no-show | done |
| 22 | Candidate emails: interest (after apply) and congratulations (hired) | done |
| 23 | Careers site: filters (department, location, remote, type); apply form adds LinkedIn + short introduction | done |

#10, #11, #16, #19–#23 were built in parallel by three agents (jobs / applicants / interviews), then merged with one
migration (`0002`) and reviewed: shared SMTP code merged into `send_mail`, hired count moved to a query.

Next: #13 users + roles, then #14 interviewer list, #15 search / drag-and-drop. "later" rows of section 2 after that.

Verified 2026-10-30: 26 backend tests pass (API, services, applicant actions, interviews, migrations);
frontend build and lint clean; migration 0002 upgraded / downgraded / upgraded on Postgres with existing rows;
live run on Postgres + Mailpit: apply (interest mail) → edit fields → book → reschedule (same UID, SEQUENCE 1)
→ cancel (METHOD:CANCEL) → stage PATCH to rejected refused (422) → refuse with reason (refusal mail).

## 4. Known limits (accepted for the demo)

- Recruiter API is protected by one shared account. Do not expose beyond localhost.
- Token is stored in `localStorage`. Move to an httpOnly cookie before going public.
- No rate limit on login or apply.
- Upload folder is local disk (`backend/uploads/`, gitignored). Use object storage if deployed.
- Times are stored in UTC; display uses the browser's timezone, emails use `TIMEZONE` from `.env`.

## 5. How to run

See the root `README.md`. In short: `docker compose up -d`, then `uvicorn app.main:app --reload --port 8000`
in `backend/`, then `npm run dev` in `frontend/`. Invitations show up at http://localhost:8025.
