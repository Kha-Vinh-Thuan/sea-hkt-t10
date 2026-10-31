# Standalone usage

`models/matcher.py` has no Odoo dependency and can be embedded in another Python
application. The recommended entry point is the evidence-review service:

```python
from rag_filter_application.dto.requests import CriterionRequest, DocumentRequest, FilterRequest
from rag_filter_application.services.screening_service import FilterService
from matcher import review

request = FilterRequest(
    run_id="run-123", candidate_id="candidate-123",
    role_id="backend-engineer", role_version="role-v2",
    criteria=(CriterionRequest("java", "Java", "Java backend experience", True),),
    documents=(DocumentRequest("cv-123", "cv.pdf", cv_pdf_bytes, "sha256"),),
    model="your-pdf-capable-model",
)
handoff = FilterService(review).execute(request)
payload = handoff.to_dict()
```

For a web service or queue worker, inject a callable with this signature instead
of using HTTP inside the module:

```python
matcher = Matcher("model", chat_fn=my_chat_function)
```

The callable receives `(model, system, parts, schema)` and must return a Python
dictionary matching the supplied JSON schema.

For a SaaS application, use the application-layer DTOs and service instead of
passing unvalidated dictionaries between controllers and the matcher:

```python
from rag_filter_application.dto.requests import CriterionRequest, DocumentRequest, FilterRequest
from rag_filter_application.services.screening_service import FilterService
from matcher import review

request = FilterRequest(
    run_id="run-123",
    candidate_id="candidate-123",
    role_id="backend-engineer",
    role_version="role-v2",
    criteria=(CriterionRequest("java", "Java", "Java backend experience", True),),
    documents=(DocumentRequest("cv-123", "cv.pdf", cv_pdf_bytes, "sha256"),),
    model="your-pdf-capable-model",
)
response = FilterService(review).execute(request)
payload = response.to_dict()
```

The controller owns request validation/serialization; the application service
owns the use case; the matcher/OpenAI client remains an injected infrastructure
dependency.
