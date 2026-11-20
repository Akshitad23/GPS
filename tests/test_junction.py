import unittest

import numpy as np

from gpsmatch.junction import add_prompts, estimate_frames, junction_replay, load_junction, simulate


class JunctionTests(unittest.TestCase):
    def setUp(self):
        _, self.roads, self.groups, self.fork, self.paths = load_junction()

    def test_directed_paths_share_approach_and_take_different_roads(self):
        stay, exit_path = self.paths["stay"], self.paths["exit"]
        self.assertEqual(stay[0], exit_path[0])
        self.assertEqual(stay[0].v, self.fork)
        self.assertEqual(self.groups[stay[1].segment], "main")
        self.assertEqual([self.groups[e.segment] for e in exit_path[1:3]], ["exit", "service"])
        for path in (stay, exit_path):
            for edge in path:
                self.assertEqual(self.roads.edges[edge.id], edge)
            self.assertTrue(all(a.v == b.u for a, b in zip(path, path[1:])))
        self.assertNotIn(stay[0].segment + "-", self.roads.edges)

    def test_future_observations_cannot_change_earlier_estimates_or_prompts(self):
        path = self.paths["stay"]
        times, gps, *_ = simulate(self.roads, self.groups, path, True)
        cutoff = 10
        prefix = estimate_frames(self.roads, self.groups, times[:cutoff], gps[:cutoff])
        changed = gps.copy()
        changed[cutoff:] += 500
        for trace in (gps, changed):
            frames = estimate_frames(self.roads, self.groups, times, trace)
            self.assertEqual(frames[:cutoff], prefix)
            prompts = add_prompts(frames, self.roads, path[0], "stay")
            self.assertEqual(prompts[:cutoff], add_prompts(prefix, self.roads, path[0], "stay"))

    def test_route_intent_changes_prompt_but_not_the_estimated_road(self):
        stay, exit_replay = junction_replay("drift-stay"), junction_replay("drift-exit")
        self.assertEqual(sum(f["burst"] for f in stay["frames"]), 8)
        self.assertEqual(sum(f["burst"] for f in exit_replay["frames"]), 8)
        for a, b in zip(stay["frames"], exit_replay["frames"]):
            if a["t"] >= 13:
                break
            for key in ("gps", "road", "estimated_xy", "confidence"):
                self.assertEqual(a[key], b[key])
        self.assertTrue(any(a["status"] == "stay" and b["status"] == "exit"
                            for a, b in zip(stay["frames"], exit_replay["frames"])))

    def test_prompt_window_and_confidence_gate(self):
        approach = self.paths["stay"][0]
        origin = self.roads.nodes[self.fork]
        away = (self.roads.nodes[approach.u] - origin) / self.roads.length(approach)
        readings = [(115, "main", .99), (98, "main", .99), (88, "main", .99),
                    (75, "main", .84), (65, None, 0.), (55, "service", .01),
                    (45, "main", .99), (35, "main", .99), (10, "main", .99),
                    (-5, "main", .99), (45, "main", .99)]
        frames = []
        for distance, road, confidence in readings:
            xy = (origin + distance * away).tolist()
            frames.append({"gps": xy, "estimated_xy": xy if road else None,
                           "road": road, "main_confidence": confidence})
        prompts = add_prompts(frames, self.roads, approach, "exit")
        self.assertEqual([f["status"] for f in prompts],
                         ["waiting", "uncertain", "exit", "uncertain", "uncertain",
                          "uncertain", "uncertain", "exit", "waiting", "passed", "passed"])
        self.assertEqual(sum(f["prompt_started"] for f in prompts), 1)

    def test_unmatched_and_clean_replay(self):
        frames = estimate_frames(self.roads, self.groups, np.array([0]), np.array([[1e5, 1e5]]))
        self.assertIsNone(frames[0]["road"])
        self.assertIsNone(frames[0]["confidence"])
        clean = junction_replay("clean")
        self.assertGreater(clean["summary"]["prompt_lead_seconds"], 0.)
        self.assertEqual(clean["summary"]["wrong_estimates"], 0)
        with self.assertRaises(ValueError):
            junction_replay("missing")
