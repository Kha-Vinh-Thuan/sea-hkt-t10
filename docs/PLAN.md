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
| Users table with roles admin / recruiter / interviewer; first admin created from `RECRUITER_EMAIL` / `RECRUITER_PASSWORD` on first login; HMAC-signed token, user reloaded on every request | No new dependency (stdlib scrypt); old `.env` keeps working; deactivation applies at once |
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
| `recruiter_id`, `manager_id`, `interviewer_ids` | interviewers per job (`job_interviewer`), recruiter + hiring manager per job | done (#14, #32) |
| `tag_ids` (job tags) | tags list, shown on the careers site | done (#32) |
| `website_description`, `job_details` (rich public page) | plain text, line breaks kept, bare URLs linked | done (#32); Markdown: dropped (no new dependency) |
| `survey_id` (interview form per job) | yes | done (#21, own scorecard instead of a survey) |
| `job_source_ids`, email alias per job | none | dropped: no inbound mail |
| `industry_id`, `company_id`, multi-company, currency | none | dropped: one company |
| color, favorite, sequence, documents on job | none | dropped: UI sugar |

### Applicant (`hr.applicant`)

| Odoo | Here | Decision |
|---|---|---|
| partner_name, email_from, partner_phone | name, email, phone | done |
| CV attachment | one CV file + extracted text, extra attachments | done (#33) |
| `stage_id`, `date_last_stage_update`, `last_stage_id` | `stage` + activity log + `stage_changed_at` | done (#20) |
| chatter (messages, tracking) | auto activity log + recruiter notes | done (#20) |
| `applicant_notes` | yes | done (#20) |
| `priority` (0–3 stars) | yes | done (#20) |
| `categ_ids` (tags) | yes | done (#20) |
| `linkedin_profile`, `availability` (start date) | yes | done (#20) |
| `type_id` (degree) | yes | done (#20, plain text) |
| `salary_expected`, `salary_proposed` (+ extra) | two numbers, monthly VND (assumption, see section 4) | done (#20); "extra" text fields dropped |
| `refuse_reason_id`, `refuse_date`, refuse email template | yes | done (#16) |
| refuse wizard: reason list (does not fit, refused by applicant: job fit / salary, job filled, duplicate, spam), optional mail | yes | done (#16: same reason list, mail optional) |
| mail templates: refuse, interest, congratulations (hired), not interested | yes | done (#16 refuse; #22 interest + congratulations; #33 "not interested" when the applicant declined) |
| `archive_applicant` / `reset_applicant` (restore to first stage) | archive / restore buttons; API `?archived=true` | done (#20); board "Show archived" view (#24) |
| `action_job_add_applicants` (copy applicant to another job) | copy to another job (`POST /applicants/{id}/copy`) | done (#33) |
| scheduled activities (to-do with deadline and owner, `mail.activity`) | `next_action` + `next_action_due`, overdue chip | done (#27); owner per to-do (#33) |
| attachments other than the CV (`attachment_ids`) | `applicant_attachment`: PDF/DOCX/TXT/PNG/JPG, 5 MB | done (#33) |
| `application_status` (ongoing / hired / refused / archived), `active` | yes | done (#20: archive flag) |
| `kanban_state` (blocked / ready), stage `rotting_threshold_days` | stuck-after-days per stage (`GET /api/stage-rules`), badge on cards + drawer | done (#27); blocked / ready flag dropped |
| `recruiter_id`, `interviewer_ids` per applicant | interviewer per interview, picked from the job's list | done (#14); recruiter owner per applicant + "Mine" board filter (#33) |
| `date_closed` (hire date), days to open / close, delay | `hired_at`, average days to hire in Reports | done (#34) |
| duplicates by email / phone (`application_count`) | "Also applied to" in the panel (same email any case, or same phone) | done (#27) |
| `skill_ids`, matching / missing skills, `matching_score` | CV text only | #18: the Filter agent produces the score |
| talent pool (`talent_pool_ids`) | pools picker in the drawer | done (#35) |
| source / medium / campaign (UTM) | `source` (careers site, LinkedIn, referral, job board, other) + detail; `?source=` on careers links | done (#27); medium / campaign dropped |
| `employee_id` (create employee on hire) | none | dropped: we stop at hired, no HR core |
| SMS (`hr_recruitment_sms`) | none | dropped: email only |
| `probability`, color, sequence, properties | none | dropped |

### Stages (`hr.recruitment.stage`)

| Odoo | Here | Decision |
|---|---|---|
| configurable stages, `fold`, `hired_stage`, per-job stages | fixed enum in code | dropped for MVP: no admin screen |
| default stages: New, Qualification, First Interview, Second Interview, Contract Proposal, Contract Signed | new, screening, interview, offer, hired, rejected | done; several interview rounds = several interviews in one `interview` stage |
| stage `requirements` text, email template on stage enter | requirements text per stage shown in the drawer; email on enter: dropped (interest / refuse / hired mails cover it) | done (#34) |

### Interviews (`calendar.event` + `hr_recruitment_survey`)

| Odoo | Here | Decision |
|---|---|---|
| meeting linked to applicant, attendees, invite mail | interview + `.ics` mail | done |
| reschedule / cancel with update mail | yes | done (#11) |
| attendee Accept / Decline, reminders | Accept / Decline links in the invite (public page); reminders skipped (need a scheduler) | done (#37), reminders later |
| interview survey per applicant (scores, answers) | yes | done (#21: scorecard (score 1–5, verdict, notes) per interview) |
| interview status (done / no-show) | yes | done (#21) |
| Google / Outlook calendar sync | Google per user (OAuth refresh token): free/busy, event + Meet link; Outlook none | done (#17) |

### Platform features

| Odoo | Here | Decision |
|---|---|---|
| users, groups (officer / manager / interviewer) | users table, roles admin / recruiter / interviewer, Users page | done (#13) |
| inbound mail gateway (CV to an alias) | public apply form | dropped: needs a real mailbox and domain |
| reporting, digest emails | Reports tab: by stage, hired vs target, days to hire, source, refuse reason | done (#34); digest emails: dropped |
| multi-language website, i18n | English UI | dropped |
| careers list filters: country, department, office, remote, employment type | yes | done (#23: filter by department, location, remote, type) |
| job page: department, location, remote flag, employment type, publish toggle | yes | done (#19 adds remote + type; #23 shows them) |
| apply form: name, email, phone, LinkedIn, short introduction, CV | yes | done (#23: LinkedIn + short introduction) |
| `/jobs/add` (create job from the website) | recruiter board "New job" | done |
| job platforms (parse LinkedIn / Indeed / JobsDB mails) | none | dropped: needs inbound mail |
| CV OCR to fill applications (`hr_recruitment_extract`, paid) | text extraction only | dropped: Filter agent reads the CV text |
| talent pool (`hr.talent.pool`: name, manager, talents, tags) | pools with members, Talent pools tab; pool manager / tags: dropped | done (#35) |
| department dashboard (new applicants, expected hires) | Reports tab per job | done (#34) |
| digest emails, guided tour, demo scenario | seed data | dropped |

### Other Odoo HR modules (not recruitment)

Checked by name and purpose; none feeds the hiring flow, which ends at `hired` (no employee record). Each one is
a product of its own (employee master data, payroll-adjacent rules), so building them would multiply the scope.
Revisit only if the product grows from "hiring" into "HR core"; `hr` (employee) would come first, the rest depend on it.

| Odoo module | What it is | Decision |
|---|---|---|
| `hr` (employees, departments, contracts) | employee master data | dropped: users + department text cover hiring; employee record = HR core |
| `hr_address_extended` | structured employee addresses | dropped: no employees |
| `hr_attendance`, `hr_presence`, `hr_holidays_attendance` | check-in / out, presence, overtime as leave | dropped: HR core |
| `hr_holidays` | leave requests and allocations | dropped: HR core |
| `hr_calendar` | working schedules in the calendar | dropped: interview slots only check interviewer clashes |
| `hr_calendar_google` | Google Calendar link for employees | #17 (interviewer free/busy only) |
| `hr_expense` | expense claims | dropped: finance |
| `hr_fleet` | company cars | dropped |
| `hr_gamification` | badges, challenges | dropped |
| `hr_livechat` | livechat operator stats | dropped: no livechat |
| `hr_maintenance` | equipment per employee | dropped |
| `hr_skills`, `hr_skills_event`, `hr_skills_slides`, `hr_skills_survey` | employee skills, certifications from courses | dropped; applicant skills: Filter agent (see Applicant `skill_ids`) |
| `hr_timesheet`, `hr_timesheet_attendance` | time tracking on projects | dropped: HR core |
| `hr_work_entry` | work entries for payroll | dropped: payroll |
| `hr_recruitment_sms` | SMS to applicants | dropped: email only |

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
| 13 | Users table: several recruiters/interviewers, hashed passwords, roles | done |
| 14 | Interviewer list per job (pick from users instead of typing an email) | done |
| 15 | Search / filter applicants, drag-and-drop between stages | done |
| 16 | Rejection email to candidates | done |
| 17 | Google Calendar: read interviewer busy times (freebusy), create event with Meet link | done (needs GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET to run for real) |
| 18 | Hook for jobhunter-platform agents: expose services as the provider the agents call | later: the platform will adapt to this app's API once the manual flow is done |
| 19 | Job fields: open/close dates (apply blocked outside), target vs hired, employment type, salary range, degree; edit job UI (#10) shows them | done |
| 20 | Applicant fields: notes, priority stars, tags, LinkedIn, start date, degree, expected/proposed salary, archive, last stage change date | done |
| 21 | Interview scorecard: score, verdict, notes per interview; status done / no-show | done |
| 22 | Candidate emails: interest (after apply) and congratulations (hired) | done |
| 23 | Careers site: filters (department, location, remote, type); apply form adds LinkedIn + short introduction | done |
| 24 | Board: "Show archived" view (API `GET /api/applicants?archived=true` exists; needs its own column or list) | done |
| 25 | Refuse dialog reads reasons from `GET /api/refuse-reasons` instead of its own label list | done |
| 26 | Recruiter screens clicked through in a browser: login, board, drag-and-drop (incl. drop on Rejected → Refuse dialog), drawer, Users page, interviewer view | done |
| 27 | Applicant extras: source, "also applied to", stuck-in-stage badge, next step + due date | done |
| 28 | Edit job / reschedule / feedback dialogs clicked through in a browser | done |
| 29 | Frontend reads stuck thresholds from `GET /api/stage-rules` instead of its own copy in `api.ts` | done |
| 30 | Drawer and Reports show refuse labels from the API (`REFUSE_REASON_LABEL` removed) | done |
| 31 | Login rate limit: 5 failures per client + email in 15 min, then 429 (in memory) | done |
| 32 | Job: recruiter + hiring manager, tags, linked URLs on the careers page | done |
| 33 | Applicant: copy to job, attachments, owner + "Mine" filter, to-do owner, "not interested" mail | done |
| 34 | Hire date, Reports tab, stage requirements in the drawer | done |
| 35 | Talent pools (tab + drawer picker) | done |
| 36 | Email composer (Odoo `mail.compose.message` + `mail.template`): editable templates (admin), compose from the drawer with a template prefilled, real SMTP send, sent mail in the activity log; moving into a stage that has a template opens the composer prefilled (human reviews, then sends) | done |
| 37 | Scheduling with the candidate: interviewer free slots (Google free/busy, else our interviews) inside working hours; propose times by email, candidate picks one on a public page; Accept / Decline links in the invite; Google event + Meet link when the interviewer connected Google | done; reminders later (need a scheduler) |
| 38 | Automation (agent) side: machine API `/api/agent/v1` (API key) shaped like the platform's `HiringProvider` (job, candidates, interviewers, availability); agent posts assessments (score, summary, skills) and approval requests; "Automation" inbox where a human approves / rejects; approved actions run through the same services; events pushed to the platform webhook (`event_id`, HMAC) | later (after the manual flow; platform follows this app) |
| 39 | Remote database for the team: CV + attachment files stored in the DB (not local disk), `pool_pre_ping`, SSL URL, one-off script to move existing uploads, run notes for a hosted Postgres | done (Supabase: use the Session pooler URL) |
| 40 | Team calendar (Odoo attendee calendar): week grid in the booking dialog with every job interviewer's busy blocks side by side (our interviews + Google free/busy, 90 s cache, never event titles); click a free cell to fill interviewer + start. Booking / rescheduling re-asks Google live and takes a per-interviewer Postgres advisory lock, so neither people nor a future agent can double-book; Google unreachable = book with a warning in the activity log | done |

#10, #11, #16, #19–#23 were built in parallel by three agents (jobs / applicants / interviews), then merged with one
migration (`0002`). #13–#15, #24–#27 the same way (users / board / applicant extras), migration `0003`.
Review fixes: shared SMTP code merged into `send_mail`, hired count as a query, merge conflicts in `api.ts` and the
applicants repository, duplicate Sign out button removed.

#32–#35 the same way (jobs / applicants / reports + pools), migration `0004`.

Round 5 (#17, #36, #37, #39): turn the app into a normal internal HR tool where every step can be done by hand
(drag stages, compose and send real mail, book on the interviewer's real calendar, let the candidate pick a time),
later the jobhunter-platform agents drive the same steps (#38); the HR app keeps the screens for anything that needs
a human. Round 5 does the manual flow only (#17, #36, #37, #39), three parallel agents, merged with migration `0005`.

Needs from the team: Google Cloud OAuth client (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), the hosted Postgres
URL. Code works without them (falls back to local data and Mailpit).

Verified 2026-10-30 (round 5): 72 backend tests pass; frontend build and lint clean; migration 0005 up / down / up on
Postgres, existing interviews got unique `response_token`s. Live on Postgres + Mailpit: CV bytes stored in and served
from the DB; 6 templates seeded; compose "offer" from template and send; interviewer free slots (73 in 7 days);
propose 3 times by email -> public `/book/:token` page books one (interview created, stage interview, invite with
Accept / Decline links), reusing the link gives 409; `/interview/:token` page records "declined". Google connect
returns 422 "not configured" until the OAuth client is set. Not tested against real Google yet.

Verified 2026-10-30 (#40): 76 backend tests pass (live Google re-check after a cached view, Google down = warning,
several interviewers, cache); build and lint clean. Browser: grid shows Techlead A busy Mon 10:00, click Tue 12:00
fills Techlead A + time, booking saved; an overlapping booking returns 409.

Verified 2026-10-30 (#28–#35): 53 backend tests pass; frontend build and lint clean; migration 0004 up / down / up
on Postgres. Browser: book, reschedule, feedback (saved: done, 4, hire), edit job target. Live API: job owners +
tags (public tags), copy to job (409 on repeat), attachment upload / download / cross-applicant 404 / .exe 422 /
delete, owner filter, talent pool add / delete, hire date, Reports, "Sorry to see you go" mail.

Verified 2026-10-30: 40 backend tests pass; frontend build and lint clean; migrations 0002 and 0003 upgraded /
downgraded / upgraded on Postgres with existing rows. Live on Postgres + Mailpit: apply → interest mail → book →
reschedule (same UID) → cancel (METHOD:CANCEL) → refuse with reason. Roles: bootstrap admin from `.env`, interviewer
sees only own interviews, gets 403 on applicants and admin routes, deactivated token 401, self-demote 409.
Browser: board drag-and-drop saved, drop on Rejected opens Refuse, drawer shows source and "also applied to",
Users page, interviewer view.

## 4. Known limits (accepted for the demo)

- Token is stored in `localStorage`. Move to an httpOnly cookie before going public.
- Login rate limit is per process memory (resets on restart). No rate limit on apply.
- CV / attachment files are stored in the database (`stored_file`, 5 MB max each). Move to object storage if files grow.
- Times are stored in UTC; display uses the browser's timezone, emails use `TIMEZONE` from `.env`.

## 4b. Deploy checklist (do not skip)

Local dev (each teammate runs the backend on their own machine against the shared Supabase DB) works with the
`localhost` values. Before putting the app on a real domain, e.g. `https://hr.example.com`:

| What | Where | Change |
|---|---|---|
| Google redirect URI | Google Cloud → Google Auth Platform → Clients → `hr-backend` → Authorized redirect URIs | **Add** `https://hr.example.com/api/google/callback` (keep the localhost one for dev; one client holds both) |
| `GOOGLE_REDIRECT_URI` | server env | `https://hr.example.com/api/google/callback` (must match the URI above character for character) |
| `FRONTEND_URL` | server env | `https://hr.example.com`: used in candidate emails (booking link, Accept / Decline). Left on localhost, candidates get links that do not open |
| Authorized domains | Google Cloud → Branding | add `example.com` if Google asks |
| Google app mode | Google Cloud → Audience | Testing = only listed test users, consent expires after 7 days. Publish (Google review) before real interviewers outside the list use it |
| HTTPS | hosting | required for every non-localhost redirect URI |
| Same Google client everywhere | every `.env` | all machines / servers sharing one DB must use the same `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, refresh tokens only work with the client that issued them |
| `SECRET_KEY` | server env | long random value, never the dev one; signs login tokens and the Google OAuth state |
| SMTP | server env | real SMTP (Gmail app password or a mail service) instead of Mailpit; `MAIL_FROM`, `COMPANY_NAME` set |
| CORS / API URL | backend `main.py` CORS list, frontend build | allow the real frontend origin; serve `/api` on the same domain or point the frontend at it |
| Login token storage | frontend | move from `localStorage` to an httpOnly cookie (section 4) |
| Google refresh tokens | `google_credential` table | stored in plain text: encrypt before a shared or public deployment |

## 5. Assumptions to confirm

Made while building without a product spec. Change them in one place if the spec says otherwise.

| Assumption | Where |
|---|---|
| Salaries (job range, expected, proposed) are gross monthly VND, whole numbers | `modules/jobs/models.py`, `modules/applicants/models.py` |
| A job's close date is inclusive, in the company timezone (`TIMEZONE`) | `modules/jobs/service.py` |
| The recruiter job list shows every job, including closed and out-of-window ones | `modules/jobs/service.py` |
| Restore works on any refused or archived applicant and sends it back to `new` | `modules/applicants/service.py` |
| Refusing an archived applicant is allowed; archive / restore send no email | `modules/applicants/service.py` |
| "Send refusal email" is ticked by default in the Refuse dialog | `components/RefuseDialog.tsx` |
| Congratulations email only on the move into `hired`, not when already hired | `modules/applicants/service.py` |
| Interview feedback can be re-submitted (overwrites); recording it sends no email | `modules/interviews/service.py` |
| A no-show may still keep a score if one is sent (the UI only sends it for done) | `modules/interviews/service.py` |
| Wrong interview status (not scheduled / cancelled) returns 409; bad input returns 422 | `modules/interviews/service.py` |
| Passwords at least 8 characters | `modules/users/schemas.py` |
| Interviewers see their past interviews too (to give feedback); matched to interviews by email, any case | `modules/interviews/service.py` |
| Any active user (any role) can be a job interviewer | `modules/jobs/service.py` |
| Applicant source list: careers site, LinkedIn, referral, job board, other | `modules/applicants/models.py` |
| Stuck after N days: new 3, screening 5, interview 7, offer 5 | `modules/applicants/models.py` |

## 6. How to run

See the root `README.md`. In short: `docker compose up -d`, then `uvicorn app.main:app --reload --port 8000`
in `backend/`, then `npm run dev` in `frontend/`. Invitations show up at http://localhost:8025.
