"""Export the frozen API contract for the frontend: contracts/openapi.json + contracts/examples/*.json.

Usage:  uv run python scripts/export_openapi.py [--check]
--check exits non-zero if the files on disk differ from what the code would produce.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_examples import EXAMPLES  # noqa: E402
from lexishield.api.app import create_app  # noqa: E402
from lexishield.settings import BACKEND_DIR, Settings  # noqa: E402

CONTRACTS = BACKEND_DIR.parent / "contracts"


class _NoGateway:
    """The OpenAPI export never calls the model."""


def render() -> dict[Path, str]:
    app = create_app(Settings(), gateway=_NoGateway())  # type: ignore[arg-type]
    files = {CONTRACTS / "openapi.json": json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"}
    for name, value in EXAMPLES.items():
        data = [v.model_dump(mode="json") for v in value] if isinstance(value, list) else value.model_dump(mode="json")
        files[CONTRACTS / "examples" / f"{name}.json"] = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    files = render()
    stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if args.check:
        for p in stale:
            print(f"stale: {p.relative_to(CONTRACTS.parent)}")
        return 1 if stale else 0
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files to {CONTRACTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
