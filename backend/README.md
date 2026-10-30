# Backend structure

Split by feature. Each feature module has the same four layers, and a request only flows downwards:

```
controller  ->  service  ->  repository  ->  models
  (HTTP)        (rules)       (queries)      (tables)
```

```
app/
  main.py                  wires routers, maps service errors to HTTP status
  config/
    settings.py            every env variable, read in one place
    database.py            engine, session, migrate (Alembic upgrade on startup)
  modules/
    jobs/                  job positions
      controller.py          routes (public careers listing + recruiter CRUD)
      service.py             rules: closed jobs hidden from the public
      repository.py          queries on the job table
      models.py              Job table
      schemas.py             request/response shapes
    applicants/            apply form, board, stage moves, refuse / archive, recruiter fields, activity log
      controller.py  service.py  repository.py  models.py  schemas.py
      emails.py              candidate emails: automatic ones by template key + recruiter composer (send, log)
    mail_templates/        editable email templates {name} {job} {company} (Odoo mail.template), seeded when empty
      controller.py  service.py  repository.py  models.py  schemas.py
      defaults.py            built-in texts: seed + fallback when a keyed template was deleted
    interviews/            book / reschedule / cancel (.ics with stable UID), feedback scorecard, candidate Accept / Decline
      controller.py  service.py  repository.py  models.py  schemas.py
      availability.py        free slots: Mon-Fri 09-17 minus busy (Google free/busy + our interviews)
      calendar_sync.py       mirror an interview on the interviewer's Google Calendar (Meet link); failure only logged
    bookings/              propose times by email, candidate books one on /book/{token} (no login)
      controller.py  service.py  repository.py  models.py  schemas.py
    google/                per-user Google Calendar connect (OAuth code -> refresh token, signed state)
      controller.py  service.py  repository.py  models.py
    reports/               GET /api/reports/summary: per job counts by stage / source / refuse reason, hired vs openings, avg days to hire
      controller.py  service.py   (no tables, reads applicants and jobs)
    talent_pools/          named groups of applicants to contact later (Odoo hr.talent.pool)
      controller.py  service.py  repository.py  models.py  schemas.py
    files/                 stored_file table: CV / attachment bytes in the DB (key kept in cv_path / stored_path)
      models.py  repository.py
    auth/                  login + token
      controller.py          POST /api/auth/login, GET /api/auth/me
      service.py             token signing (user id + role), reloads the user on every request
      dependencies.py        require_user / require_recruiter (admin or recruiter) / require_admin
      schemas.py
    users/                 accounts and roles (admin | recruiter | interviewer)
      controller.py  service.py  repository.py  models.py  schemas.py
      passwords.py           stdlib scrypt hash + constant-time verify
  integrations/            outside systems, called by services
    cv.py                    validate + save CV / attachment as a stored_file row, extract text (PDF/DOCX/TXT)
    mail.py                  SMTP send_mail (optional .ics attachment), build_ics
    google_calendar.py       Google OAuth + Calendar REST over httpx (freebusy, events with Meet), no SDK
  utils/                   small shared helpers
    errors.py                NotFound / Conflict / Invalid (services raise, main.py maps)
    time.py                  UTC helpers
  seed.py                  demo jobs
  move_uploads_to_db.py    one-off: old uploads/ files -> stored_file
migrations/                Alembic revisions (versions/0001_initial_schema.py, ...)
tests/
  conftest.py              stubs candidate emails for every test
  test_api.py              through HTTP: jobs, apply, board, booking
  test_applicant_actions.py  edit fields, refuse, archive / restore, candidate emails
  test_interviews.py       reschedule, cancel, feedback
  test_services.py         services directly, no HTTP
  test_reports_pools.py    hire date, reports summary, stage requirements, talent pools
  test_job_extras.py       job recruiter / manager, tags
  test_applicant_more.py   copy to job, attachments, owner, "not interested" mail
  test_mail_templates.py   render, seeded defaults, admin CRUD, compose / send email
  test_migrations.py       migrations == models (fails if you forgot a revision)
  test_file_storage.py     CV / attachment bytes in the DB, move script, hosted DATABASE_URL
```

## Shared hosted Postgres

The team shares one hosted Postgres (Neon / Supabase); each dev runs the backend locally against it. CV and
attachment bytes are stored in the `stored_file` table, so every machine can open every file.

1. Create a database in the provider console (e.g. `hr`) and copy its connection URL.
2. In `backend/.env` set `DATABASE_URL=postgresql://user:password@host/hr?sslmode=require` (keep `sslmode=require`;
   `postgres://` / `postgresql://` are switched to the psycopg driver automatically).
3. Start the backend: migrations run on startup.
4. Optional, once per DB: `python -m app.seed` for demo jobs.
5. Once, from the machine that holds the old `uploads/` folder: `python -m app.move_uploads_to_db`. It copies every
   referenced file into `stored_file` under its old name (so applicant rows need no change), prints
   `moved / already_in_db / missing_on_disk`, is safe to rerun and leaves the files on disk.

`SECRET_KEY` can differ per machine; it only needs to match if a login token from one machine must work on another.

## Users and roles

On the first login, if the `app_user` table is empty, an admin is created from `RECRUITER_EMAIL` / `RECRUITER_PASSWORD`
(so an existing `.env` keeps working). After that the env pair is ignored; the admin manages users in the Users tab.

| Role | Can |
|---|---|
| admin | everything, plus `/api/admin/users` (create, edit name/role/active, reset password); cannot demote or deactivate self or the last admin |
| recruiter | jobs, applicants, interviews, `GET /api/users?role=` (pickers) |
| interviewer | `GET /api/interviews` (own, matched by email) and feedback on own interviews; nothing else (403) |

## Rules of thumb

| Layer | Does | Never |
|---|---|---|
| controller | parse request, call one service function, return | business rules, queries |
| service | rules, validation, commits, calls other modules' services/repositories | import FastAPI |
| repository | `select` / `add` on its own tables | decide anything, commit (except simple `save`) |
| models | table definitions | logic |

A module may use another module's `service` or `repository` (interviews reads applicants and jobs).
Services never import FastAPI, so the AI agents (jobhunter-platform) can call the same rules later.

## Where to change things

| Want to change... | Edit |
|---|---|
| A URL, status code, request field | `modules/<x>/controller.py` + `schemas.py` |
| A rule (who can apply, clash check, stage moves) | `modules/<x>/service.py` |
| A query | `modules/<x>/repository.py` |
| A table column | `modules/<x>/models.py`, then `alembic revision --autogenerate -m "..."`, review the file, `alembic upgrade head` |
| Mail provider, CV formats | `integrations/` |
| An env variable | `config/settings.py` + `.env.example` |

New feature = new folder under `modules/` with the same files, then add its router in `main.py`
its models import in `config/database.py` (`import_models`), and a migration.
