"""Causal GPS replay and prompt evaluation at the Kudlu Gate junction."""

from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path

import numpy as np

from .inference import NoPathError
from .pipeline import Config, match
from .roads import Edge, RoadMap


EXTRACT = Path(__file__).with_name("demo_static") / "kudlu_gate.json"
SCENARIOS = {"clean": ("stay", False), "drift-stay": ("stay", True), "drift-exit": ("exit", True)}
WINDOW = 12
MIN_CONFIDENCE = 0.85
PROMPT_NEAR, PROMPT_FAR = 20, 100
SPEED = 10
SEED = 42
BURST_SECONDS = 8
MATCH_CONFIG = Config(model="robust", assumed_sigma=4., candidate_radius=35.)
ROAD_NAMES = {"main": "Hosur Road · main road", "exit": "Exit connector", "service": "Service road"}


def load_junction():
    data = json.loads(EXTRACT.read_text(encoding="utf8"))
    fork = data["fork_node"]
    lat0, lon0 = np.radians(data["nodes"][fork])
    nodes = {}
    for node, coords in data["nodes"].items():
        lat, lon = np.radians(coords)
        nodes[node] = 6_371_008.8 * np.array([(lon - lon0) * np.cos(lat0), lat - lat0])
    groups, edges, ways = {}, [], {}
    for way in data["ways"]:
        group = way["group"]
        ways[group] = []
        direction = way["tags"].get("oneway")
        for index, (u, v) in enumerate(zip(way["nodes"], way["nodes"][1:])):
            segment = f"{way['id']}:{index}"
            groups[segment] = group
            if direction != "-1":
                edges.append(Edge(segment + "+", segment, u, v))
                ways[group].append(edges[-1])
            if direction != "yes":
                edges.append(Edge(segment + "-", segment, v, u))
                if direction == "-1":
                    ways[group].insert(0, edges[-1])

    roads = RoadMap(nodes, edges)
    approach = next(edge for edge in ways["main"] if edge.v == fork)
    onward = next(edge for edge in ways["main"] if edge.u == fork)
    connector = next(edge for edge in edges if groups[edge.segment] == "exit" and edge.u == fork)
    service = ways["service"]
    first_service = next(i for i, edge in enumerate(service) if edge.u == connector.v)
    paths = {"stay": [approach, onward], "exit": [approach, connector, *service[first_service:]]}
    for path in paths.values():
        if any(a.v != b.u for a, b in zip(path, path[1:])):
            raise ValueError("The demo route is disconnected")
    return data["name"], roads, groups, fork, paths


def point_on_path(roads, path, station):
    for edge in path:
        length = roads.length(edge)
        if station < length:
            u, v = roads.nodes[edge.u], roads.nodes[edge.v]
            return u + (v - u) * station / length, edge.segment
        station -= length
    raise ValueError("Replay extends beyond the mapped route")


def simulate(roads, groups, path, burst_enabled):
    approach_length = roads.length(path[0])
    seconds_from_fork = np.arange(-13, 13)
    stations = approach_length + SPEED * seconds_from_fork + 1.
    truth, segments = zip(*(point_on_path(roads, path, station) for station in stations))
    truth = np.asarray(truth)
    gps = truth + np.random.default_rng(SEED).normal(0., 1.5, truth.shape)
    burst = burst_enabled & (seconds_from_fork >= -BURST_SECONDS) & (seconds_from_fork < 0)
    if burst_enabled:
        for i in np.flatnonzero(burst):
            service = min((c for c in roads.candidates(truth[i], MATCH_CONFIG.candidate_radius)
                           if groups[c.edge.segment] == "service"), key=lambda c: c.residual)
            gps[i] += service.point - truth[i]
    return np.arange(len(stations)), gps, truth, segments, burst, stations - approach_length


