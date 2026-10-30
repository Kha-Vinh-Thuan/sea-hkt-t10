"""Interviewer busy / free times: working hours minus busy times (Google free/busy when connected, plus our own
interviews).

Our own interviews always count, even with Google: booking rejects a clash with them, so offering such a slot
would only fail later. Display reads go through a short cache; booking re-asks Google live (`check_google_free`).
"""

import time as clock
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.config import settings
from app.integrations import google_calendar
from app.integrations.google_calendar import GoogleError
from app.modules.google import service as google_service
from app.modules.interviews import repository
from app.modules.users import service as user_service
from app.utils.time import as_utc, utcnow

# ASSUMPTION: Mon-Fri 09:00-17:00 local time until the product spec gives per-user working hours.
WORK_DAYS = {0, 1, 2, 3, 4}
WORK_START, WORK_END = time(9), time(17)
SLOT_STEP_MINUTES = 30   # candidate start times every half hour

GOOGLE_CACHE_SECONDS = 90  # calendar views reopen often; a booking always re-asks Google live

Interval = tuple[datetime, datetime]

# (refresh_token, start, end) -> (fetched_at, busy). ponytail: per-process dict, unbounded; fine for a small team.
_google_cache: dict[tuple[str, datetime, datetime], tuple[float, list[Interval]]] = {}

def _google_busy(refresh_token: str, start: datetime, end: datetime, cached: bool) -> list[Interval]:
    key = (refresh_token, start, end)
    hit = _google_cache.get(key)
    if cached and hit and clock.monotonic() - hit[0] < GOOGLE_CACHE_SECONDS:
        return hit[1]
    busy = [(as_utc(s), as_utc(e)) for s, e in google_calendar.busy(refresh_token, start, end)]
    _google_cache[key] = (clock.monotonic(), busy)
    return busy

def own_busy(session: Session, email: str, start: datetime, end: datetime) -> list[Interval]:
    return [(as_utc(i.start), as_utc(i.end)) for i, _a, _j in repository.list_upcoming(
        session, start, interviewer_email=email) if as_utc(i.start) < end]

def google_busy(session: Session, user_id: int, start: datetime, end: datetime,
                cached: bool = True) -> list[Interval] | None:
    """Google busy times, [] if the user has not connected Google, None if Google could not be reached."""
    return _google_busy_for(google_service.refresh_token_for(session, user_id), start, end, cached)

def _google_busy_for(refresh_token: str | None, start: datetime, end: datetime, cached: bool) -> list[Interval] | None:
    if not refresh_token:
        return []
    try:
        return _google_busy(refresh_token, start, end, cached)
    except GoogleError:
        return None

def busy_times(session: Session, user_id: int, start: datetime, end: datetime) -> list[Interval]:
    user = user_service.get(session, user_id)
    # ponytail: Google down falls back to our own interviews; the calendar view says so via `google_ok`.
    return own_busy(session, user.email, start, end) + (google_busy(session, user_id, start, end) or [])

def check_google_free(session: Session, email: str, start: datetime, end: datetime) -> str | None:
    """Live Google check at booking time: "busy" if Google shows the interviewer busy, a warning text if Google
    could not be asked (the booking goes ahead, decided 2026-10-30), else None."""
    # Typed-in outsiders have no Google link: [] here, our own clash check still applies.
    busy = _google_busy_for(google_service.refresh_token_for_email(session, email), start, end, cached=False)
    if busy is None:
        return "Could not check Google Calendar, booked without it"
    return "busy" if any(b_start < end and b_end > start for b_start, b_end in busy) else None

def free_slots(session: Session, user_id: int, start: datetime, end: datetime, minutes: int) -> list[Interval]:
    """Every [s, s + minutes) inside working hours between start and end, in the future, overlapping nothing busy."""
    start, end = max(as_utc(start), utcnow()), as_utc(end)
    if start >= end:
        return []
    busy = busy_times(session, user_id, start, end)
    zone = ZoneInfo(settings.timezone_name())
    length, step = timedelta(minutes=minutes), timedelta(minutes=SLOT_STEP_MINUTES)
    slots: list[Interval] = []
    day = start.astimezone(zone).date()
    while day <= end.astimezone(zone).date():
        if day.weekday() in WORK_DAYS:
            slot = datetime.combine(day, WORK_START, zone)
            day_end = datetime.combine(day, WORK_END, zone)
            while slot + length <= day_end:
                slot_start, slot_end = as_utc(slot), as_utc(slot + length)
                if (slot_start >= start and slot_end <= end
                        and not any(b_start < slot_end and b_end > slot_start for b_start, b_end in busy)):
                    slots.append((slot_start, slot_end))
                slot += step
        day += timedelta(days=1)
    return slots

def still_free(session: Session, user_id: int, slots: list[Interval]) -> list[Interval]:
    """The given slots (any time of day, the recruiter chose them) that are in the future and overlap nothing busy."""
    now = utcnow()
    slots = [(as_utc(s), as_utc(e)) for s, e in slots if as_utc(s) > now]
    if not slots:
        return []
    busy = busy_times(session, user_id, min(s for s, _ in slots), max(e for _, e in slots))
    return [(s, e) for s, e in slots if not any(b_start < e and b_end > s for b_start, b_end in busy)]

def week_busy(session: Session, user_ids: list[int], start: datetime, end: datetime) -> list[dict]:
    """Busy blocks per interviewer for the calendar grid: only times, never Google event titles."""
    rows = []
    for user_id in user_ids:
        user = user_service.get(session, user_id)
        google = google_busy(session, user_id, start, end)
        rows.append({
            "user_id": user.id, "name": user.name or user.email, "email": user.email,
            "google_connected": google_service.is_connected(session, user_id), "google_ok": google is not None,
            "busy": [{"start": s, "end": e, "source": "interview"} for s, e in own_busy(session, user.email, start, end)]
                    + [{"start": s, "end": e, "source": "google"} for s, e in (google or [])],
        })
    return rows
