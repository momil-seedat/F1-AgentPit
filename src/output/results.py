from __future__ import annotations

import json
from pathlib import Path


def write_results(results: dict, run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "results.json"
    out_path.write_text(json.dumps(results, indent=2))
    return out_path
