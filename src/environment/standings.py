from __future__ import annotations

from src.models.schemas import CarState

SPEED_TO_TIME_GAP_DIVISOR_KMH = 300.0  # rough conversion of distance gap -> seconds gap


def update_positions_and_gaps(states: dict[str, CarState]) -> None:
    """Ranks cars by total distance traveled (lap progress), sets position,
    and computes gap_ahead/gap_behind in approximate seconds."""
    active = [s for s in states.values() if not s.retired]
    ranked = sorted(active, key=lambda s: s.total_distance_m, reverse=True)

    for idx, state in enumerate(ranked):
        state.position = idx + 1

    for idx, state in enumerate(ranked):
        if idx == 0:
            state.gap_ahead = None
        else:
            ahead = ranked[idx - 1]
            dist_gap_m = ahead.total_distance_m - state.total_distance_m
            avg_speed = max(1.0, (ahead.speed_kmh + state.speed_kmh) / 2.0)
            state.gap_ahead = round((dist_gap_m / 1000.0) / avg_speed * 3600.0, 2)

        if idx == len(ranked) - 1:
            state.gap_behind = None
        else:
            behind = ranked[idx + 1]
            dist_gap_m = state.total_distance_m - behind.total_distance_m
            avg_speed = max(1.0, (behind.speed_kmh + state.speed_kmh) / 2.0)
            state.gap_behind = round((dist_gap_m / 1000.0) / avg_speed * 3600.0, 2)
