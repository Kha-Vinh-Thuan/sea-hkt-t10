"""Interview invitation email with an .ics attachment: Gmail/Outlook add it to the calendar, no OAuth needed.

Dev: docker compose runs Mailpit (SMTP on 1025, inbox UI on http://localhost:8025), so nothing reaches real inboxes.
"""

import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage


class MailError(Exception):
    pass


def _ics_time(dt: datetime) -> str:
    # SQLite hands back naive datetimes; everything is stored as UTC, so naive means UTC.
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(uid: str, summary: str, start: datetime, end: datetime, location: str,
              organizer: str, attendees: list[str]) -> str:
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//HR System//EN", "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_ics_time(datetime.now(timezone.utc))}",
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
    return os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER") or "hr@localhost"


def mail_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST"))


def send_invite(to: list[str], subject: str, body: str, ics: str) -> None:
    message = EmailMessage()
    message["From"] = mail_from()
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(ics.encode(), maintype="text", subtype="calendar", filename="interview.ics",
                           params={"method": "REQUEST"})
    try:
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=20) as smtp:
            if os.environ.get("SMTP_STARTTLS", "true").lower() == "true":
                smtp.starttls()
            if os.environ.get("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"Could not send email: {e}") from e
