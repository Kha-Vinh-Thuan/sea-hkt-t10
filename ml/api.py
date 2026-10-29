"""T10 Interview AI: standalone service a company's internal system plugs into.

Integrator (server-to-server, header  Authorization: Bearer <tenant api key>):
  POST /v1/sessions                       context -> {id, join_url, embed_token, expires_in}
  GET  /v1/sessions/{id}                  status, transcript, report
  GET  /v1/sessions?limit=50
  POST /v1/sessions/{id}/decision         {decision: hire|reject, note} -> labels for self-learning (if consented)
  PATCH /v1/tenant                        {webhook_url, share_training}
  GET  /v1/trust-report                   latest fairness audit of the scorer
Webhooks (POST to tenant.webhook_url, header X-T10-Signature: sha256=HMAC(secret, body)):
  session.started, session.completed, report.ready, integrity.flag
Candidate (token in the URL, no API key):
  GET  /join/{token}                      full-page interview (integration mode 1: send the link)
  GET  /embed.js                          <t10-interview token="..."> web component (mode 2: embed in your UI)
  POST /c/{token}/consent|chat|proctor
Admin (header X-Admin-Key = T10_ADMIN_KEY): POST /admin/tenants {name, webhook_url}
"""
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import threading
import urllib.request
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

import engine
import interview
import store
from claude import ClaudeError
from voice import tts

_logger = logging.getLogger(__name__)
app = FastAPI(title='T10 Interview AI', version='1.0')
# Candidate endpoints are called from the tenant's own pages when embedded; the token is the only credential.
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
PUBLIC_URL = os.environ.get('T10_PUBLIC_URL', 'http://localhost:8000').rstrip('/')
CONSENT_VERSION = '2026-10-29'
DECISION_LABEL = {'hire': 80, 'reject': 30}  # ponytail: one label per interview; add per-answer recruiter ratings later
_report_lock = threading.Lock()


# ------------------------------------------------------------------ auth

def tenant(authorization: str = Header('')):
    t = authorization.startswith('Bearer ') and store.tenant_by_key(authorization[7:])
    if not t:
        raise HTTPException(401, 'invalid API key')
    return t


def admin(x_admin_key: str = Header('')):
    expected = os.environ.get('T10_ADMIN_KEY')
    if not expected or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(401, 'admin key required')


# ------------------------------------------------------------------ models

class Context(BaseModel):
    """Everything the company's system knows about the role. Only job_title is required."""
    job_title: str = Field(max_length=200)
    description: str = Field('', max_length=20000)
    requirements: str = Field('', max_length=10000)
    seniority: str = Field('', max_length=50)
    industry: str = Field('', pattern=r'^[a-z_]{0,32}$', description='picks the industry adapter, e.g. it, sales')
    company: str = Field('', max_length=200)
    company_context: str = Field('', max_length=10000, description='culture, team, product: anything that helps')
    questions: list[str] = Field([], max_length=20, description='must-ask questions; default plan if empty')
    verify_claims: list[str] = Field([], max_length=10, description='CV claims to check, e.g. from your CV screener')
    rubric: str = Field('', max_length=5000)
    language: str = Field('Vietnamese', max_length=30)
    max_answers: int = Field(8, ge=2, le=20)
    candidate_ref: str = Field('', max_length=200, description='your own id for the candidate; no personal data needed')


class SessionIn(BaseModel):
    context: Context
    expires_in_hours: int = Field(72, ge=1, le=720)


class DecisionIn(BaseModel):
    decision: str = Field(pattern='^(hire|reject)$')
    note: str = Field('', max_length=2000)


class TenantIn(BaseModel):
    name: str = Field(max_length=200)
    webhook_url: str | None = None
    share_training: bool = False


class TenantPatch(BaseModel):
    webhook_url: str | None = None
    share_training: bool | None = None


class ChatIn(BaseModel):
    message: str = Field('', max_length=interview.MAX_ANSWER_CHARS)


class ConsentIn(BaseModel):
    training: bool = False


class ProctorIn(BaseModel):
    events: list[dict] = Field([], max_length=100)
    snapshot: str | None = None


