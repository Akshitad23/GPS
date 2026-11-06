"""Directed straight-segment roads and exact partial-edge routing."""
from dataclasses import dataclass
import heapq
import math
import numpy as np


@dataclass(frozen=True)
class Edge:
    id: str
    segment: str
    u: str
    v: str


@dataclass
class Candidate:
    edge: Edge
    offset: float
    point: np.ndarray
    residual: float


class RoadMap:
    def __init__(self, nodes, edges):
        self.nodes = {k: np.asarray(v, dtype=float) for k, v in nodes.items()}
        self.edges = {e.id: e for e in edges}
        self.adj = {k: [] for k in nodes}
        for e in edges:
            self.adj[e.u].append((e.v, self.length(e)))
        self._cache = {}

    def length(self, edge):
        return float(np.linalg.norm(self.nodes[edge.v] - self.nodes[edge.u]))

    def shortest(self, start, end):
        key = (start, end)
        if key in self._cache:
            return self._cache[key]
        queue, best = [(0., start)], {start: 0.}
        while queue:
            dist, node = heapq.heappop(queue)
            if dist > best[node]:
                continue
            if node == end:
                self._cache[key] = dist
                return dist
            for nxt, weight in self.adj[node]:
                value = dist + weight
                if value < best.get(nxt, math.inf):
                    best[nxt] = value
                    heapq.heappush(queue, (value, nxt))
        self._cache[key] = math.inf
        return math.inf

    def distance(self, a, b):
        # States are physical positions; heading continuity is not assumed.
        starts = [(a.edge.v, self.length(a.edge)-a.offset)]
        ends = [(b.edge.u, b.offset)]
        a_reverse = any(e.segment == a.edge.segment and e.u == a.edge.v
                        and e.v == a.edge.u for e in self.edges.values())
        b_reverse = any(e.segment == b.edge.segment and e.u == b.edge.v
                        and e.v == b.edge.u for e in self.edges.values())
        if a_reverse:
            starts.append((a.edge.u, a.offset))
        if b_reverse:
            ends.append((b.edge.v, self.length(b.edge)-b.offset))
        best = min(da+self.shortest(u,v)+db for u,da in starts for v,db in ends)
        if a.edge.segment == b.edge.segment:
            end = b.offset if a.edge.u == b.edge.u else self.length(b.edge)-b.offset
            delta = end-a.offset
            if delta >= 0 or a_reverse:
                best = min(best, abs(delta))
        return best

    def candidates(self, point, radius):
        found = []
        seen = set()
        for edge in self.edges.values():
            if edge.segment in seen:
                continue
            seen.add(edge.segment)
            origin = self.nodes[edge.u]
            vector = self.nodes[edge.v] - origin
            frac = float(np.clip(np.dot(point-origin, vector) / np.dot(vector, vector), 0, 1))
            projection = origin + frac * vector
            residual = float(np.linalg.norm(point - projection))
            if residual <= radius:
                found.append(Candidate(edge, frac*self.length(edge), projection, residual))
        return found


def synthetic_map(separation=20.):
    if separation <= 0:
        raise ValueError("Road separation must be positive")
    nodes = {f"{lane}{i}": (i*100., y)
             for lane, y in [("m", 0.), ("s", separation)] for i in range(4)}
    pairs = [(f"{lane}{i}", f"{lane}{i+1}", f"{lane}{i}")
             for lane in ("m", "s") for i in range(3)]
    pairs += [(f"m{i}", f"s{i}", f"c{i}") for i in (0, 2, 3)]
    edges = []
    for u, v, segment in pairs:
        edges += [Edge(segment+"+", segment, u, v), Edge(segment+"-", segment, v, u)]
    return RoadMap(nodes, edges)
