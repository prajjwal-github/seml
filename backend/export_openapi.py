"""Exports FastAPI OpenAPI specification to docs/openapi.json."""

import json
from pathlib import Path
from backend.app.main import app

docs_dir = Path(__file__).resolve().parent.parent / "docs"
docs_dir.mkdir(parents=True, exist_ok=True)
openapi_path = docs_dir / "openapi.json"

openapi_schema = app.openapi()
openapi_path.write_text(json.dumps(openapi_schema, indent=2), encoding="utf-8")
print(f"Exported OpenAPI schema to: {openapi_path}")
