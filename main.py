from __future__ import annotations

import argparse
import json

from src.ai.client import OllamaClient, RuleBasedMockClient
from src.environment.simulator import Simulator
from src.models.loader import load_race_config
from src.output.results import write_results


def main() -> None:
    parser = argparse.ArgumentParser(description="F1 strategy-AI race simulator (Phase 1)")
    parser.add_argument("--config", default="config/race_config.json")
    parser.add_argument(
        "--ai", choices=["mock", "ollama"], default="mock", help="AI backend for strategy decisions"
    )
    parser.add_argument("--ollama-model", default="qwen2.5:7b")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument(
        "--ollama-timeout", type=float, default=90.0, help="Per-request timeout in seconds for Ollama calls"
    )
    parser.add_argument("--run-dir", default=None, help="Defaults to runs/<race_id>")
    args = parser.parse_args()

    config = load_race_config(args.config)
    run_dir = args.run_dir or f"runs/{config.race_id}"

    if args.ai == "ollama":
        ai_client = OllamaClient(model=args.ollama_model, host=args.ollama_host, timeout=args.ollama_timeout)
    else:
        ai_client = RuleBasedMockClient()

    sim = Simulator(config=config, ai_client=ai_client, run_dir=run_dir)
    results = sim.run()

    out_path = write_results(results, run_dir)
    print(json.dumps(results, indent=2))
    print(f"\nResults written to {out_path}")
    print(f"Telemetry: {run_dir}/telemetry.jsonl")
    print(f"Decisions: {run_dir}/decisions.jsonl")


if __name__ == "__main__":
    main()
