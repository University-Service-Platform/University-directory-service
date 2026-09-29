"""Write the service's OpenAPI document to docs/openapi.json.

Run after any API change:  python scripts/export_openapi.py
tests/test_openapi_spec.py fails while the committed file is out of date.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

OUTPUT = ROOT / "docs" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
