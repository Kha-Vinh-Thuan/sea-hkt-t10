import json
import logging
import os
import urllib.error
import urllib.request

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# The interview AI runs as its own service (ml/api.py). Odoo is one tenant of it, nothing more.
URL = os.environ.get('T10_API_URL', 'http://ml:8000').rstrip('/')


def call(method, path, payload=None, timeout=30):
    """Authenticated call to T10 Interview AI. Raises UserError so the orchestrator logs it and retries later."""
    key = os.environ.get('T10_API_KEY')
    if not key:
        raise UserError("T10_API_KEY is not set: create a tenant on the T10 Interview AI service first.")
    req = urllib.request.Request(URL + path, json.dumps(payload).encode() if payload is not None else None,
                                 {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise UserError(f"T10 Interview AI {path}: HTTP {e.code} {e.read()[:300]!r}") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise UserError(f"T10 Interview AI unavailable: {e}") from e
