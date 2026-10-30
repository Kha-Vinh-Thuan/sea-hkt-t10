"""FastAPI app: wires every module's routers and maps business errors to HTTP.

Each module under modules/ has controller -> service -> repository -> models. See backend/README.md.
Run: uvicorn app.main:app --reload  (from backend/)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.database import migrate
from app.modules.applicants import controller as applicants
from app.modules.auth import controller as auth
from app.modules.interviews import controller as interviews
from app.modules.jobs import controller as jobs
from app.modules.users import controller as users
from app.utils.errors import ServiceError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    migrate()
    yield


app = FastAPI(title="HR System API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

for router in (jobs.public_router, applicants.public_router, auth.router,
               jobs.router, applicants.router, interviews.router, users.router, users.admin_router):
    app.include_router(router)


@app.exception_handler(ServiceError)
def service_error(_request: Request, error: ServiceError):
    return JSONResponse(status_code=error.status_code, content={"detail": str(error)})


@app.get("/api/health")
def health():
    return {"ok": True}
