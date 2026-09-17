# F1 Strategy-AI Simulator — Phase 1

A minimal, deterministic F1 race simulator where a single AI agent makes
strategy decisions (PIT / STAY_OUT / PUSH) under a limited token budget,
triggered by threshold-crossing events in the simulation (tyre wear, fuel,
rain, gaps, lap-time delta).

## Run locally

```bash
python3 main.py --config config/race_config.json --ai mock
```

`--ai mock` uses a deterministic rule-based stand-in for the AI (no network
calls) — good for validating the simulator itself.

To use a real local model via Ollama:

```bash
ollama serve
ollama pull qwen2.5:7b
python3 main.py --ai ollama --ollama-model qwen2.5:7b
```

Optional flags: `--ollama-host` (default `http://localhost:11434`),
`--ollama-timeout` (default `90` seconds — CPU-only inference can be slow,
raise this if you see `TimeoutError`).

## Run with Docker

Mock AI, simulator only:

```bash
docker build -t f1-sim .
docker run --rm -v "$(pwd)/runs:/app/runs" f1-sim
```

Simulator + Ollama together (Ollama runs as its own service):

```bash
docker compose up --build
```

The first `docker compose up` will need a model pulled into the Ollama
container once:

```bash
docker compose exec f1-ollama ollama pull qwen2.5:7b
```

Then re-run just the simulator once the model is pulled:

```bash
docker compose up f1-simulator
```

## View results in a browser

A small local viewer at `viewer/index.html` renders the podium, full
classification, and each car's AI strategy log (trigger → decision → reason).
It fetches `runs/<race_id>/results.json` and `decisions.jsonl` at load time,
so it always reflects your latest run — serve the project root over HTTP
(it won't work opened directly as a `file://` path):

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000/viewer/` (add `?race=<race_id>` for a
different run than `race_001`).

## Output

Each run writes to `runs/<race_id>/`:

- `telemetry.jsonl` — one record per car per tick (position, speed, fuel, tyres, weather, AI budget)
- `decisions.jsonl` — one record per AI decision (trigger, state before, decision, tokens used)
- `results.json` — final classification, pit stops, tokens used, AI decisions per car

## Project layout

```
config/           race_config.json — race-level settings (laps, tick, token budget, seed)
data/             track.json, tyres.json, drivers.json, cars.json — static definitions
src/models/       dataclasses + JSON loaders for all schemas
src/environment/  physics, weather, track, standings, trigger system, simulator loop
src/ai/           AgentClient interface, RuleBasedMockClient, OllamaClient, decision context
src/logging/      telemetry + decision JSONL writers
src/output/       final results.json writer
viewer/           static HTML/JS results dashboard (reads runs/<race_id>/ at load time)
main.py           CLI entrypoint
```

## Design notes

- **Determinism**: a single seeded `random.Random` drives weather drift and
  driver-consistency speed noise. Same `seed` → same race, every time.
- **Edge-triggered thresholds with hysteresis**: triggers fire once on
  crossing (e.g. tyre degradation 69%→70%), not on every tick while above
  threshold. Each trigger re-arms only after the value falls back below
  `threshold - rearm_margin`, preventing flapping at the boundary.
  See `src/environment/triggers.py`.
- **Token budget as a real constraint**: each car gets `ai_token_budget`
  tokens (default 700) plus a small `ai_token_overage` allowance (default
  100) to absorb the last call going over. Once remaining tokens can't
  safely cover another AI call, `BudgetExhaustedClient` takes over with a
  conservative default policy instead of calling the AI — this makes "ran
  out of budget" a simulatable outcome, not just a logged number, and
  usage is hard-capped at `budget + overage` (800 by default).
- **Pluggable AI backend**: `AgentClient` is an abstract interface
  (`src/ai/client.py`). Phase 1 ships `RuleBasedMockClient` (for testing)
  and `OllamaClient` (for real local-model decisions). Phase 2 (multi-agent
  harness) can add new implementations without touching the simulator loop.
