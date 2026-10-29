"""End-to-end API test with the models mocked (no GPU, no network). Run: python -m pytest -q test_api.py"""
import hashlib
import hmac
import json
import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ['T10_ADMIN_KEY'] = 'admin-test'
import api  # noqa: E402
import interview  # noqa: E402
import store  # noqa: E402

TURN = {'reply': 'Bạn giới thiệu bản thân nhé?', 'done': False, 'flags': [], 'model': 'local/qwen+lora:base'}
NARRATIVE = {'summary': 'Ổn', 'criteria': [], 'strengths': ['a'], 'concerns': [], 'next_round_focus': [],
             'integrity_score': 95, 'integrity_summary': 'Không có dấu hiệu', 'followup_questions': [],
             '_cost': 0.1, '_model': 'x'}


@pytest.fixture
def client(monkeypatch):
    store._conn = None
    monkeypatch.setattr(store, 'DB', tempfile.mktemp(suffix='.db'))
    monkeypatch.setattr(api, 'tts', lambda text: None)
    monkeypatch.setattr(api, 'emit', lambda *a, **k: sent.append(a))
    sent.clear()
    c = TestClient(api.app)
    r = c.post('/admin/tenants', json={'name': 'Acme', 'webhook_url': 'http://hook'}, headers={'X-Admin-Key': 'admin-test'})
    c.headers['Authorization'] = 'Bearer ' + r.json()['api_key']
    return c


sent = []


def _session(c, **ctx):
    r = c.post('/v1/sessions', json={'context': {'job_title': 'Python Dev', 'company': 'Acme', 'max_answers': 2,
                                                 'questions': ['Kể về dự án Django'], **ctx}})
    assert r.status_code == 201
    return r.json()


def _interview(c, token, score=80, consent_training=True):
    assert c.post(f'/c/{token}/consent', json={'training': consent_training}).json() == {'ok': True}
    with patch('engine.interview', side_effect=lambda *a: dict(TURN)), \
            patch('engine.score', return_value={'scores': [score, score], 'calibrated': False, 'model': 'phobert@1'}), \
            patch('interview.ask', side_effect=lambda **kwargs: dict(NARRATIVE)):
        assert c.post(f'/c/{token}/chat', json={'message': ''}).json()['reply'] == TURN['reply']
        c.post(f'/c/{token}/proctor', json={'events': [{'type': 'tab_hidden', 'at': 3}, {'type': 'evil'}]})
        c.post(f'/c/{token}/chat', json={'message': 'Em làm Django 3 năm'})
        result = c.post(f'/c/{token}/chat', json={'message': 'Em tối ưu query'}).json()
        if result.get('followup'):
            for answer in ('Em đo bằng KPI.', 'Tăng 20 phần trăm.', 'Duy trì ổn định.'):
                result = c.post(f'/c/{token}/chat', json={'message': answer}).json()
                if result['done']:
                    break
        return result


def test_full_flow_report_and_webhooks(client):
    s = _session(client)
    assert s['join_url'].endswith('/join/' + s['embed_token'])
    assert _interview(client, s['embed_token'])['done'] is True
    got = client.get(f"/v1/sessions/{s['id']}").json()
    assert got['status'] == 'reported'
    rep = got['report']
    assert (rep['score'], rep['verdict'], rep['integrity']['events']) == (80, 'pass', {'tab_hidden': 1})
    assert rep['models']['interviewer'] == 'local/qwen+lora:base' and rep['models']['scorer'] == 'phobert@1'
    assert [e[1] for e in sent] == ['session.started', 'session.completed', 'report.ready']
    # link is dead after the interview
    assert client.post(f"/c/{s['embed_token']}/chat", json={'message': 'x'}).status_code == 404


def test_gray_zone_means_human_decides(client):
    s = _session(client)
    _interview(client, s['embed_token'], score=60)
    rep = client.get(f"/v1/sessions/{s['id']}").json()['report']
    assert rep['verdict'] == 'review'
    with patch('engine.add_feedback', return_value=None):
        r = client.post(f"/v1/sessions/{s['id']}/decision", json={'decision': 'hire'}).json()
    assert r['agrees_with_ai'] is None and r['used_for_learning'] is True


