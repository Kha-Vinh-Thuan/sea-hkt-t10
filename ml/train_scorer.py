"""Answer scorer: PhoBERT regression head, (question, answer) -> quality 0-100.

Trained on distilled scores plus real recruiter labels from tenants that opted in (weighted higher).
Per-tenant taste is handled by calibration in engine.py, never by mixing tenants' private labels.

Usage: python train_scorer.py
Output: models/scorer/ + MAE / pass-fail accuracy on a held-out split.
"""
import glob
import json
import random

import numpy as np
import torch
from datasets import Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments)

BASE = 'vinai/phobert-base-v2'
OUT = 'models/scorer'
FEEDBACK_WEIGHT = 3  # one real recruiter-labelled answer counts like three distilled ones


def rows():
    data = [json.loads(l) for l in open('data/scorer.jsonl', encoding='utf-8')]
    # Real recruiter labels join the shared model only from tenants that opted in (share=true).
    for path in glob.glob('data/tenants/*/feedback.jsonl'):
        shared = [dict(r, source='real') for r in map(json.loads, open(path, encoding='utf-8'))
                  if r.get('shared') and r.get('provenance', {}).get('consent_version')]  # candidate opted in
        data += shared * FEEDBACK_WEIGHT
    random.Random(0).shuffle(data)
    return data


# Debiasing augmentation: same label, different accent/identity -> the model learns these must not move the score.
# Identities here are deliberately DIFFERENT from fairness.py's test groups so the audit is not trained on.
TRAIN_INTROS = [
    'Dạ em là Phạm Quốc Anh, quê Hải Phòng, 27 tuổi.', 'Dạ em là Đỗ Thu Trang, quê Nam Định, 31 tuổi.',
    'Dạ em là Võ Minh Khang, quê Đồng Nai, 23 tuổi.', 'Dạ em là Huỳnh Ngọc Lan, quê An Giang, 35 tuổi.',
    'Dạ em là Phan Đức Long, quê Quảng Nam, 42 tuổi.', 'Dạ em là Ngô Thị Thảo, quê Thanh Hóa, 26 tuổi.',
    'Dạ em là Lò Văn Sáng, người Thái, quê Sơn La, 28 tuổi.', 'Dạ em là Bùi Khánh Linh, quê Bình Định, 30 tuổi.',
]


def augment(train, seed=1):
    from fairness import dialect
    rng, out = random.Random(seed), []
    for i, r in enumerate(train):
        out.append(dict(r, answer=dialect(r['answer'], rng.choice(['bac', 'trung', 'nam']), seed * 100000 + i)))
        if rng.random() < 0.5:
            out.append(dict(r, answer=f"{rng.choice(TRAIN_INTROS)} {r['answer']}"))
    return out


def main():
    data = rows()
    cut = max(50, len(data) // 10)
    data = data[:cut] + data[cut:] + augment(data[cut:])  # augment the train split only; held-out stays clean
    tok = AutoTokenizer.from_pretrained(BASE)

    def enc(batch):
        out = tok(batch['question'], batch['answer'], truncation=True, max_length=256)
        out['labels'] = [s / 100.0 for s in batch['score']]
        return out

    held, train = Dataset.from_list(data[:cut]), Dataset.from_list(data[cut:])
    cols = ['question', 'answer', 'score']
    train = train.select_columns(cols).map(enc, batched=True, remove_columns=cols)
    held = held.select_columns(cols).map(enc, batched=True, remove_columns=cols)
    model = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=1, problem_type='regression')

    def metrics(p):
        pred, gold = p.predictions.squeeze() * 100, p.label_ids * 100
        return {'mae': float(np.abs(pred - gold).mean()),
                'pass_fail_acc': float(((pred >= 60) == (gold >= 60)).mean())}

    trainer = Trainer(
        model=model, train_dataset=train, eval_dataset=held, processing_class=tok, compute_metrics=metrics,
        args=TrainingArguments(output_dir='models/_ckpt_scorer', num_train_epochs=4, learning_rate=3e-5,
                               per_device_train_batch_size=16, per_device_eval_batch_size=32, fp16=torch.cuda.is_available(),
                               eval_strategy='epoch', save_strategy='no', logging_steps=20, report_to=[], warmup_ratio=0.1),
    )
    trainer.train()
    result = trainer.evaluate()
    trainer.save_model(OUT)
    tok.save_pretrained(OUT)
    real = sum(1 for r in data if r.get('source') == 'real') // FEEDBACK_WEIGHT
    info = {'base': BASE, 'train': len(train), 'held_out': len(held),
            'data_sources': {'distilled_synthetic': len(data) - real * FEEDBACK_WEIGHT, 'real_consented': real},
            'mae': round(result['eval_mae'], 2), 'pass_fail_acc': round(result['eval_pass_fail_acc'], 3)}
    json.dump(info, open(OUT + '/train_info.json', 'w'), indent=2)
    print(info)


if __name__ == '__main__':
    main()
