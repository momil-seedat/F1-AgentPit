from __future__ import annotations

import random

from src.models.schemas import WeatherState


def rain_intensity_to_grip(rain_intensity: float) -> float:
    """0.0 -> dry (grip 1.0), 1.0 -> full heavy rain (grip ~0.55)."""
    return max(0.55, 1.0 - (rain_intensity * 0.45))


def rain_intensity_to_condition(rain_intensity: float) -> str:
    if rain_intensity <= 0.0:
        return "dry"
    if rain_intensity < 0.35:
        return "light"
    if rain_intensity < 0.65:
        return "medium"
    return "heavy"


def step_weather(weather: WeatherState, rng: random.Random, drift_std: float = 0.01) -> WeatherState:
    """Random-walk the rain intensity slightly each tick, clamped to [0, 1]."""
    delta = rng.gauss(0, drift_std)
    new_rain = min(1.0, max(0.0, weather.rain_intensity + delta))
    return WeatherState(
        condition=rain_intensity_to_condition(new_rain),
        rain_intensity=round(new_rain, 4),
        track_grip=round(rain_intensity_to_grip(new_rain), 4),
    )
