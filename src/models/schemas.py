from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TyreType = Literal["soft", "medium", "hard"]
Decision = Literal["PIT", "STAY_OUT", "PUSH", "NORMAL"]


@dataclass
class RaceConfig:
    race_id: str
    environment_id: str
    track_id: str
    total_laps: int
    tick_seconds: int
    cars: list[str]
    ai_token_budget: int
    seed: int
    initial_weather: "WeatherState"
    ai_token_overage: int = 100


@dataclass
class Driver:
    driver_id: str
    name: str
    skill: float
    consistency: float
    risk_tolerance: float = 0.5


@dataclass
class CarSpecs:
    pace: float
    tyre_efficiency: float
    fuel_efficiency: float
    reliability: float
    pit_time: float


@dataclass
class CarDefinition:
    car_id: str
    team: str
    driver_id: str
    specs: CarSpecs


@dataclass
class TyreCompound:
    grip: float
    degradation: float


@dataclass
class TrackSegment:
    segment_id: int
    length_m: float
    speed_factor: float


@dataclass
class Track:
    track_id: str
    lap_distance_m: float
    segments: list[TrackSegment]


@dataclass
class WeatherState:
    condition: str
    rain_intensity: float
    track_grip: float


@dataclass
class TriggerState:
    armed: bool = True
    last_fired_tick: int | None = None


@dataclass
class CarState:
    """Mutable per-tick state for a single car. Recomputed/updated every tick."""

    car_id: str
    lap: int = 1
    position: int = 1
    distance_m: float = 0.0
    total_distance_m: float = 0.0
    speed_kmh: float = 0.0
    fuel: float = 100.0
    tyre: TyreType = "medium"
    tyre_age: int = 0
    tyre_degradation: float = 0.0
    lap_time: float = 0.0
    lap_start_tick: int = 0
    last_lap_time: float | None = None
    gap_ahead: float | None = None
    gap_behind: float | None = None
    pit_stops: int = 0
    retired: bool = False
    finished: bool = False
    total_time: float = 0.0

    ai_tokens_remaining: int = 700
    ai_tokens_used: int = 0
    ai_decisions_count: int = 0

    triggers: dict[str, TriggerState] = field(default_factory=dict)


@dataclass
class AIDecisionResult:
    decision: Decision
    reason: str
    tokens_used: int
