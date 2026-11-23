"""Independent grid planning and mission-quality evaluation prototypes.

These pure-Python utilities are not connected to PX4, ROS 2 or real aircraft.
"""
from collections import deque
from itertools import combinations
from math import dist

def plan_grid(start, goal, blocked, width, height):
    """Shortest four-neighbour path on a static integer grid. None if unreachable."""
    if width <= 0 or height <= 0:
        raise ValueError("positive grid dimensions required")
    inside = lambda p: (isinstance(p, tuple) and len(p) == 2
                         and all(isinstance(v, int) for v in p)
                         and 0 <= p[0] < width and 0 <= p[1] < height)
    obstacles = set(blocked)
    if not inside(start) or not inside(goal):
        raise ValueError("start/goal outside grid")
    if any(not inside(p) for p in obstacles):
        raise ValueError("obstacle outside grid")
    if start in obstacles or goal in obstacles:
        return None
    frontier = deque([start])
    previous = {start: None}
    while frontier:
        cell = frontier.popleft()
        if cell == goal:
            result = []
            while cell is not None:
                result.append(cell)
                cell = previous[cell]
            return list(reversed(result))
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            nxt = (cell[0] + dx, cell[1] + dy)
            if inside(nxt) and nxt not in obstacles and nxt not in previous:
                previous[nxt] = cell
                frontier.append(nxt)
    return None

def path_geofence_valid(path, bounds):
    """Inclusive rectangular static geofence (xmin, ymin, xmax, ymax)."""
    xmin, ymin, xmax, ymax = bounds
    if xmin > xmax or ymin > ymax:
        raise ValueError("invalid geofence")
    return all(xmin <= p[0] <= xmax and ymin <= p[1] <= ymax for p in path)

def trajectory_conflicts(trajectories, minimum_separation):
    """Evaluate synchronous 3D position samples; no control or avoidance is performed."""
    if minimum_separation <= 0:
        raise ValueError("minimum separation must be positive")
    if not trajectories:
        return []
    n = len(next(iter(trajectories.values())))
    if any(len(v) != n for v in trajectories.values()):
        raise ValueError("all sampled trajectories must have equal length")
    conflicts = []
    for i in range(n):
        for a, b in combinations(sorted(trajectories), 2):
            d = dist(trajectories[a][i], trajectories[b][i])
            if d < minimum_separation:
                conflicts.append({"sample": i, "a": a, "b": b, "distance_m": round(d, 5)})
    return conflicts

def evaluate_inspection(mission):
    """Check mission-evidence completeness and target uniqueness; no defect inference."""
    target_ids = [t["id"] for t in mission["targets"]]
    if len(target_ids) != len(set(target_ids)):
        raise ValueError("duplicate targets in mission definition")
    observations = mission["observations"]
    ids = [o["target_id"] for o in observations]
    duplicates = sorted({x for x in ids if ids.count(x) > 1})
    unknown = sorted(set(ids) - set(target_ids))
    missing = sorted(set(target_ids) - set(ids))
    provenance_missing = [o.get("target_id", "?") for o in observations
                          if not all(o.get(k) is not None for k in
                                     ("target_id", "vehicle_id", "time_s", "source", "finding"))]
    return {"coverage_pct": round(100 * (len(set(ids) & set(target_ids)) / len(target_ids)), 2)
            if target_ids else 0.0,
            "duplicate_observations": duplicates, "unknown_targets": unknown,
            "missing_targets": missing, "missing_provenance": provenance_missing,
            "passed": not (duplicates or unknown or missing or provenance_missing)}
