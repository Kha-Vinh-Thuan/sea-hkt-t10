"""FastAPI app: wires routers and maps business errors to HTTP.

Layers: api/ (HTTP only) -> services/ (business rules) -> models + core/db (data);
integrations/ wraps outside systems (mail, CV parsing). See backend/README.md.
Run: uvicorn app.main:app --reload  (from backend/)
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # before importing core.db, which reads DATABASE_URL

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app.api import auth, public, recruiter  # noqa: E402
from app.core.db import create_tables  # noqa: E402
from app.services.errors import ServiceError  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="HR System API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(recruiter.router)


@app.exception_handler(ServiceError)
def service_error(_request: Request, error: ServiceError):
    return JSONResponse(status_code=error.status_code, content={"detail": str(error)})


@app.get("/api/health")
def health():
    return {"ok": True}
