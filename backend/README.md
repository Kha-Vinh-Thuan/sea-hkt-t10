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
    database.py            engine, session, create_tables
  modules/
    jobs/                  job positions
      controller.py          routes (public careers listing + recruiter CRUD)
      service.py             rules: closed jobs hidden from the public
      repository.py          queries on the job table
      models.py              Job table
      schemas.py             request/response shapes
    applicants/            apply form, board, stage moves, activity log
      controller.py  service.py  repository.py  models.py  schemas.py
    interviews/            booking + invitation email
      controller.py  service.py  repository.py  models.py  schemas.py
    auth/                  recruiter login
      controller.py          POST /api/auth/login
      service.py             token signing, credential check
      dependencies.py        require_recruiter, used by other modules' routes
      schemas.py
  integrations/            outside systems, called by services
    cv.py                    save CV file, extract text (PDF/DOCX/TXT)
    mail.py                  SMTP + .ics invitation
  utils/                   small shared helpers
    errors.py                NotFound / Conflict / Invalid (services raise, main.py maps)
    time.py                  UTC helpers
  seed.py                  demo jobs
tests/
  test_api.py              through HTTP
  test_services.py         services directly, no HTTP
```

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
| A table column | `modules/<x>/models.py` (then recreate the table: no migrations yet) |
| Mail provider, CV formats | `integrations/` |
| An env variable | `config/settings.py` + `.env.example` |

New feature = new folder under `modules/` with the same files, then add its router in `main.py`
and its models import in `config/database.py`.
