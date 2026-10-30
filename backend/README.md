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
      emails.py              candidate email texts (received, refusal, congratulations)
    interviews/            book / reschedule / cancel (.ics with stable UID), feedback scorecard
      controller.py  service.py  repository.py  models.py  schemas.py
    reports/               GET /api/reports/summary: per job counts by stage / source / refuse reason, hired vs openings, avg days to hire
      controller.py  service.py   (no tables, reads applicants and jobs)
    talent_pools/          named groups of applicants to contact later (Odoo hr.talent.pool)
      controller.py  service.py  repository.py  models.py  schemas.py
    auth/                  login + token
      controller.py          POST /api/auth/login, GET /api/auth/me
      service.py             token signing (user id + role), reloads the user on every request
      dependencies.py        require_user / require_recruiter (admin or recruiter) / require_admin
      schemas.py
    users/                 accounts and roles (admin | recruiter | interviewer)
      controller.py  service.py  repository.py  models.py  schemas.py
      passwords.py           stdlib scrypt hash + constant-time verify
  integrations/            outside systems, called by services
    cv.py                    save CV file, extract text (PDF/DOCX/TXT)
    mail.py                  SMTP send_mail (optional .ics attachment), build_ics
  utils/                   small shared helpers
    errors.py                NotFound / Conflict / Invalid (services raise, main.py maps)
    time.py                  UTC helpers
  seed.py                  demo jobs
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
  test_migrations.py       migrations == models (fails if you forgot a revision)
```

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
