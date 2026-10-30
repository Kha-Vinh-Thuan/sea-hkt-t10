"""Mail template routes: list for recruiters (composer picker), CRUD for admins."""

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.config.database import get_session
from app.modules.auth.dependencies import require_admin, require_recruiter
from app.modules.mail_templates import service
from app.modules.mail_templates.schemas import TemplateIn

router = APIRouter(prefix="/api/mail-templates", tags=["mail templates"], dependencies=[Depends(require_recruiter)])
admin_router = APIRouter(prefix="/api/admin/mail-templates", tags=["mail templates"],
                         dependencies=[Depends(require_admin)])

@router.get("")
def list_templates(session: Session = Depends(get_session)):
    return service.list_all(session)

@admin_router.get("")
def admin_list_templates(session: Session = Depends(get_session)):
    return service.list_all(session)

@admin_router.post("", status_code=201)
def create_template(data: TemplateIn, session: Session = Depends(get_session)):
    return service.create(session, data)

@admin_router.put("/{template_id}")
def update_template(template_id: int, data: TemplateIn, session: Session = Depends(get_session)):
    return service.update(session, template_id, data)

@admin_router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, session: Session = Depends(get_session)):
    service.delete(session, template_id)
    return Response(status_code=204)
