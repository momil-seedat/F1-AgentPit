from __future__ import annotations

import json
from abc import ABC, abstractmethod

from src.ai.context import DecisionContext
from src.models.schemas import AIDecisionResult

VALID_DECISIONS = {"PIT", "STAY_OUT", "PUSH", "NORMAL"}

SYSTEM_PROMPT = """You are a Formula 1 race strategist AI. You are given the current \
state of one car and the reason a strategic decision is needed right now (the trigger). \
Choose exactly one action and respond with ONLY a JSON object, no other text:

{"decision": "PIT" | "STAY_OUT" | "PUSH", "reason": "<one short sentence>"}

Guidance:
- PIT: come into the pits this lap to change tyres (costs significant time).
- STAY_OUT: continue on current tyres/strategy, no change.
- PUSH: continue but drive more aggressively to attack a rival or defend position.

Consider tyre degradation, fuel, rain intensity, and gaps to rivals ahead/behind."""


class AgentClient(ABC):
    """Interface for the Phase 1 strategy agent. One decide() call = one AI decision."""

    @abstractmethod
    def decide(self, context: DecisionContext) -> AIDecisionResult:
        ...


class RuleBasedMockClient(AgentClient):
    """Deterministic stand-in for the AI, used for testing the simulator without
    needing Ollama running. No network calls, fixed token cost per decision."""

    FIXED_TOKEN_COST = 50

    def decide(self, context: DecisionContext) -> AIDecisionResult:
        reasons = []
        decision = "STAY_OUT"

        if context.trigger_type == "TYRE_DEGRADATION" and context.tyre_degradation >= 0.70:
            decision = "PIT"
            reasons.append("tyre degradation critical")
        elif context.trigger_type == "RAIN" and context.rain_intensity >= 0.50:
            decision = "PIT"
            reasons.append("rain intensity rising, switch tyres")
        elif context.trigger_type == "FUEL_LOW" and context.fuel <= 20:
            decision = "STAY_OUT"
            reasons.append("fuel low but no fuel-stop strategy in MVP")
        elif context.trigger_type == "GAP_AHEAD" and (context.gap_ahead or 99) <= 1.0:
            decision = "PUSH"
            reasons.append("close gap to car ahead, attempt overtake")
        elif context.trigger_type == "GAP_BEHIND" and (context.gap_behind or 99) <= 1.0:
            decision = "PUSH"
            reasons.append("defend position from car behind")

        reason = "; ".join(reasons) if reasons else "no strategic change required"
        return AIDecisionResult(decision=decision, reason=reason, tokens_used=self.FIXED_TOKEN_COST)


class OllamaClient(AgentClient):
    """Calls a local Ollama server for strategy decisions."""

    def __init__(self, model: str = "qwen2.5:7b", host: str = "http://localhost:11434", timeout: float = 90.0):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def decide(self, context: DecisionContext) -> AIDecisionResult:
        import urllib.request

        payload = context.to_payload()
        body = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "prompt": json.dumps(payload),
            "stream": False,
            "format": "json",
        }
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        response_text = raw.get("response", "{}")
        parsed = json.loads(response_text)
        decision = parsed.get("decision", "STAY_OUT")
        if decision not in VALID_DECISIONS:
            decision = "STAY_OUT"
        reason = parsed.get("reason", "")

        prompt_tokens = raw.get("prompt_eval_count", 0)
        completion_tokens = raw.get("eval_count", 0)
        tokens_used = prompt_tokens + completion_tokens

        return AIDecisionResult(decision=decision, reason=reason, tokens_used=tokens_used)


class BudgetExhaustedClient(AgentClient):
    """Fallback policy applied when a car has run out of AI token budget.
    No AI call is made; a conservative default decision is returned at zero cost."""

    def decide(self, context: DecisionContext) -> AIDecisionResult:
        decision = "PIT" if context.tyre_degradation >= 0.95 else "STAY_OUT"
        return AIDecisionResult(
            decision=decision,
            reason="AI token budget exhausted; applying default policy",
            tokens_used=0,
        )
