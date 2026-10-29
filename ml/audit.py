"""Trust checks for the distilled dataset.

1. Blind re-score: a different model scores a random sample WITHOUT seeing the persona; compare with stored scores.
2. Export a blind CSV for a human recruiter to label (data/human_audit.csv); re-run with --human to compare.

Usage: python audit.py [n]          # model cross-check + export CSV
       python audit.py --human      # after filling column human_score in data/human_audit.csv
"""
import csv
import json
import os
import random
import statistics as st
import sys

SCHEMA = {'type': 'object', 'properties': {'score': {'type': 'integer'}}, 'required': ['score'],
          'additionalProperties': False}


def sample(n):
    rows = [json.loads(l) for l in open('data/scorer.jsonl', encoding='utf-8')]
    return random.Random(42).sample(rows, min(n, len(rows)))


def report(name, gold, other):
    diffs = [abs(a - b) for a, b in zip(gold, other)]
    agree = sum((a >= 60) == (b >= 60) for a, b in zip(gold, other)) / len(gold)
    corr = st.correlation(gold, other) if len(set(other)) > 1 else 0
    print(f"{name}: n={len(gold)}  MAE={st.mean(diffs):.1f}  pass/fail agreement={agree:.0%}  correlation={corr:.2f}")


def model_check(n):
    from claude import ask  # JSON via strict forced tool
    rows, gold, other = sample(n), [], []
    for r in rows:
        try:
            res = ask("Chấm chất lượng câu trả lời phỏng vấn từ 0 đến 100 cho vị trí đã nêu. Khách quan, dựa trên nội dung.",
                      [{'role': 'user', 'content': f"Vị trí: {r['job']}\nCâu hỏi: {r['question']}\nTrả lời: {r['answer']}"}],
                      SCHEMA, effort='low', model='cc/claude-opus-5-5')
        except Exception as e:  # noqa: BLE001
            print('skip', e)
            continue
        gold.append(r['score'])
        other.append(res['score'])
    report('Sonnet (dataset) vs Opus blind', gold, other)
    with open('data/human_audit.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['id', 'job', 'question', 'answer', 'human_score'])
        for i, r in enumerate(rows):
            w.writerow([i, r['job'], r['question'], r['answer'], ''])
    print("Blind CSV for a recruiter: data/human_audit.csv (fill human_score 0-100, then: python audit.py --human)")


def human_check():
    rows = sample(10 ** 9)  # same seed, same order as the export
    by_id = {}
    for line in csv.DictReader(open('data/human_audit.csv', encoding='utf-8-sig')):
        if line['human_score'].strip():
            by_id[int(line['id'])] = int(line['human_score'])
    n = len(list(csv.DictReader(open('data/human_audit.csv', encoding='utf-8-sig'))))
    gold = [r['score'] for i, r in enumerate(sample(n)) if i in by_id]
    report('Dataset vs human recruiter', gold, list(by_id.values()))


if __name__ == '__main__':
    human_check() if '--human' in sys.argv else model_check(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