def test_gray_zone_opens_same_link_for_bounded_followup(client):
    s = _session(client)
    followup = dict(NARRATIVE, followup_questions=['Bạn đã đo kết quả thế nào?'])
    final = dict(NARRATIVE, followup_questions=[])
    assert client.post(f"/c/{s['embed_token']}/consent", json={'training': False}).json() == {'ok': True}
    with patch('engine.interview', side_effect=lambda *a: dict(TURN)), \
            patch('engine.score', return_value={'scores': [60, 60], 'calibrated': False, 'model': 'phobert@1'}), \
            patch('interview.ask', side_effect=[followup, final]):
        client.post(f"/c/{s['embed_token']}/chat", json={'message': ''})
        client.post(f"/c/{s['embed_token']}/chat", json={'message': 'A'})
        first_done = client.post(f"/c/{s['embed_token']}/chat", json={'message': 'B'}).json()
        assert first_done['done'] is False and first_done['followup'] is True
        assert first_done['followup_questions'] == ['Bạn đã đo kết quả thế nào?']
        assert client.get(f"/c/{s['embed_token']}/info").json()['followup'] is True
        second_done = client.post(f"/c/{s['embed_token']}/chat", json={'message': 'Em đo bằng KPI.'}).json()
        assert second_done['done'] is False
        third_done = client.post(f"/c/{s['embed_token']}/chat", json={'message': 'Tăng 20 phần trăm.'}).json()
        assert third_done['done'] is False
        fourth_done = client.post(f"/c/{s['embed_token']}/chat", json={'message': 'Duy trì ổn định.'}).json()
        assert fourth_done['done'] is True
    got = client.get(f"/v1/sessions/{s['id']}").json()
    assert got['status'] == 'reported'
    assert client.post(f"/c/{s['embed_token']}/chat", json={'message': 'x'}).status_code == 404


def test_no_learning_without_candidate_consent(client):
    s = _session(client)
    _interview(client, s['embed_token'], consent_training=False)
    with patch('engine.add_feedback') as learn:
        r = client.post(f"/v1/sessions/{s['id']}/decision", json={'decision': 'reject'}).json()
    learn.assert_not_called()
    assert (r['used_for_learning'], r['agrees_with_ai']) == (False, False)


def test_feedback_carries_provenance(client):
    s = _session(client)
    _interview(client, s['embed_token'])
    with patch('engine.add_feedback', return_value={'n': 20}) as learn:
        client.post(f"/v1/sessions/{s['id']}/decision", json={'decision': 'hire'})
    tenant_id, rows, share = learn.call_args.args
    assert rows[0]['score'] == 80 and rows[0]['provenance']['consent_version'] == api.CONSENT_VERSION
    assert share is False  # tenant did not opt in to the shared model


def test_local_model_down_falls_back_to_claude(client):
    s = _session(client)
    client.post(f"/c/{s['embed_token']}/consent", json={'training': False})
    with patch('engine.interview', return_value=None), \
            patch('interview.ask', return_value={'reply': 'Fallback?', 'done': False, 'flags': [], '_cost': 0,
                                                 '_model': 'cc/claude-sonnet-5-5'}) as claude:
        assert client.post(f"/c/{s['embed_token']}/chat", json={'message': ''}).json()['reply'] == 'Fallback?'
    assert claude.call_args.kwargs['model'] == 'cc/claude-sonnet-5-5'


def test_unaudited_scorer_is_never_used(client):
    """No trained score (missing or failed fairness audit) -> no AI verdict, a human decides."""
    s = _session(client)
    client.post(f"/c/{s['embed_token']}/consent", json={'training': False})
    with patch('engine.interview', side_effect=lambda *a: dict(TURN)), patch('engine.release_ok', return_value=False), \
            patch('engine.os.path.exists', return_value=True), patch('interview.ask', return_value=dict(NARRATIVE)):
        for msg in ('', 'a', 'b'):
            client.post(f"/c/{s['embed_token']}/chat", json={'message': msg})
    rep = client.get(f"/v1/sessions/{s['id']}").json()['report']
    assert (rep['score'], rep['verdict']) == (None, 'review')


def test_tenant_isolation_and_auth(client):
    s = _session(client)
    other = TestClient(api.app)
    key = other.post('/admin/tenants', json={'name': 'Other'}, headers={'X-Admin-Key': 'admin-test'}).json()['api_key']
    other.headers['Authorization'] = 'Bearer ' + key
    assert other.get(f"/v1/sessions/{s['id']}").status_code == 404
    assert other.get('/v1/sessions').json() == []
    assert TestClient(api.app).get('/v1/sessions').status_code == 401
    assert client.post('/admin/tenants', json={'name': 'x'}).status_code == 401
    assert client.post('/v1/sessions', json={'context': {'job_title': 'x', 'industry': '../etc'}}).status_code == 422


def test_chat_requires_consent_and_bad_tokens_404(client):
    s = _session(client)
    assert client.post(f"/c/{s['embed_token']}/chat", json={'message': ''}).status_code == 409
    assert client.post('/c/short/chat', json={'message': ''}).status_code == 404
    assert 'Đường dẫn không còn hiệu lực' in client.get('/join/nope').text


def test_webhook_signature():
    body = b'{"event":"x"}'
    assert api.sign('s3cret', body) == 'sha256=' + hmac.new(b's3cret', body, hashlib.sha256).hexdigest()


def test_verdict_bands():
    assert [interview.verdict(x) for x in (56, 57, 63, 64)] == ['reject', 'review', 'review', 'pass']
    assert interview.qa_pairs([{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': 'Q'},
                               {'role': 'user', 'content': 'A'}]) == [{'question': 'Q', 'answer': 'A'}]
    assert json.dumps(interview.REPORT_SCHEMA)  # serialisable for the tool schema
    assert interview.plan({'questions': ['A'], 'verify_claims': ['Lead 10 người']}) == \
        "1. A\n2. Hỏi cụ thể để xác minh: Lead 10 người"
