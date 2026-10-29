"""Local inference API for Odoo: fine-tuned interviewer + answer scorer, multi-tenant.

Layers (shared -> specific):
  1. base        shared Qwen LoRA interviewer + PhoBERT scorer (distilled + consented data only)
  2. industry    optional LoRA per industry in models/adapters/<industry>/, falls back to base
  3. context     job, plan, rubric, company sent in each request (no training)
  4. tenant      per-tenant score calibration learned from that tenant's recruiter decisions only

POST /interview  {tenant_id, industry, job, company, plan, max_answers, followup, messages} -> {reply, done, flags}
POST /score      {tenant_id, items:[{question, answer}]} -> {scores, calibrated}
POST /feedback   {tenant_id, share, items:[{job, question, answer, score}]} -> {stored, calibrated}
GET  /health
"""
import json
import os
import re
import threading

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from prompts import interviewer_system

app = FastAPI()
LORA, SCORER, ADAPTERS, TENANTS = 'models/interviewer-lora', 'models/scorer', 'models/adapters', 'data/tenants'
CALIBRATE_MIN = 20  # tenant labels before its calibration kicks in
TENANT_RE = r'^[A-Za-z0-9_-]{1,64}$'  # used as a directory name: no path traversal
_lock = threading.Lock()
_m = {}


def _interviewer(industry):
    """One 4-bit base in VRAM, LoRA adapters hot-swapped per request (~60 MB each)."""
    if 'lm' not in _m:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        base = json.load(open(LORA + '/train_info.json'))['base']
        model = AutoModelForCausalLM.from_pretrained(
            base, device_map='auto', dtype=torch.float16,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                                   bnb_4bit_compute_dtype=torch.float16))
        _m['lm'] = (AutoTokenizer.from_pretrained(LORA), PeftModel.from_pretrained(model, LORA, adapter_name='base').eval())
    tok, model = _m['lm']
    name = industry if industry and os.path.isdir(f'{ADAPTERS}/{industry}') else 'base'
    if name not in model.peft_config:
        model.load_adapter(f'{ADAPTERS}/{name}', adapter_name=name)
    model.set_adapter(name)
    return tok, model, name


def _scorer():
    if 'sc' not in _m:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        _m['sc'] = (AutoTokenizer.from_pretrained(SCORER),
                    AutoModelForSequenceClassification.from_pretrained(SCORER).to('cuda' if torch.cuda.is_available() else 'cpu').eval())
    return _m['sc']


def _raw_scores(items):
    tok, model = _scorer()
    enc = tok([i.question for i in items], [i.answer for i in items], truncation=True, max_length=256,
              padding=True, return_tensors='pt').to(model.device)
    with torch.inference_mode():
        return [float(p) for p in model(**enc).logits.squeeze(-1).clamp(0, 1) * 100]


def _tenant_dir(tenant_id):
    path = f'{TENANTS}/{tenant_id}'
    os.makedirs(path, exist_ok=True)
    return path


def _calibration(tenant_id):
    f = f'{TENANTS}/{tenant_id}/calibration.json'
    return json.load(open(f)) if os.path.exists(f) else None


def _fit_calibration(tenant_id):
    """Least-squares map shared-scorer score -> this tenant's labels. Only this tenant's data is used."""
    rows = [json.loads(l) for l in open(f'{TENANTS}/{tenant_id}/feedback.jsonl', encoding='utf-8')]
    if len(rows) < CALIBRATE_MIN:
        return None
    xs, ys = [r['raw'] for r in rows], [r['score'] for r in rows]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    var = sum((x - mx) ** 2 for x in xs)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var else 1.0
    calib = {'a': a, 'b': my - a * mx, 'n': len(rows)}
    json.dump(calib, open(f'{TENANTS}/{tenant_id}/calibration.json', 'w'))
    return calib


class Msg(BaseModel):
    role: str
    content: str


class InterviewIn(BaseModel):
    tenant_id: str = Field(pattern=TENANT_RE)
    industry: str = Field('', pattern=r'^[a-z_]{0,32}$')
    job: str
    company: str
    plan: str
    max_answers: int = 10
    followup: bool = False
    messages: list[Msg]


class QA(BaseModel):
    question: str
    answer: str
    job: str = ''
    score: int | None = None


class Items(BaseModel):
    tenant_id: str = Field(pattern=TENANT_RE)
    share: bool = False  # tenant consented to its anonymised labels improving the shared base model
    provenance: dict = {}  # source, candidate consent version/time, label type: kept with every stored label
    items: list[QA]


@app.get('/health')
def health():
    info = {}
    for name, path in (('interviewer', LORA), ('scorer', SCORER)):
        f = path + '/train_info.json'
        info[name] = json.load(open(f)) if os.path.exists(f) else None
    info['industry_adapters'] = sorted(os.listdir(ADAPTERS)) if os.path.isdir(ADAPTERS) else []
    f = SCORER + '/trust_report.json'
    info['trust_report'] = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else None
    return info


@app.post('/interview')
def interview(body: InterviewIn):
    if not os.path.exists(LORA):
        raise HTTPException(503, 'interviewer not trained yet')
    system = interviewer_system(body.job, body.company, body.plan, body.max_answers, body.followup)
    msgs = [{'role': 'system', 'content': system}] + [m.model_dump() for m in body.messages][-7:]
    with _lock, torch.inference_mode():  # one GPU, one adapter active at a time
        tok, model, adapter = _interviewer(body.industry)
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors='pt').to(model.device)
        out = model.generate(ids, max_new_tokens=200, do_sample=True, temperature=0.6, top_p=0.9,
                             repetition_penalty=1.05)
    text = tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
    match = re.search(r'\{.*\}', text, re.S)
    try:
        data = json.loads(match.group(0))
        return {'reply': str(data['reply']).strip(), 'done': bool(data.get('done')),
                'flags': [str(f) for f in data.get('flags') or [] if f], 'adapter': adapter}
    except (AttributeError, KeyError, ValueError):
        raise HTTPException(502, f'bad model output: {text[:200]}')


@app.post('/score')
def score(body: Items):
    if not os.path.exists(SCORER):
        raise HTTPException(503, 'scorer not trained yet')
    raw, calib = _raw_scores(body.items), _calibration(body.tenant_id)
    if calib:
        raw = [calib['a'] * r + calib['b'] for r in raw]
    return {'scores': [round(min(100, max(0, r))) for r in raw], 'calibrated': bool(calib)}


@app.post('/feedback')
def feedback(body: Items):
    """Recruiter labels, stored per tenant. They tune that tenant's calibration only; they reach the shared
    base model (train_scorer.py) only when the tenant opted in with share=true."""
    items = [i for i in body.items if i.score is not None]
    if not items:
        return {'stored': 0, 'calibrated': bool(_calibration(body.tenant_id))}
    raw = _raw_scores(items) if os.path.exists(SCORER) else [50.0] * len(items)
    with open(f'{_tenant_dir(body.tenant_id)}/feedback.jsonl', 'a', encoding='utf-8') as f:
        f.writelines(json.dumps(dict(i.model_dump(), raw=r, shared=body.share, provenance=body.provenance),
                                ensure_ascii=False) + '\n'
                     for i, r in zip(items, raw))
    calib = _fit_calibration(body.tenant_id)
    return {'stored': len(items), 'calibrated': bool(calib), 'labels': calib and calib['n']}
