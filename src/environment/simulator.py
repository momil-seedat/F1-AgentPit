from __future__ import annotations

import random
from pathlib import Path

from src.ai.client import AgentClient, BudgetExhaustedClient
from src.ai.context import build_decision_context
from src.environment.physics import step_car_physics
from src.environment.standings import update_positions_and_gaps
from src.environment.triggers import check_triggers
from src.environment.weather import step_weather
from src.logging.decisions import DecisionLogWriter
from src.logging.telemetry import TelemetryWriter
from src.models.loader import load_cars, load_cars_initial_state, load_drivers, load_tyres, load_track
from src.models.schemas import CarState, RaceConfig

PIT_TYRE_CHOICE = "medium"  # MVP: AI always fits mediums on a pit stop
BASELINE_LAP_TIME_S = 95.0

# Real AI calls have an unknown cost until they complete and can't be split, so we
# stop issuing new calls once the remaining allowance can't safely absorb one more
# worst-case call. This is what makes the ai_token_budget + ai_token_overage cap
# a real hard cap instead of a check that a single call can blow past.
MAX_CALL_TOKEN_COST = 350


class Simulator:
    def __init__(self, config: RaceConfig, ai_client: AgentClient, run_dir: str | Path):
        self.config = config
        self.ai_client = ai_client
        self.budget_exhausted_client = BudgetExhaustedClient()
        self.rng = random.Random(config.seed)

        self.track = load_track(config.track_id)
        self.tyres = load_tyres()
        self.drivers = load_drivers()
        self.cars = load_cars()
        initial_states = load_cars_initial_state()

        self.weather = config.initial_weather

        self.states: dict[str, CarState] = {}
        for car_id in config.cars:
            init = initial_states[car_id]
            self.states[car_id] = CarState(
                car_id=car_id,
                position=init["position"],
                fuel=init["fuel"],
                tyre=init["tyre"],
                tyre_age=init["tyre_age"],
                speed_kmh=init["speed"],
                ai_tokens_remaining=config.ai_token_budget,
            )

        run_dir = Path(run_dir)
        self.telemetry = TelemetryWriter(run_dir / "telemetry.jsonl")
        self.decisions = DecisionLogWriter(run_dir / "decisions.jsonl")

        self.tick = 0

    def run(self) -> dict:
        while not self._race_finished():
            self._step()
        return self._final_results()

    def _race_finished(self) -> bool:
        return all(s.finished or s.retired for s in self.states.values())

    def _step(self) -> None:
        self.tick += 1
        self.weather = step_weather(self.weather, self.rng)

        for car_id in self.config.cars:
            state = self.states[car_id]
            if state.finished or state.retired:
                continue

            car = self.cars[car_id]
            driver = self.drivers[car.driver_id]

            step_car_physics(
                state=state,
                car=car,
                driver=driver,
                track=self.track,
                tyres=self.tyres,
                weather=self.weather,
                tick_seconds=self.config.tick_seconds,
                rng=self.rng,
            )

            if state.lap > self.config.total_laps:
                state.finished = True

        update_positions_and_gaps(self.states)

        for car_id in self.config.cars:
            state = self.states[car_id]
            if state.finished or state.retired:
                continue
            self._check_and_run_ai(state)
            self.telemetry.write(self.config.race_id, self.tick, state, self.weather)

    def _check_and_run_ai(self, state: CarState) -> None:
        fired = check_triggers(state, self.weather, self.tick, BASELINE_LAP_TIME_S)
        if not fired:
            return

        trigger_type = fired[0]  # MVP: handle the first fired trigger per tick
        from src.environment.triggers import TRIGGER_RULES

        rule = TRIGGER_RULES[trigger_type]
        trigger_value = {
            "TYRE_DEGRADATION": state.tyre_degradation,
            "FUEL_LOW": state.fuel,
            "RAIN": self.weather.rain_intensity,
            "GAP_AHEAD": state.gap_ahead or 0.0,
            "GAP_BEHIND": state.gap_behind or 0.0,
            "LAPTIME_DELTA": (state.last_lap_time - BASELINE_LAP_TIME_S) if state.last_lap_time else 0.0,
        }[trigger_type]

        context = build_decision_context(
            race_id=self.config.race_id,
            car_state=state,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            trigger_threshold=rule.threshold,
            weather=self.weather,
        )

        token_cap = self.config.ai_token_budget + self.config.ai_token_overage
        client = (
            self.ai_client
            if state.ai_tokens_used + MAX_CALL_TOKEN_COST <= token_cap
            else self.budget_exhausted_client
        )
        result = client.decide(context)

        state.ai_tokens_used = min(token_cap, state.ai_tokens_used + result.tokens_used)
        state.ai_tokens_remaining = max(0, self.config.ai_token_budget - state.ai_tokens_used)
        state.ai_decisions_count += 1

        self._apply_decision(state, result.decision)
        self.decisions.write(self.tick, context, result, state)

    def _apply_decision(self, state: CarState, decision: str) -> None:
        if decision == "PIT":
            state.total_time += self.cars[state.car_id].specs.pit_time
            state.tyre = PIT_TYRE_CHOICE
            state.tyre_age = 0
            state.tyre_degradation = 0.0
            state.pit_stops += 1
        # STAY_OUT / PUSH / NORMAL: no direct state mutation in MVP;
        # PUSH's aggression is expected to be reflected via driver risk_tolerance in later phases.

    def _final_results(self) -> dict:
        self.telemetry.close()
        self.decisions.close()

        ranked = sorted(self.states.values(), key=lambda s: (not s.finished, s.total_time))
        results = []
        for idx, state in enumerate(ranked):
            car = self.cars[state.car_id]
            results.append(
                {
                    "position": idx + 1,
                    "car_id": state.car_id,
                    "driver_id": car.driver_id,
                    "total_time": round(state.total_time, 2),
                    "pit_stops": state.pit_stops,
                    "ai_tokens_used": state.ai_tokens_used,
                    "ai_decisions": state.ai_decisions_count,
                }
            )

        return {
            "race_id": self.config.race_id,
            "winner": results[0]["car_id"] if results else None,
            "results": results,
        }
