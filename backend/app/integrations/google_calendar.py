"""Google Calendar over plain OAuth2 + REST with httpx (no Google SDK): consent URL, code exchange,
freebusy, and insert / patch / delete of an event with a Meet link on the user's primary calendar.

Every call takes the user's refresh token and gets a fresh access token first.
ponytail: one token refresh per call; cache access tokens (they live 1 h) if Google quota or latency matters.
Never put tokens in exceptions or logs: GoogleError messages carry only the HTTP status and Google's error code.
"""

import base64
import json
from datetime import datetime
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.utils.time import as_utc

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API = "https://www.googleapis.com/calendar/v3"
# openid + email only to learn which Google account was connected (shown to the user).
SCOPES = ("openid email https://www.googleapis.com/auth/calendar.events "
          "https://www.googleapis.com/auth/calendar.freebusy")
TIMEOUT = 15


class GoogleError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def configured() -> bool:
    config = settings.google()
    return bool(config["client_id"] and config["client_secret"])


def consent_url(state: str) -> str:
    config = settings.google()
    return AUTH_URL + "?" + urlencode({
        "client_id": config["client_id"], "redirect_uri": config["redirect_uri"], "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state,
    })


def _call(method: str, url: str, **kwargs) -> dict:
    try:
        response = httpx.request(method, url, timeout=TIMEOUT, **kwargs)
    except httpx.HTTPError as e:
        raise GoogleError(f"Google unreachable: {type(e).__name__}") from None
    if response.status_code >= 400:
        try:
            error = response.json().get("error")
            error = error.get("status") or error.get("message") if isinstance(error, dict) else error
        except ValueError:
            error = ""
        raise GoogleError(f"Google returned {response.status_code} {error or ''}".strip(), response.status_code)
    return response.json() if response.content else {}


def exchange_code(code: str) -> tuple[str, str]:
    """(refresh_token, google account email) for the code Google sent to the callback."""
    config = settings.google()
    data = _call("POST", TOKEN_URL, data={
        "code": code, "client_id": config["client_id"], "client_secret": config["client_secret"],
        "redirect_uri": config["redirect_uri"], "grant_type": "authorization_code"})
    if not data.get("refresh_token"):
        raise GoogleError("Google sent no refresh token")
    return data["refresh_token"], _email_from_id_token(data.get("id_token", ""))


def _email_from_id_token(id_token: str) -> str:
    # Straight from Google's token endpoint over TLS, so reading the payload without verifying the signature is fine.
    try:
        payload = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("email", "")
    except (IndexError, ValueError):
        return ""


def revoke(refresh_token: str) -> None:
    _call("POST", REVOKE_URL, data={"token": refresh_token})


def _access_token(refresh_token: str) -> str:
    config = settings.google()
    return _call("POST", TOKEN_URL, data={
        "refresh_token": refresh_token, "client_id": config["client_id"],
        "client_secret": config["client_secret"], "grant_type": "refresh_token"})["access_token"]


def _auth(refresh_token: str) -> dict:
    return {"Authorization": f"Bearer {_access_token(refresh_token)}"}


def busy(refresh_token: str, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Busy intervals on the user's primary calendar between start and end."""
    data = _call("POST", f"{API}/freeBusy", headers=_auth(refresh_token), json={
        "timeMin": as_utc(start).isoformat(), "timeMax": as_utc(end).isoformat(), "items": [{"id": "primary"}]})
    return [(datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"]))
            for b in data.get("calendars", {}).get("primary", {}).get("busy", [])]


def save_event(refresh_token: str, event_id: str, body: dict) -> tuple[str, str]:
    """Create (event_id "") or update the event; returns (event_id, Meet link).

    sendUpdates=none: the candidate already gets our .ics email, Google must not send a second invitation.
    """
    params = {"conferenceDataVersion": 1, "sendUpdates": "none"}
    if event_id:
        data = _call("PATCH", f"{API}/calendars/primary/events/{event_id}", params=params,
                     headers=_auth(refresh_token), json=body)
    else:
        data = _call("POST", f"{API}/calendars/primary/events", params=params, headers=_auth(refresh_token), json=body)
    return data["id"], data.get("hangoutLink", "")


def delete_event(refresh_token: str, event_id: str) -> None:
    try:
        _call("DELETE", f"{API}/calendars/primary/events/{event_id}", params={"sendUpdates": "none"},
              headers=_auth(refresh_token))
    except GoogleError as e:
        if e.status not in (404, 410):  # already deleted on the Google side: nothing to do
            raise


def event_body(summary: str, description: str, start: datetime, end: datetime, location: str,
               attendees: list[str], request_id: str) -> dict:
    """Event fields; createRequest asks Google for a Meet link (drop it on patch to keep the existing link)."""
    return {
        "summary": summary, "description": description, "location": location,
        "start": {"dateTime": as_utc(start).isoformat()}, "end": {"dateTime": as_utc(end).isoformat()},
        "attendees": [{"email": email} for email in attendees],
        "conferenceData": {"createRequest": {"requestId": request_id,
                                             "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
    }
