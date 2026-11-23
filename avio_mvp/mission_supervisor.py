"""AVIO mission supervisor: deterministic, advisory-only state machine.

This package never arms, disarms, switches modes or sends PX4 commands.
Simulation integration only. Caller owns monotonic clock and telemetry input.
"""
from dataclasses import dataclass, field
from enum import Enum
import math

VEHICLES = ("uav_1", "uav_2", "uav_3")

class Phase(str, Enum):
    IDLE = "idle"
    PREFLIGHT = "preflight"
    READY = "ready"
    RUNNING = "running"
    HOLD = "hold"
    ABORTED = "aborted"
    COMPLETED = "completed"

@dataclass(frozen=True)
class Observation:
    vehicle: str
    stamp_s: float
    xy_valid: bool
    z_valid: bool
    position: tuple

@dataclass
class Mission:
    """Control-free mission state with conservative fail-closed transitions."""
    waypoint_counts: dict = field(default_factory=lambda: {v: 3 for v in VEHICLES})
    phase: Phase = Phase.IDLE
    latest: dict = field(default_factory=dict)
    completed_waypoints: dict = field(default_factory=lambda: {v: 0 for v in VEHICLES})
    events: list = field(default_factory=list)
    stale_after_s: float = 2.0
    max_duration_s: float = 300.0
    bounds: tuple = (-30.0, -30.0, 30.0, 30.0, 0.0, 25.0)
    started_at: float = None

    def __post_init__(self):
        if set(self.waypoint_counts) != set(VEHICLES) or any(
                type(c) is not int or c <= 0 for c in self.waypoint_counts.values()):
            raise ValueError("exactly three UAVs with positive waypoint counts required")
        if not 0 < self.stale_after_s < self.max_duration_s:
            raise ValueError("invalid time limits")
        xmin, ymin, xmax, ymax, zmin, zmax = self.bounds
        if not (xmin < xmax and ymin < ymax and zmin < zmax):
            raise ValueError("invalid local geofence")
        self.completed_waypoints = {v: 0 for v in VEHICLES}

    def _event(self, now, code, detail=""):
        self.events.append({"time_s": now, "phase": self.phase.value,
                            "event": code, "detail": detail})

    def _set(self, phase, now, reason):
        self.phase = phase
        self._event(now, reason)

    def observe(self, sample):
        if sample.vehicle not in VEHICLES:
            raise ValueError("unknown vehicle")
        if not math.isfinite(sample.stamp_s) or len(sample.position) != 3 or not all(
                isinstance(x, (int, float)) and math.isfinite(x) for x in sample.position):
            raise ValueError("invalid observation")
        previous = self.latest.get(sample.vehicle)
        if previous and sample.stamp_s <= previous.stamp_s:
            raise ValueError("non-monotonic vehicle sample")
        self.latest[sample.vehicle] = sample

    def _health(self, now):
        if not math.isfinite(now):
            return "invalid_clock"
        for name in VEHICLES:
            sample = self.latest.get(name)
            if sample is None:
                return f"{name}:missing"
            age = now - sample.stamp_s
            if not (0 <= age <= self.stale_after_s):
                return f"{name}:stale"
            if not (sample.xy_valid and sample.z_valid):
                return f"{name}:invalid_local_position"
            x, y, z = sample.position
            xmin, ymin, xmax, ymax, zmin, zmax = self.bounds
            if not (xmin <= x <= xmax and ymin <= y <= ymax and zmin <= z <= zmax):
                return f"{name}:outside_local_bounds"
        return None

    def begin_preflight(self, now):
        if self.phase != Phase.IDLE:
            raise ValueError("preflight only from idle")
        self._set(Phase.PREFLIGHT, now, "preflight_requested")

    def check_preflight(self, now):
        if self.phase != Phase.PREFLIGHT:
            raise ValueError("not in preflight")
        error = self._health(now)
        if error:
            self._event(now, "preflight_blocked", error)
            return False
        self._set(Phase.READY, now, "preflight_passed")
        return True

    def start(self, now):
        if self.phase != Phase.READY:
            raise ValueError("start only from ready")
        error = self._health(now)
        if error:
            self._set(Phase.HOLD, now, "start_blocked:" + error)
            return False
        self.started_at = now
        self._set(Phase.RUNNING, now, "simulated_mission_started")
        return True

    def tick(self, now):
        if self.phase not in (Phase.RUNNING, Phase.HOLD):
            return self.phase
        if self.started_at is not None and now - self.started_at > self.max_duration_s:
            self.abort(now, "mission_timeout")
            return self.phase
        error = self._health(now)
        if error:
            if self.phase == Phase.RUNNING:
                self._set(Phase.HOLD, now, "automatic_hold:" + error)
            return self.phase
        # Recovery is intentionally manual; healthy telemetry alone never resumes.
        return self.phase

    def resume(self, now):
        if self.phase != Phase.HOLD:
            raise ValueError("resume only from hold")
        error = self._health(now)
        if error:
            self._event(now, "resume_blocked", error)
            return False
        self._set(Phase.RUNNING, now, "operator_approved_simulated_resume")
        return True

    def waypoint_reached(self, vehicle, now):
        if self.phase != Phase.RUNNING or vehicle not in VEHICLES:
            raise ValueError("waypoint credit requires running mission and valid vehicle")
        self.tick(now)
        if self.phase != Phase.RUNNING:
            return False
        if self.completed_waypoints[vehicle] >= self.waypoint_counts[vehicle]:
            raise ValueError("no remaining waypoints")
        self.completed_waypoints[vehicle] += 1
        self._event(now, "waypoint_recorded", vehicle)
        if all(self.completed_waypoints[v] == self.waypoint_counts[v] for v in VEHICLES):
            self._set(Phase.COMPLETED, now, "all_waypoints_recorded")
        return True

    def abort(self, now, reason="operator_abort"):
        if self.phase in (Phase.ABORTED, Phase.COMPLETED):
            return False
        self._set(Phase.ABORTED, now, reason)
        return True

    def report(self):
        return {"mode": "ADVISORY_ONLY_NO_PX4_COMMANDS", "phase": self.phase.value,
                "completed_waypoints": dict(self.completed_waypoints),
                "total_waypoints": dict(self.waypoint_counts), "events": list(self.events),
                "note": "Geofences are per-vehicle local values, NOT shared/global boundaries."}
