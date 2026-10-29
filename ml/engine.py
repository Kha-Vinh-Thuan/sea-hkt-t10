"""Model runtime: fine-tuned interviewer (Qwen + LoRA per industry) and answer scorer (PhoBERT) with per-tenant
calibration. Heavy imports are lazy so the API and its tests run without a GPU.

Layers (shared -> specific): 1 base model, 2 industry LoRA, 3 per-session context (no training),
4 per-tenant score calibration learned only from that tenant's own recruiter decisions.
"""
import json
import logging
import os
import re
import threading

_logger = logging.getLogger(__name__)

LORA, SCORER, ADAPTERS, TENANTS = 'models/interviewer-lora', 'models/scorer', 'models/adapters', 'data/tenants'
FALLBACK = os.environ.get('T10_FALLBACK_MODEL', 'cc/claude-sonnet-5-5')
REPORT_MODEL = os.environ.get('T10_REPORT_MODEL', 'cc/claude-opus-5-5')
CALIBRATE_MIN = 20
_lock = threading.Lock()
_m = {}


def release_ok():
    """Scorer may only be used if its last fairness audit passed (fairness.py writes trust_report.json)."""
    f = SCORER + '/trust_report.json'
    return os.path.exists(f) and json.load(open(f, encoding='utf-8')).get('release_ok', False)


def trust_report():
    f = SCORER + '/trust_report.json'
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else None


def _interviewer(industry):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    if 'lm' not in _m:
        base = json.load(open(LORA + '/train_info.json'))['base']
        model = AutoModelForCausalLM.from_pretrained(
            base, device_map='auto', dtype=torch.float16,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                                   bnb_4bit_compute_dtype=torch.float16))
        _m['lm'] = (AutoTokenizer.from_pretrained(LORA), PeftModel.from_pretrained(model, LORA, adapter_name='base').eval())
        _m['lm_base'] = base
    tok, model = _m['lm']
    name = industry if industry and os.path.isdir(f'{ADAPTERS}/{industry}') else 'base'
    if name not in model.peft_config:
        model.load_adapter(f'{ADAPTERS}/{name}', adapter_name=name)
    model.set_adapter(name)
    return tok, model, name


def interview(tenant_id, ctx, messages):
    """Fine-tuned interviewer turn, or None so the caller falls back to Claude."""
    if not os.path.exists(LORA):
        return None
    import torch
    from prompts import interviewer_system
    from interview import plan
    system = interviewer_system(ctx['job_title'], ctx.get('company', ''), plan(ctx),
                                 ctx.get('max_answers', 8), followup=bool(ctx.get('followup_round')))
    msgs = [{'role': 'system', 'content': system}] + messages[-7:]
    try:
        with _lock, torch.inference_mode():  # one GPU, one adapter active at a time
            tok, model, adapter = _interviewer(ctx.get('industry'))
            enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors='pt',
                                           return_dict=True).to(model.device)
            out = model.generate(**enc, max_new_tokens=120, do_sample=True, temperature=0.6, top_p=0.9,
                                 repetition_penalty=1.05, pad_token_id=tok.eos_token_id)
            ids = enc['input_ids']
        text = tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
        data = json.loads(re.search(r'\{.*\}', text, re.S).group(0))
        return {'reply': str(data['reply']).strip(), 'done': bool(data.get('done')),
                'flags': [str(f) for f in data.get('flags') or [] if f],
                'model': f"{_m['lm_base']}+lora:{adapter}"}
    except Exception as e:  # noqa: BLE001 - live candidate: fall back, never crash the turn
        _logger.warning("local interviewer failed, falling back: %s", e)
        return None


def _scorer():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    if 'sc' not in _m:
        _m['sc'] = (AutoTokenizer.from_pretrained(SCORER), AutoModelForSequenceClassification.from_pretrained(SCORER)
                    .to('cuda' if torch.cuda.is_available() else 'cpu').eval())
    return _m['sc']


def raw_scores(pairs):
    import torch
    tok, model = _scorer()
    enc = tok([p['question'] for p in pairs], [p['answer'] for p in pairs], truncation=True, max_length=256,
              padding=True, return_tensors='pt').to(model.device)
    with torch.inference_mode():
        return [float(x) for x in model(**enc).logits.squeeze(-1).clamp(0, 1) * 100]


def score(tenant_id, pairs):
    """Per-answer 0-100, tenant-calibrated. None if the scorer is missing or failed its fairness audit."""
    if not os.path.exists(SCORER) or not release_ok():
        return None
    raw, calib = raw_scores(pairs), calibration(tenant_id)
    if calib:
        raw = [calib['a'] * r + calib['b'] for r in raw]
    info = json.load(open(SCORER + '/train_info.json'))
    return {'scores': [round(min(100, max(0, r))) for r in raw], 'calibrated': bool(calib),
            'model': f"{info['base']}@{os.path.getmtime(SCORER + '/train_info.json'):.0f}"}


def _tenant_dir(tenant_id):
    path = f'{TENANTS}/{tenant_id}'
    os.makedirs(path, exist_ok=True)
    return path


def calibration(tenant_id):
    f = f'{TENANTS}/{tenant_id}/calibration.json'
    return json.load(open(f)) if os.path.exists(f) else None


def add_feedback(tenant_id, rows, share):
    """Store recruiter labels for this tenant only; refit its calibration. rows: [{question, answer, score,
    provenance}]. They reach the shared base model (train_scorer.py) only if the tenant opted in (share)."""
    raw = raw_scores(rows) if os.path.exists(SCORER) else [50.0] * len(rows)
    path = f'{_tenant_dir(tenant_id)}/feedback.jsonl'
    with open(path, 'a', encoding='utf-8') as f:
        f.writelines(json.dumps(dict(r, raw=x, shared=share), ensure_ascii=False) + '\n' for r, x in zip(rows, raw))
    data = [json.loads(l) for l in open(path, encoding='utf-8')]
    if len(data) < CALIBRATE_MIN:
        return None
    xs, ys = [d['raw'] for d in data], [d['score'] for d in data]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    var = sum((x - mx) ** 2 for x in xs)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var else 1.0
    calib = {'a': a, 'b': my - a * mx, 'n': len(data)}
    json.dump(calib, open(f'{TENANTS}/{tenant_id}/calibration.json', 'w'))
    return calib


def health():
    info = {}
    for name, path in (('interviewer', LORA), ('scorer', SCORER)):
        f = path + '/train_info.json'
        info[name] = json.load(open(f)) if os.path.exists(f) else None
    info['industry_adapters'] = sorted(os.listdir(ADAPTERS)) if os.path.isdir(ADAPTERS) else []
    info['scorer_release_ok'] = release_ok()
    return info
