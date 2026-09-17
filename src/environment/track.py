from __future__ import annotations

from src.models.schemas import Track


def segment_speed_factor(track: Track, distance_in_lap_m: float) -> float:
    """Given distance traveled within the current lap, return the speed_factor
    of the segment the car is currently in."""
    cursor = 0.0
    for seg in track.segments:
        cursor += seg.length_m
        if distance_in_lap_m < cursor:
            return seg.speed_factor
    return track.segments[-1].speed_factor