def estimate_frames(roads, groups, times, observations):
    """Estimate only the newest sample from each available observation window."""
    frames = []
    for index, point in enumerate(observations):
        start = max(0, index + 1 - WINDOW)
        candidates = roads.candidates(point, MATCH_CONFIG.candidate_radius)
        nearest = min(candidates, key=lambda c: c.residual, default=None)
        frame = {"gps": point.tolist(), "t": int(times[index]),
                 "nearest_road": groups[nearest.edge.segment] if nearest else None,
                 "nearest_xy": nearest.point.tolist() if nearest else None,
                 "road": None, "estimated_xy": None, "confidence": None, "main_confidence": 0.}
        try:
            result = match(roads, times[start:index + 1], observations[start:index + 1], MATCH_CONFIG)
        except NoPathError:
            frames.append(frame)
            continue
        latest = result["candidates"][-1]
        posterior = result["posterior"][-1]
        masses = defaultdict(float)
        for candidate, probability in zip(latest, posterior):
            masses[groups[candidate.edge.segment]] += float(probability)
        road = max(masses, key=masses.get)
        best = max((i for i, candidate in enumerate(latest)
                    if groups[candidate.edge.segment] == road), key=posterior.__getitem__)
        frame.update(road=road, estimated_xy=latest[best].point.tolist(),
                     confidence=min(1., masses[road]), main_confidence=min(1., masses["main"]))
        frames.append(frame)
    return frames


def add_prompts(frames, roads, approach, maneuver):
    fork = roads.nodes[approach.v]
    direction = (fork - roads.nodes[approach.u]) / roads.length(approach)
    streak = 0
    prompted = False
    passed = False
    output = []
    for index, frame in enumerate(frames):
        trusted = frame["road"] == "main" and frame["main_confidence"] >= MIN_CONFIDENCE
        streak = streak + 1 if trusted else 0
        # A GPS projection still locates the approach window when the match
        # favors the service road or returns no path.
        position = frame["estimated_xy"] if trusted else frame["gps"]
        distance = float(np.dot(fork - position, direction))
        passed = passed or distance <= 0
        if passed:
            status = "passed"
        elif PROMPT_NEAR <= distance <= PROMPT_FAR:
            status = maneuver if streak >= 2 and index >= 2 else "uncertain"
        else:
            status = "waiting"
        prompt_started = status == maneuver and not prompted
        prompted |= prompt_started
        output.append({**frame, "status": status, "prompt_started": prompt_started})
    return output


@lru_cache(maxsize=len(SCENARIOS))
def junction_replay(scenario="drift-stay"):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown junction scenario")
    maneuver, burst_enabled = SCENARIOS[scenario]
    name, roads, groups, fork, paths = load_junction()
    path = paths[maneuver]
    times, gps, truth, segments, burst, progress = simulate(roads, groups, path, burst_enabled)
    frames = add_prompts(estimate_frames(roads, groups, times, gps), roads, path[0], maneuver)
    for frame, xy, segment, is_burst in zip(frames, truth, segments, burst):
        frame.update(truth_xy=xy.tolist(), truth_road=groups[segment], burst=bool(is_burst))

    near = [f for f, metres in zip(frames, progress) if abs(metres) <= PROMPT_FAR]
    lead = next((float(-metres / SPEED) for frame, metres in zip(frames, progress)
                 if frame["status"] == maneuver and PROMPT_NEAR <= -metres <= PROMPT_FAR), None)
    segments = [{"road": groups[e.segment], "a": roads.nodes[e.u].tolist(), "b": roads.nodes[e.v].tolist()}
                for e in roads.edges.values() if e.id.endswith("+")]
    # Draw just the planned portion of each path, over the full road context.
    remaining = roads.length(path[0]) + progress[-1]
    planned_path = [truth[0].tolist()]
    for edge in path:
        length = roads.length(edge)
        if remaining <= length:
            break
        planned_path.append(roads.nodes[edge.v].tolist())
        remaining -= length
    planned_path.append(truth[-1].tolist())
    return {
        "name": name, "scenario": scenario, "maneuver": maneuver, "road_names": ROAD_NAMES,
        "segments": segments, "fork": roads.nodes[fork].tolist(), "planned_path": planned_path,
        "threshold": MIN_CONFIDENCE, "frames": frames,
        "summary": {
            "near_fork_samples": len(near),
            "wrong_estimates": sum(f["road"] is not None and f["road"] != f["truth_road"] for f in near),
            "unmatched": sum(f["road"] is None for f in near),
            "nearest_wrong": sum(f["nearest_road"] is not None and f["nearest_road"] != f["truth_road"] for f in near),
            "nearest_unmatched": sum(f["nearest_road"] is None for f in near),
            "uncertain_seconds": sum(f["status"] == "uncertain" for f in frames),
            "prompt_lead_seconds": lead,
        },
    }
