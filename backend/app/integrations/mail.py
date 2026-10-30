"""Interview invitation email with an .ics attachment: Gmail/Outlook add it to the calendar, no OAuth needed.

Dev: docker compose runs Mailpit (SMTP on 1025, inbox UI on http://localhost:8025), so nothing reaches real inboxes.
"""

import smtplib
from datetime import datetime
from email.message import EmailMessage

from app.config import settings
from app.utils.time import as_utc, utcnow


class MailError(Exception):
    pass


def _ics_time(dt: datetime) -> str:
    return as_utc(dt).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(uid: str, summary: str, start: datetime, end: datetime, location: str,
              organizer: str, attendees: list[str], method: str = "REQUEST", sequence: int = 0) -> str:
    """method REQUEST creates/updates, CANCEL removes. Calendars match on UID and keep the highest SEQUENCE."""
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//HR System//EN", f"METHOD:{method}",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"SEQUENCE:{sequence}",
        *(["STATUS:CANCELLED"] if method == "CANCEL" else []),
        f"DTSTAMP:{_ics_time(utcnow())}",
        f"DTSTART:{_ics_time(start)}",
        f"DTEND:{_ics_time(end)}",
        f"SUMMARY:{_escape(summary)}",
        f"LOCATION:{_escape(location)}",
        f"ORGANIZER:mailto:{organizer}",
        *[f"ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE:mailto:{email}" for email in attendees],
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def mail_from() -> str:
    return settings.smtp()["sender"]


def mail_configured() -> bool:
    return bool(settings.smtp()["host"])


def send_mail(to: list[str], subject: str, body: str, ics: str | None = None, method: str = "REQUEST") -> None:
    """Plain text email; with `ics` it carries a calendar invite (method must match METHOD inside the .ics)."""
    config = settings.smtp()
    message = EmailMessage()
    message["From"] = config["sender"]
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)
    if ics:
        message.add_attachment(ics.encode(), maintype="text", subtype="calendar", filename="interview.ics",
                               params={"method": method})
    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=20) as client:
            if config["starttls"]:
                client.starttls()
            if config["user"]:
                client.login(config["user"], config["password"])
            client.send_message(message)
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"Could not send email: {e}") from e

def send_invite(to: list[str], subject: str, body: str, ics: str, method: str = "REQUEST") -> None:
    send_mail(to, subject, body, ics, method)
