from __future__ import annotations

import random

from src.environment.track import segment_speed_factor
from src.models.schemas import CarDefinition, CarState, Driver, Track, TyreCompound, WeatherState

BASE_TRACK_SPEED_KMH = 320.0
MAX_ACCEL_KMH_PER_TICK = 25.0
MAX_DECEL_KMH_PER_TICK = 40.0

FUEL_BASE_CONSUMPTION_PER_TICK = 0.028
TYRE_DEGRADATION_BASE_PER_TICK = 0.0018


def fuel_factor(fuel: float) -> float:
    """Low fuel makes the car lighter -> a small speed benefit late in the race.
    Very low fuel (<5) also risks a penalty, but MVP keeps this simple."""
    return 0.97 + (100.0 - fuel) / 100.0 * 0.03


def tyre_grip_factor(tyre_compound: TyreCompound, tyre_degradation: float) -> float:
    """Degradation erodes grip: at 1.0 degradation, effective grip drops ~35%."""
    wear_penalty = tyre_degradation * 0.35
    return max(0.5, tyre_compound.grip - wear_penalty)


def calculate_target_speed(
    *,
    track: Track,
    distance_in_lap_m: float,
    car: CarDefinition,
    driver: Driver,
    tyre_compound: TyreCompound,
    tyre_degradation: float,
    weather: WeatherState,
    fuel: float,
) -> float:
    seg_factor = segment_speed_factor(track, distance_in_lap_m)
    tyre_factor = tyre_grip_factor(tyre_compound, tyre_degradation)
    weather_factor = weather.track_grip
    f_factor = fuel_factor(fuel)

    target = (
        BASE_TRACK_SPEED_KMH
        * seg_factor
        * car.specs.pace
        * driver.skill
        * tyre_factor
        * weather_factor
        * f_factor
    )
    return max(0.0, target)


def move_towards(current: float, target: float, max_accel: float, max_decel: float) -> float:
    if target > current:
        return min(target, current + max_accel)
    return max(target, current - max_decel)


def apply_consistency_noise(speed: float, consistency: float, rng: random.Random) -> float:
    """Lower consistency -> more random variation in speed (std dev scales inversely)."""
    std = (1.0 - consistency) * 6.0
    noise = rng.gauss(0, std)
    return max(0.0, speed + noise)


def calculate_fuel_consumption(car: CarDefinition, speed_kmh: float, tick_seconds: int) -> float:
    speed_factor = speed_kmh / BASE_TRACK_SPEED_KMH if BASE_TRACK_SPEED_KMH else 0
    consumption = FUEL_BASE_CONSUMPTION_PER_TICK * speed_factor / car.specs.fuel_efficiency
    return consumption * tick_seconds


def calculate_tyre_degradation_increment(
    car: CarDefinition, tyre_compound: TyreCompound, speed_kmh: float, tick_seconds: int
) -> float:
    speed_factor = speed_kmh / BASE_TRACK_SPEED_KMH if BASE_TRACK_SPEED_KMH else 0
    increment = (
        TYRE_DEGRADATION_BASE_PER_TICK
        * tyre_compound.degradation
        * speed_factor
        / car.specs.tyre_efficiency
    )
    return increment * tick_seconds


def step_car_physics(
    *,
    state: CarState,
    car: CarDefinition,
    driver: Driver,
    track: Track,
    tyres: dict[str, TyreCompound],
    weather: WeatherState,
    tick_seconds: int,
    rng: random.Random,
) -> None:
    """Mutates `state` in place: fuel, tyre degradation, speed, distance, lap, lap_time.
    Position/gaps are computed separately across all cars after this runs for each car."""
    if state.retired or state.finished:
        return

    tyre_compound = tyres[state.tyre]
    distance_in_lap_m = state.distance_m

    target_speed = calculate_target_speed(
        track=track,
        distance_in_lap_m=distance_in_lap_m,
        car=car,
        driver=driver,
        tyre_compound=tyre_compound,
        tyre_degradation=state.tyre_degradation,
        weather=weather,
        fuel=state.fuel,
    )

    new_speed = move_towards(state.speed_kmh, target_speed, MAX_ACCEL_KMH_PER_TICK, MAX_DECEL_KMH_PER_TICK)
    new_speed = apply_consistency_noise(new_speed, driver.consistency, rng)
    state.speed_kmh = new_speed

    distance_this_tick_m = (new_speed * 1000.0 / 3600.0) * tick_seconds

    fuel_used = calculate_fuel_consumption(car, new_speed, tick_seconds)
    state.fuel = max(0.0, state.fuel - fuel_used)

    tyre_inc = calculate_tyre_degradation_increment(car, tyre_compound, new_speed, tick_seconds)
    state.tyre_degradation = min(1.0, state.tyre_degradation + tyre_inc)

    state.distance_m += distance_this_tick_m
    state.total_distance_m += distance_this_tick_m
    state.lap_time += tick_seconds

    if state.distance_m >= track.lap_distance_m:
        state.distance_m -= track.lap_distance_m
        state.last_lap_time = state.lap_time
        state.lap_time = 0.0
        state.lap += 1
        state.tyre_age += 1

    state.total_time += tick_seconds
