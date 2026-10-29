import importlib.util
from pathlib import Path
from unittest.mock import patch

_spec = importlib.util.spec_from_file_location(
    'rag_agent_under_test', Path(__file__).parents[1] / 'models' / 'agent.py')
agent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent)


def test_chunks_keep_long_text_and_sources():
    items = agent.build_index({'company': 'Company context ' * 100, 'cv': 'CV claim'}, 'embed')
    assert items and {x['source'] for x in items} == {'company', 'cv'}


def test_retrieve_keeps_each_source():
    index = [
        {'source': 'company', 'text': 'c', 'vec': [1.0, 0.0]},
        {'source': 'job', 'text': 'j', 'vec': [0.99, 0.01]},
        {'source': 'cv', 'text': 'v', 'vec': [0.0, 1.0]},
    ]
    got = agent.retrieve(index, [1.0, 0.0], k=1)
    assert {x['source'] for x in got} == {'company', 'job', 'cv'}


def test_next_turn_enforces_question_budget_and_json():
    with patch.object(agent, 'embed', return_value=[[1.0, 0.0]]), \
         patch.object(agent, 'chat', return_value={
             'score': 8, 'evidence': 'e', 'next_question': '**next?**', 'done': False, 'flags': []}):
        got = agent.next_turn({'turn_model': 'turn', 'embed_model': 'embed'},
                              {'job': 'Dev', 'company': 'Acme', 'max_questions': 2},
                              [{'source': 'job', 'text': 'JD', 'vec': [1.0, 0.0]}],
                              [{'question': 'q1', 'answer': 'a1', 'score': 8}], 'q1', 'a2')
    assert got['done'] is True
    assert got['question'] == 'next?'


def test_realtime_secret_never_exposes_api_key():
    with patch.object(agent, '_post', return_value={'value': 'ephemeral'} ) as post:
        assert agent.realtime_secret('gpt-realtime', 'marin', 'gpt-4o-transcribe') == 'ephemeral'
        assert post.call_args.args[2] == 'OPENAI_API_KEY'
