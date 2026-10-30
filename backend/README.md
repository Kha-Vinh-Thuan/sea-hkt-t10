# Backend structure

Three layers. A request only flows downwards; a lower layer never imports an upper one.

```
app/
  main.py            app setup, routers, ServiceError -> HTTP status
  api/               1. HTTP layer: parse request, call a service, return result. No business rules.
    public.py          careers site (no login)
    auth.py            login
    recruiter.py       recruiter routes (login required)
  services/          2. Business layer: rules, validation, logging. No FastAPI imports.
    jobs.py
    applicants.py
    interviews.py
    errors.py          NotFound / Conflict / Invalid
  models.py          3. Data layer: database tables (SQLModel)
  core/
    db.py              engine + session
    security.py        token signing, recruiter credentials
  integrations/      outside systems, called by services
    cv.py              save CV file, extract text
    mail.py            SMTP + .ics invitation
  schemas.py         request/response shapes (what clients send and see)
  seed.py            demo jobs
tests/
  test_api.py        through HTTP
  test_services.py   services directly, no HTTP
```

| Want to change... | Edit |
|---|---|
| A URL, status code, request field | `api/` + `schemas.py` |
| A rule (who can apply, clash check, stage moves) | `services/` |
| A table column | `models.py` (then recreate the table: no migrations yet) |
| Mail provider, CV formats | `integrations/` |

Why services never import FastAPI: the same rules will be called by the AI agents later, not only by HTTP.
No repository layer: SQLModel's session already is the data-access layer; wrapping it would add a file per
table with nothing in it.