# ------------------------------------------------------------------ webhooks

def sign(secret, body):
    return 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def emit(tenant_id, event, payload):
    t = store.tenant(tenant_id)
    if not t or not t['webhook_url']:
        return
    body = json.dumps({'event': event, 'data': payload}, ensure_ascii=False).encode()
    req = urllib.request.Request(t['webhook_url'], body, {'Content-Type': 'application/json', 'User-Agent': 't10/1.0',
                                                           'X-T10-Event': event,
                                                           'X-T10-Signature': sign(t['webhook_secret'], body)})
    for attempt in range(3):  # ponytail: in-process retries; add a durable outbox when delivery must be guaranteed
        try:
            urllib.request.urlopen(req, timeout=10).close()
            return
        except Exception as e:  # noqa: BLE001
            _logger.warning("webhook %s to %s failed (try %s): %s", event, t['webhook_url'], attempt + 1, e)


# ------------------------------------------------------------------ views

def public(s, full=True):
    out = {k: s[k] for k in ('id', 'status', 'created', 'consent', 'decision')}
    out['candidate_ref'] = s['context'].get('candidate_ref')
    if full:
        out.update(context=s['context'], transcript=s['transcript'], report=s['report'],
                   proctor_events=s['proctor_events'])
    return out


def finish(s):
    """Build one report; a gray-zone report may reopen the same room for one bounded follow-up."""
    with _report_lock:  # one report at a time keeps GPU memory predictable
        try:
            report = interview.build_report(s, engine)
            s['report'] = report
            if report.get('needs_followup') and not s.get('followup_round'):
                s['followup_round'] = True
                s['followup_start'] = len(s['transcript'])
                s['followup_questions'] = report['followup_questions']
                s['status'] = 'in_progress'
                store.save_session(s)
                emit(s['tenant_id'], 'followup.started', public(s, full=False))
                return True
            s['status'] = 'reported'
        except ClaudeError as e:
            s['status'], s['report'] = 'report_failed', {'error': str(e)}
        store.save_session(s)
    emit(s['tenant_id'], 'session.completed', public(s, full=False))
    if s['status'] == 'reported':
        emit(s['tenant_id'], 'report.ready', public(s))
        if s['report']['integrity']['review']:
            emit(s['tenant_id'], 'integrity.flag', {'id': s['id'], 'integrity': s['report']['integrity']})
    return False


# ------------------------------------------------------------------ integrator API

@app.post('/admin/tenants', dependencies=[Depends(admin)])
def create_tenant(body: TenantIn):
    tid, key = store.create_tenant(body.name, body.webhook_url, body.share_training)
    return {'tenant_id': tid, 'api_key': key, 'webhook_secret': store.tenant(tid)['webhook_secret'],
            'note': 'api_key is shown only once'}


@app.patch('/v1/tenant')
def patch_tenant(body: TenantPatch, t=Depends(tenant)):
    store.update_tenant(t['id'], **{k: (int(v) if isinstance(v, bool) else v)
                                    for k, v in body.model_dump().items() if v is not None})
    return {k: v for k, v in store.tenant(t['id']).items() if k != 'webhook_secret'}


@app.post('/v1/sessions', status_code=201)
def create_session(body: SessionIn, t=Depends(tenant)):
    s, token = store.create_session(t['id'], body.context.model_dump(), body.expires_in_hours)
    return {'id': s['id'], 'status': s['status'], 'join_url': f'{PUBLIC_URL}/join/{token}', 'embed_token': token,
            'expires_in_hours': body.expires_in_hours}


@app.get('/v1/sessions')
def list_sessions(limit: int = 50, t=Depends(tenant)):
    return [public(s, full=False) for s in store.list_sessions(t['id'], min(limit, 200))]


@app.get('/v1/sessions/{sid}')
def get_session(sid: str, t=Depends(tenant)):
    s = store.get_session(sid, t['id'])
    if not s:
        raise HTTPException(404, 'not found')
    return public(s)


