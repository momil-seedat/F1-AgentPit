from __future__ import annotations

import json
from pathlib import Path

from src.models.schemas import (
    CarDefinition,
    CarSpecs,
    Driver,
    RaceConfig,
    Track,
    TrackSegment,
    TyreCompound,
    WeatherState,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_race_config(path: str | Path) -> RaceConfig:
    raw = json.loads(Path(path).read_text())
    weather = WeatherState(**raw["initial_weather"])
    return RaceConfig(
        race_id=raw["race_id"],
        environment_id=raw["environment_id"],
        track_id=raw["track_id"],
        total_laps=raw["total_laps"],
        tick_seconds=raw["tick_seconds"],
        cars=raw["cars"],
        ai_token_budget=raw["ai_token_budget"],
        seed=raw["seed"],
        ai_token_overage=raw.get("ai_token_overage", 100),
        initial_weather=weather,
    )


def load_track(track_id: str, data_dir: Path = DATA_DIR) -> Track:
    raw = json.loads((data_dir / "track.json").read_text())
    if raw["track_id"] != track_id:
        raise ValueError(f"Track file does not match requested track_id={track_id}")
    segments = [TrackSegment(**s) for s in raw["segments"]]
    return Track(track_id=raw["track_id"], lap_distance_m=raw["lap_distance_m"], segments=segments)


def load_tyres(data_dir: Path = DATA_DIR) -> dict[str, TyreCompound]:
    raw = json.loads((data_dir / "tyres.json").read_text())
    return {name: TyreCompound(**vals) for name, vals in raw.items()}


def load_drivers(data_dir: Path = DATA_DIR) -> dict[str, Driver]:
    raw = json.loads((data_dir / "drivers.json").read_text())
    return {d["driver_id"]: Driver(**d) for d in raw}


def load_cars(data_dir: Path = DATA_DIR) -> dict[str, CarDefinition]:
    raw = json.loads((data_dir / "cars.json").read_text())
    cars = {}
    for c in raw:
        specs = CarSpecs(**c["specs"])
        cars[c["car_id"]] = CarDefinition(
            car_id=c["car_id"], team=c["team"], driver_id=c["driver_id"], specs=specs
        )
    return cars


def load_cars_initial_state(data_dir: Path = DATA_DIR) -> dict[str, dict]:
    """Returns raw initial_state dicts keyed by car_id (fuel, tyre, tyre_age, position, speed)."""
    raw = json.loads((data_dir / "cars.json").read_text())
    return {c["car_id"]: c["initial_state"] for c in raw}
