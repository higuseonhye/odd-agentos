# agentos-sdk

Installable Python client for the AgentOS HTTP API.

```bash
pip install -e .
```

```python
from agentos_sdk import AgentOS

client = AgentOS(project="my-project", base_url="http://localhost:8080")
run_id = client.run("workflows/sample.yaml")
report = client.diagnose(run_id)
```

The server package in this repository uses the top-level module name `agentos` (Flask API and runtime). This distribution exposes **`agentos_sdk`** so both can coexist in one checkout when you install this package in editable mode.

Optional tracing decorator:

```python
from agentos_sdk.decorators import trace

@trace(requires_approval=True, risk_level="high")
def my_fn(x: str) -> str:
    return x.upper()
```
