from __future__ import annotations

import json
from pathlib import Path

from src.models.schemas import CarState, WeatherState


class TelemetryWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w")

    def write(self, race_id: str, timestamp: int, state: CarState, weather: WeatherState) -> None:
        record = {
            "race_id": race_id,
            "timestamp": timestamp,
            "car_id": state.car_id,
            "race": {
                "lap": state.lap,
                "position": state.position,
                "distance_m": round(state.total_distance_m, 1),
            },
            "performance": {
                "speed_kmh": round(state.speed_kmh, 1),
                "lap_time": round(state.lap_time, 2),
                "gap_ahead": state.gap_ahead,
                "gap_behind": state.gap_behind,
            },
            "fuel": {"remaining": round(state.fuel, 2)},
            "tyres": {
                "type": state.tyre,
                "age": state.tyre_age,
                "degradation": round(state.tyre_degradation, 3),
            },
            "weather": {
                "rain_intensity": weather.rain_intensity,
                "track_grip": weather.track_grip,
            },
            "ai": {"tokens_remaining": state.ai_tokens_remaining},
        }
        self._fh.write(json.dumps(record) + "\n")

    def close(self) -> None:
        self._fh.close()
