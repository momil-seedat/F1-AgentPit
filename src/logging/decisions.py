from __future__ import annotations

import json
from pathlib import Path

from src.ai.context import DecisionContext
from src.models.schemas import AIDecisionResult, CarState


class DecisionLogWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w")

    def write(
        self,
        timestamp: int,
        context: DecisionContext,
        result: AIDecisionResult,
        state_after: CarState,
    ) -> None:
        record = {
            "timestamp": timestamp,
            "car_id": context.car_id,
            "trigger": context.trigger_type,
            "state_before_decision": {
                "lap": context.lap,
                "position": context.position,
                "rain": context.rain_intensity,
                "tyre": context.tyre,
                "tyre_degradation": round(context.tyre_degradation, 3),
                "fuel": round(context.fuel, 1),
                "gap_ahead": context.gap_ahead,
                "gap_behind": context.gap_behind,
            },
            "ai_tokens_available": context.tokens_remaining,
            "ai_tokens_used": result.tokens_used,
            "decision": result.decision,
            "reason": result.reason,
            "position_after_decision": state_after.position,
        }
        self._fh.write(json.dumps(record) + "\n")

    def close(self) -> None:
        self._fh.close()