@app.post('/v1/sessions/{sid}/decision')
def decide(sid: str, body: DecisionIn, t=Depends(tenant)):
    """Recruiter's final call. Becomes a training label only if the candidate consented to training use."""
    s = store.get_session(sid, t['id'])
    if not s:
        raise HTTPException(404, 'not found')
    if s['status'] != 'reported':
        raise HTTPException(409, f"session is {s['status']}")
    s['decision'] = body.model_dump()
    store.save_session(s)
    learned = None
    if (s['consent'] or {}).get('training'):
        rows = [dict(p, job=s['context']['job_title'], score=DECISION_LABEL[body.decision],
                     provenance={'source': 'interview', 'consent_version': s['consent']['version'],
                                 'consent_at': s['consent']['at'], 'label': 'recruiter_decision'})
                for p in interview.qa_pairs(s['transcript'])]
        learned = bool(rows) and engine.add_feedback(t['id'], rows, bool(t['share_training']))
    ai = s['report']['verdict']
    return {'id': sid, 'decision': body.decision, 'ai_verdict': ai,
            'agrees_with_ai': None if ai == 'review' else (ai == 'pass') == (body.decision == 'hire'),
            'used_for_learning': bool((s['consent'] or {}).get('training')),
            'tenant_calibrated': bool(learned)}


@app.get('/v1/trust-report')
def get_trust_report(t=Depends(tenant)):
    return engine.trust_report() or {'release_ok': False, 'note': 'no audit yet'}


@app.get('/health')
def health():
    return engine.health()


# ------------------------------------------------------------------ candidate side

def _candidate(token):
    s = store.session_by_token(token)
    if not s:
        raise HTTPException(404, 'link expired or invalid')
    return s


@app.get('/join/{token}', response_class=HTMLResponse)
def join(token: str):
    s = store.session_by_token(token)
    page = (Path(__file__).parent / 'static' / 'interview.html').read_text(encoding='utf-8')
    return page.replace('__TOKEN__', token if s else '').replace('__API__', '')


@app.get('/embed.js')
def embed_js():
    return FileResponse(Path(__file__).parent / 'static' / 'embed.js', media_type='application/javascript')


@app.get('/c/{token}/info')
def candidate_info(token: str):
    s = _candidate(token)
    return {'job_title': s['context']['job_title'], 'company': s['context']['company'], 'status': s['status'],
            'followup': bool(s.get('followup_round')), 'followup_questions': s.get('followup_questions', [])}


@app.post('/c/{token}/consent')
def consent(token: str, body: ConsentIn):
    s = _candidate(token)
    s['consent'] = {'interview': True, 'training': body.training, 'version': CONSENT_VERSION,
                    'at': __import__('datetime').datetime.utcnow().isoformat(timespec='seconds') + 'Z'}
    store.save_session(s)
    return {'ok': True}


@app.post('/c/{token}/chat')
def chat(token: str, body: ChatIn):
    s = _candidate(token)
    if not s['consent']:
        raise HTTPException(409, 'consent first')
    started = s['status'] == 'created'
    started_at = time.monotonic()
    try:
        res = interview.chat(s, body.message.strip(), engine)
    except ValueError:
        return {'error': 'closed'}
    except ClaudeError:
        return {'error': 'ai'}
    finally:
        _logger.info('chat session=%s elapsed=%.1fs', s['id'], time.monotonic() - started_at)
    if started:
        emit(s['tenant_id'], 'session.started', public(s, full=False))
    if res['done']:
        reopened = finish(s)
        # The room remains open only when the report explicitly requested follow-up questions.
        res['done'] = not reopened
        if reopened:
            # Ask the first follow-up question now; the candidate hears a real question, not the closing sentence.
            res = interview.chat(s, '', engine)
            store.save_session(s)
            res['followup'] = True
            res['followup_questions'] = s.get('followup_questions', [])
            res['done'] = False
        else:
            store.close_token(s['id'])
    else:
        store.save_session(s)
    res['audio'] = tts(res['reply'])  # None: page falls back to the browser's voice
    return res


@app.post('/c/{token}/proctor')
def proctor(token: str, body: ProctorIn):
    s = _candidate(token)
    try:
        res = interview.proctor(s, body.events, body.snapshot)
    except ValueError:
        return {'error': 'closed'}
    store.save_session(s)
    return res
