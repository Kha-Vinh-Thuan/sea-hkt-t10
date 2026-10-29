import logging
import os

_logger = logging.getLogger(__name__)

# Router (9router) ids carry a provider prefix ("cc/"); direct Anthropic ids do not.
# Only Claude models passed the structured-JSON probe through the router (DeepSeek ignores json_schema).
MODELS = [
    ('cc/claude-haiku-5-5', 'Haiku 5.5 (fast, cheap)'),
    ('cc/claude-sonnet-5-5', 'Sonnet 5.5 (balanced)'),
    ('cc/claude-opus-5-5', 'Opus 5.5 (best reasoning)'),
    ('cc/claude-fable-5-1', 'Fable 5.1 (frontier, expensive)'),
]
PRICE_PER_MTOK = {  # input, output USD; ponytail: ignores cache discounts and fallback-model pricing
    'claude-haiku-5-5': (0.10, 0.50),
    'claude-sonnet-5-5': (2.0, 10.0),
    'claude-opus-5-5': (4.0, 20.0),
    'claude-fable-5-1': (10.0, 50.0),
}
# Fable rejects forced tool_choice; it gets 'auto' plus an instruction to call the tool.
NO_FORCED_TOOL = {'claude-fable-5-1'}
# Haiku: effort turns thinking on, which forced tool_choice rejects.
NO_EFFORT = {'claude-haiku-5-5'}
_client = None


class ClaudeError(Exception):
    pass


def _base_url():
    url = os.environ.get('ANTHROPIC_BASE_URL', '').rstrip('/')
    return url.removesuffix('/v1') or None  # SDK appends /v1/messages itself


def _model_id(model):
    """Router keeps the prefix; direct Anthropic needs the bare id."""
    return model if _base_url() else model.split('/', 1)[-1]


def ask(system, messages, schema, effort='medium', model='cc/claude-opus-5-5'):
    """One Claude call with structured JSON output. Raises ClaudeError on any failure."""
    global _client
    try:
        import anthropic
    except ImportError as e:
        raise ClaudeError("Python package 'anthropic' is not installed in the Odoo image.") from e
    if _client is None:
        _client = anthropic.Anthropic(
            base_url=_base_url(),
            api_key=os.environ.get('ANTHROPIC_AUTH_TOKEN') or os.environ.get('ANTHROPIC_API_KEY') or None)
    try:
        # JSON via a strict tool, not output_config.format: 9router drops format for some models.
        bare = model.split('/', 1)[-1]
        forced = bare not in NO_FORCED_TOOL
        response = _client.beta.messages.create(
            model=_model_id(model),
            max_tokens=16000,
            system=system if forced else system + "\n\nAlways answer by calling the `result` tool.",
            messages=messages,
            tools=[{'name': 'result', 'description': 'Return your answer.', 'input_schema': schema, 'strict': True}],
            tool_choice={'type': 'tool', 'name': 'result'} if forced else {'type': 'auto'},
            output_config={} if bare in NO_EFFORT else {'effort': effort},
            betas=['server-side-fallback-2026-07-01'],
            fallbacks='default',
        )
    except anthropic.APIStatusError as e:
        _logger.error("Claude API error %s (%s): %s", e.status_code, model, e.message)
        raise ClaudeError(f"Claude API error {e.status_code} ({model})") from e
    except anthropic.APIConnectionError as e:
        raise ClaudeError("Cannot reach Claude API") from e
    except TypeError as e:  # SDK raises this when no API key is configured
        raise ClaudeError("ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN is not set") from e
    if response.stop_reason == 'refusal':
        raise ClaudeError("Claude declined this request")
    if response.stop_reason == 'max_tokens':
        raise ClaudeError("Claude response was truncated")
    data = next((dict(b.input) for b in response.content if b.type == 'tool_use'), None)
    if data is None:
        raise ClaudeError(f"{model} did not return structured output")
    price_in, price_out = PRICE_PER_MTOK.get(model.split('/', 1)[-1], (0.0, 0.0))
    usage = response.usage
    data['_cost'] = (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1e6
    data['_model'] = model
    return data
