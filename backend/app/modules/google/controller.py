"""Google Calendar connect routes. connect/disconnect need a login; the callback is Google's browser redirect."""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.config import settings
from app.config.database import get_session
from app.integrations.google_calendar import GoogleError
from app.modules.auth.dependencies import require_user
from app.modules.google import service
from app.modules.users.models import User

router = APIRouter(prefix="/api/google", tags=["google"])

@router.get("/connect")
def connect(user: User = Depends(require_user)):
    return {"url": service.connect_url(user)}

@router.get("/callback")
def callback(state: str = "", code: str = "", error: str = "", session: Session = Depends(get_session)):
    # A bad state raises Invalid (422) before anything else: never store a token we did not ask for.
    service.read_state(state)
    result = "denied" if error or not code else "connected"
    if result == "connected":
        try:
            service.finish_connect(session, state, code)
        except GoogleError:
            result = "error"
    return RedirectResponse(f"{settings.frontend_url()}/?google={result}", status_code=303)

@router.delete("/connection", status_code=204)
def disconnect(user: User = Depends(require_user), session: Session = Depends(get_session)):
    service.disconnect(session, user)
