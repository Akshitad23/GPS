"""Generate truth first; corrupt coordinates only afterwards."""
import numpy as np


def journey(roads, rng, dt=1., speed=8., variant=0):
    routes = [
        ["m0+", "m1+", "m2+"],
        ["s0+", "s1+", "s2+"],
        ["m0+", "m1+", "c2+", "s2+"],
        ["s2-", "s1-", "s0-"],
        ["m2-", "m1-", "m0-"],
        ["s0+", "s1+", "c2-", "m2+"],
    ]
    ids = routes[variant % len(routes)]
    edges = [roads.edges[e] for e in ids]
    if any(a.v != b.u for a, b in zip(edges, edges[1:])):
        raise ValueError("Noncontiguous truth route")
    lengths = np.array([roads.length(e) for e in edges])
    cumulative = np.cumsum(lengths)
    # Random start phase avoids points lying exactly on junctions.
    distances = np.arange(rng.uniform(.1, min(speed*dt, 5.)), cumulative[-1], speed*dt)
    times = np.arange(len(distances), dtype=float)*dt
    coords, segments, directed = [], [], []
    for distance in distances:
        index = int(np.searchsorted(cumulative, distance, side="right"))
        before = cumulative[index-1] if index else 0.
        edge = edges[index]
        frac = (distance-before)/lengths[index]
        coords.append(roads.nodes[edge.u] + frac*(roads.nodes[edge.v]-roads.nodes[edge.u]))
        segments.append(edge.segment)
        directed.append(edge.id)
    return {"time": times, "xy": np.array(coords),
            "segment": np.array(segments), "edge": np.array(directed)}


def corrupt(truth, rng, kind="independent", sigma=8., burst_offset=20.,
            burst_points=10, gap_points=6, burst_angle_degrees=90., burst_start_fraction=.5):
    n = len(truth["time"])
    noise = rng.normal(0., sigma, (n, 2))
    burst = np.zeros(n, dtype=bool)
    keep = np.ones(n, dtype=bool)
    if kind in ("burst", "matched_iid"):
        size = min(burst_points, n)
        start = int((n-size)*burst_start_fraction)
        burst[start:start+size] = True
        angle = np.deg2rad(burst_angle_degrees)
        direction = np.array([np.cos(angle),np.sin(angle)])
        direction[np.abs(direction)<1e-12] = 0.
        noise[burst] += burst_offset*direction
        if kind == "matched_iid":
            # Exact empirical RMSE match to burst condition with the same noise seed.
            target = np.sqrt(np.mean(np.sum(noise**2, axis=1)))
            noise = rng.normal(0., 1., (n, 2))
            noise *= target / np.sqrt(np.mean(np.sum(noise**2, axis=1)))
            burst[:] = False
    elif kind == "gap":
        size = min(gap_points, max(0, n-2))
        start = max(1, (n-size)//2)
        keep[start:start+size] = False
    elif kind != "independent":
        raise ValueError("Unknown noise kind")
    return {
        "time": truth["time"][keep],
        "xy": (truth["xy"]+noise)[keep],
        "truth_xy": truth["xy"][keep],
        "segment": truth["segment"][keep],
        "edge": truth["edge"][keep],
        "burst": burst[keep],
    }
