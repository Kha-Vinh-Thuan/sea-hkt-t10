"""Code default for every keyed template: seeded into an empty table, and used when the keyed row was deleted."""

from typing import NamedTuple

from app.modules.applicants.models import Stage

class DefaultTemplate(NamedTuple):
    name: str
    subject: str
    body: str
    stage: Stage | None = None

DEFAULTS: dict[str, DefaultTemplate] = {
    "interest": DefaultTemplate(
        "Recruitment: Interest", "We received your application for {job}",
        "Hello {name},\n\nThank you for applying for {job}. We received your application and will review it soon.\n"
        "We will contact you by email about the next steps.\n"),
    "refusal": DefaultTemplate(
        "Recruitment: Refuse", "Your application for {job}",
        "Hello {name},\n\nThank you for your interest in {job} and for the time you spent applying.\n"
        "After careful consideration we have decided not to move forward with your application.\n"
        "We wish you all the best in your job search.\n"),
    # Odoo's "not interested" template: the applicant withdrew (job fit / salary), so no "we decided" wording.
    "not_interested": DefaultTemplate(
        "Recruitment: Not interested anymore", "Sorry to see you go: {job}",
        "Hello {name},\n\nThank you for letting us know that you are no longer interested in {job}.\n"
        "We are sorry to see you go, and we have closed your application.\n"
        "You are welcome to apply again for this or any other position in the future.\n"),
    "congratulations": DefaultTemplate(
        "Recruitment: Congratulations", "Congratulations! Welcome aboard as {job}",
        "Hello {name},\n\nCongratulations! We are happy to tell you that you have been selected for {job}.\n"
        "We will contact you shortly with the details about your first day.\n"),
    # ASSUMPTION: screening / offer wording until the product spec provides it.
    "screening": DefaultTemplate(
        "Recruitment: Screening", "We are reviewing your application for {job}",
        "Hello {name},\n\nGood news: your application for {job} at {company} has moved to screening.\n"
        "We are reviewing it now and will contact you soon to arrange a short call.\n",
        Stage.screening),
    "offer": DefaultTemplate(
        "Recruitment: Offer letter", "Job offer: {job} at {company}",
        "Hello {name},\n\nWe are pleased to offer you the position of {job} at {company}.\n"
        "Offer details (salary, start date, benefits):\n\n[fill in before sending]\n\n"
        "Please reply to this email to accept or to ask any questions. We look forward to working with you.\n",
        Stage.offer),
}
