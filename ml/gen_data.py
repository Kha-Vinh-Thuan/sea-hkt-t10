"""Distillation data: Claude (teacher) role-plays full Vietnamese voice interviews.

Writes two datasets:
  data/interviewer.jsonl  chat samples for fine-tuning the local interviewer (Qwen + LoRA)
  data/scorer.jsonl       (question, answer, score 0-100) pairs for the PhoBERT answer scorer

Usage: python gen_data.py 300      # number of simulated interviews (~4 s each, parallel)
"""
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import anthropic

from prompts import interviewer_system

TEACHER = 'cc/claude-sonnet-5-5'  # good Vietnamese, 2x cheaper than Opus; ~$0.01/interview
JOBS = [
    ('Lập trình viên Python Backend', 'Django/FastAPI, PostgreSQL, REST API, Docker'),
    ('Lập trình viên Frontend React', 'React, TypeScript, CSS, tối ưu hiệu năng web'),
    ('Kỹ sư DevOps', 'CI/CD, Kubernetes, AWS, giám sát hệ thống'),
    ('Chuyên viên Kiểm thử (QA)', 'test case, kiểm thử tự động, Selenium, quy trình bug'),
    ('Kỹ sư Dữ liệu', 'SQL, ETL, Spark, data warehouse'),
    ('Lập trình viên Mobile', 'Flutter hoặc React Native, phát hành app store'),
    ('Business Analyst', 'thu thập yêu cầu, BPMN, user story, làm việc với khách hàng'),
    ('Chuyên viên Nhân sự', 'tuyển dụng, onboarding, luật lao động cơ bản'),
    ('Chuyên viên Marketing', 'digital marketing, Facebook Ads, SEO, đo lường chiến dịch'),
    ('Nhân viên Kinh doanh B2B', 'tìm khách hàng, đàm phán, CRM, chỉ tiêu doanh số'),
    ('Kế toán tổng hợp', 'sổ sách, thuế GTGT, báo cáo tài chính, phần mềm MISA'),
    ('Thực tập sinh Lập trình', 'kiến thức nền tảng, ham học, dự án cá nhân'),
]
PERSONAS = [  # drives answer quality so the scorer sees the full range
    ('xuất sắc', 'trả lời cụ thể, có số liệu, ví dụ thật, hiểu sâu'),
    ('khá', 'trả lời đúng ý nhưng thiếu chi tiết ở vài chỗ'),
    ('trung bình', 'trả lời chung chung, ví dụ mơ hồ'),
    ('yếu', 'trả lời lan man, sai kiến thức cơ bản, né câu hỏi'),
    ('gian lận', 'đọc câu trả lời quá trau chuốt như văn mẫu/AI viết, thiếu trải nghiệm cá nhân khi bị hỏi sâu'),
    ('lo lắng', 'năng lực khá nhưng nói ngắt quãng, ngập ngừng, lỗi nhận dạng giọng nói (thiếu dấu, sai từ)'),
]

SCHEMA = {
    'type': 'object',
    'properties': {
        'turns': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'interviewer': {'type': 'string'},
                    'candidate': {'type': 'string', 'description': "'' on the final closing turn"},
                    'answer_score': {'type': 'integer', 'description': '0-100 quality of this candidate answer'},
                    'flag': {'type': 'string', 'description': "contradiction/scripted-answer note, or ''"},
                },
                'required': ['interviewer', 'candidate', 'answer_score', 'flag'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['turns'],
    'additionalProperties': False,
}

client = anthropic.Anthropic(
    base_url=os.environ.get('ANTHROPIC_BASE_URL', '').rstrip('/').removesuffix('/v1') or None,
    api_key=os.environ.get('ANTHROPIC_AUTH_TOKEN') or os.environ.get('ANTHROPIC_API_KEY'))


def simulate(seed):
    rnd = random.Random(seed)
    job, skills = rnd.choice(JOBS)
    level, behaviour = rnd.choice(PERSONAS)
    n = rnd.randint(4, 7)
    plan = f"1. Giới thiệu bản thân và lý do ứng tuyển.\n2. Kinh nghiệm với {skills}.\n" \
           f"3. Một vấn đề khó đã giải quyết.\n4. Điểm mạnh, điểm yếu."
    system = interviewer_system(job, 'T10 Tech', plan, n)
    r = client.messages.create(
        model=TEACHER, max_tokens=6000,
        system=("Bạn mô phỏng một buổi phỏng vấn bằng giọng nói hoàn chỉnh để làm dữ liệu huấn luyện. "
                "Đóng vai người phỏng vấn tuân thủ CHÍNH XÁC hướng dẫn dưới đây, và đóng vai ứng viên mức "
                f"'{level}': {behaviour}. Lời ứng viên viết như văn nói đã qua nhận dạng giọng nói. "
                f"Đúng {n} câu trả lời của ứng viên, rồi một lượt kết thúc (candidate rỗng). Chấm answer_score "
                "khách quan cho từng câu trả lời.\n\n=== HƯỚNG DẪN NGƯỜI PHỎNG VẤN ===\n" + system),
        messages=[{'role': 'user', 'content': 'Bắt đầu mô phỏng.'}],
        tools=[{'name': 'result', 'description': 'Return the interview.', 'input_schema': SCHEMA, 'strict': True}],
        tool_choice={'type': 'tool', 'name': 'result'},
    )
    turns = next(b.input for b in r.content if b.type == 'tool_use')['turns']
    return job, system, level, turns


def to_samples(job, system, level, turns):
    """One chat sample per interviewer turn (assistant = JSON the Odoo side expects), plus scorer pairs."""
    chats, scores = [], []
    history = [{'role': 'user', 'content': '[Ứng viên đã vào phòng phỏng vấn.]'}]
    for i, t in enumerate(turns):
        last = i == len(turns) - 1 or not t['candidate']
        flags = [turns[i - 1]['flag']] if i and turns[i - 1]['flag'] else []
        reply = json.dumps({'reply': t['interviewer'], 'done': last, 'flags': flags}, ensure_ascii=False)
        chats.append({'messages': [{'role': 'system', 'content': system}] + history + [
            {'role': 'assistant', 'content': reply}], 'level': level})
        if last:
            break
        history = history + [{'role': 'assistant', 'content': reply}, {'role': 'user', 'content': t['candidate']}]
        scores.append({'job': job, 'question': t['interviewer'], 'answer': t['candidate'],
                       'score': max(0, min(100, t['answer_score'])), 'level': level})
    return chats, scores


def main(n):
    os.makedirs('data', exist_ok=True)
    done = 0
    with open('data/interviewer.jsonl', 'a', encoding='utf-8') as fi, \
            open('data/scorer.jsonl', 'a', encoding='utf-8') as fs, ThreadPoolExecutor(8) as pool:
        for fut in [pool.submit(simulate, random.randrange(1 << 30)) for _ in range(n)]:
            try:
                chats, scores = to_samples(*fut.result())
            except Exception as e:  # noqa: BLE001 - skip a bad simulation, keep the rest
                print('skip:', str(e)[:120])
                continue
            fi.writelines(json.dumps(c, ensure_ascii=False) + '\n' for c in chats)
            fs.writelines(json.dumps(s, ensure_ascii=False) + '\n' for s in scores)
            done += 1
            if done % 20 == 0:
                print(done, 'interviews', flush=True)
    print('done', done)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
