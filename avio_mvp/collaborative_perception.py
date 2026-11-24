"""Synthetic map sharing experiment; not flight software or SLAM."""
import json
import random

SIZE = 20
POSITIONS = ((4, 4), (10, 10), (15, 15))
RADIUS = 5


def observe(truth, position):
    x, y = position
    return {p: value for p, value in truth.items()
            if (p[0] - x)**2 + (p[1] - y)**2 <= RADIUS**2}


def fuse(maps):
    merged = {}
    for local in maps:
        for cell, value in local.items():
            if cell in merged and merged[cell] != value:
                raise ValueError("Conflicting observations require a fusion policy")
            merged[cell] = value
    return merged


def experiment(seed=0):
    rng = random.Random(seed)
    truth = {(x, y): int(rng.random() < 0.2)
             for x in range(SIZE) for y in range(SIZE)}
    local = [observe(truth, p) for p in POSITIONS]
    shared = fuse(local)
    return {
        "seed": seed,
        "provenance": "synthetic perfect observations; fixed shared coordinates",
        "agent_coverage": [len(m) / len(truth) for m in local],
        "shared_coverage": len(shared) / len(truth),
        "duplicate_observations": sum(map(len, local)) - len(shared),
        "shared_accuracy_on_observed_cells": sum(
            truth[p] == v for p, v in shared.items()) / len(shared),
    }


if __name__ == "__main__":
    print(json.dumps(experiment(), indent=2))
