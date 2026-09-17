from __future__ import annotations

from dataclasses import dataclass

from src.models.schemas import CarState, TriggerState, WeatherState

TRIGGER_TYPES = (
    "TYRE_DEGRADATION",
    "FUEL_LOW",
    "RAIN",
    "GAP_AHEAD",
    "GAP_BEHIND",
    "LAPTIME_DELTA",
)


@dataclass
class TriggerRule:
    name: str
    threshold: float
    rearm_margin: float  # value must fall back below (threshold - rearm_margin) to re-arm
    direction: str = "above"  # "above": fires when value crosses up through threshold
    # "below": fires when value crosses down through threshold (e.g. fuel dropping)


TRIGGER_RULES: dict[str, TriggerRule] = {
    "TYRE_DEGRADATION": TriggerRule("TYRE_DEGRADATION", threshold=0.70, rearm_margin=0.10, direction="above"),
    "FUEL_LOW": TriggerRule("FUEL_LOW", threshold=20.0, rearm_margin=10.0, direction="below"),
    "RAIN": TriggerRule("RAIN", threshold=0.50, rearm_margin=0.15, direction="above"),
    "GAP_AHEAD": TriggerRule("GAP_AHEAD", threshold=1.0, rearm_margin=0.5, direction="below"),
    "GAP_BEHIND": TriggerRule("GAP_BEHIND", threshold=1.0, rearm_margin=0.5, direction="below"),
    "LAPTIME_DELTA": TriggerRule("LAPTIME_DELTA", threshold=2.0, rearm_margin=1.0, direction="above"),
}


def ensure_trigger_states(state: CarState) -> None:
    for name in TRIGGER_TYPES:
        if name not in state.triggers:
            state.triggers[name] = TriggerState()


def _crossed(rule: TriggerRule, value: float, trig: TriggerState) -> bool:
    if rule.direction == "above":
        if trig.armed and value >= rule.threshold:
            return True
        if not trig.armed and value < (rule.threshold - rule.rearm_margin):
            trig.armed = True
        return False
    else:  # "below"
        if trig.armed and value <= rule.threshold:
            return True
        if not trig.armed and value > (rule.threshold + rule.rearm_margin):
            trig.armed = True
        return False


RACE_START_GRACE_TICKS = 15  # ignore gap-based triggers while the start-grid bunching is still settling


def check_triggers(state: CarState, weather: WeatherState, tick: int, baseline_lap_time: float) -> list[str]:
    """Returns list of trigger names that fired this tick (edge-triggered, with hysteresis re-arm)."""
    ensure_trigger_states(state)
    fired: list[str] = []

    values = {
        "TYRE_DEGRADATION": state.tyre_degradation,
        "FUEL_LOW": state.fuel,
        "RAIN": weather.rain_intensity,
        "GAP_AHEAD": state.gap_ahead if state.gap_ahead is not None else float("inf"),
        "GAP_BEHIND": state.gap_behind if state.gap_behind is not None else float("inf"),
        "LAPTIME_DELTA": (state.last_lap_time - baseline_lap_time) if state.last_lap_time else 0.0,
    }

    for name, rule in TRIGGER_RULES.items():
        if name in ("GAP_AHEAD", "GAP_BEHIND") and tick <= RACE_START_GRACE_TICKS:
            continue
        trig = state.triggers[name]
        value = values[name]
        if _crossed(rule, value, trig):
            trig.armed = False
            trig.last_fired_tick = tick
            fired.append(name)

    return fired
