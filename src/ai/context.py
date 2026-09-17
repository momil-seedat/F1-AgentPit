from __future__ import annotations

from dataclasses import dataclass

from src.models.schemas import CarState, WeatherState


@dataclass
class DecisionContext:
    race_id: str
    car_id: str
    trigger_type: str
    trigger_value: float
    trigger_threshold: float
    lap: int
    position: int
    fuel: float
    tyre: str
    tyre_age: int
    tyre_degradation: float
    rain_intensity: float
    gap_ahead: float | None
    gap_behind: float | None
    tokens_remaining: int

    def to_payload(self) -> dict:
        return {
            "race_id": self.race_id,
            "car_id": self.car_id,
            "trigger": {
                "type": self.trigger_type,
                "value": round(self.trigger_value, 3),
                "threshold": self.trigger_threshold,
            },
            "state": {
                "lap": self.lap,
                "position": self.position,
                "fuel": round(self.fuel, 1),
                "tyre": self.tyre,
                "tyre_age": self.tyre_age,
                "tyre_degradation": round(self.tyre_degradation, 3),
                "rain_intensity": round(self.rain_intensity, 3),
                "gap_ahead": self.gap_ahead,
                "gap_behind": self.gap_behind,
            },
            "tokens_remaining": self.tokens_remaining,
        }


def build_decision_context(
    *,
    race_id: str,
    car_state: CarState,
    trigger_type: str,
    trigger_value: float,
    trigger_threshold: float,
    weather: WeatherState,
) -> DecisionContext:
    return DecisionContext(
        race_id=race_id,
        car_id=car_state.car_id,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        trigger_threshold=trigger_threshold,
        lap=car_state.lap,
        position=car_state.position,
        fuel=car_state.fuel,
        tyre=car_state.tyre,
        tyre_age=car_state.tyre_age,
        tyre_degradation=car_state.tyre_degradation,
        rain_intensity=weather.rain_intensity,
        gap_ahead=car_state.gap_ahead,
        gap_behind=car_state.gap_behind,
        tokens_remaining=car_state.ai_tokens_remaining,
    )
