import itertools
import unittest
from dataclasses import replace
import numpy as np
from scipy.special import logsumexp
from gpsmatch.inference import infer, NoPathError
from gpsmatch.roads import RoadMap, Edge, Candidate, synthetic_map
from gpsmatch.simulation import journey, corrupt
from gpsmatch.pipeline import Config, run_pipeline, match


class InferenceTests(unittest.TestCase):
    def test_exhaustive_variable_width(self):
        initial = np.log([.5,.5])
        emissions = [np.log([.9,.1]), np.log([.4,.5,.1]), np.log([.6,.4])]
        transitions = [np.log([[.8,.1,.1],[.1,.8,.1]]),
                       np.log([[.9,.1],[.2,.8],[.5,.5]])]
        output = infer(initial, emissions, transitions)
        paths = list(itertools.product(range(2),range(3),range(2)))
        scores = []
        for path in paths:
            value = initial[path[0]] + emissions[0][path[0]]
            for t in (1,2):
                value += transitions[t-1][path[t-1],path[t]]+emissions[t][path[t]]
            scores.append(value)
        self.assertEqual(output["path"], list(paths[int(np.argmax(scores))]))
        self.assertAlmostEqual(output["log_evidence"], logsumexp(scores))
        for t in range(3):
            expected = [np.exp(logsumexp([s for p,s in zip(paths,scores) if p[t]==j])
                               -logsumexp(scores)) for j in range(len(emissions[t]))]
            np.testing.assert_allclose(output["posterior"][t], expected)

    def test_guide_example(self):
        output = infer(np.log([.5,.5]), [np.log([.9,.1]),np.log([.4,.6])],
                       [np.log([[.9,.1],[.1,.9]])])
        self.assertEqual(output["path"], [0,0])
        self.assertAlmostEqual(output["posterior"][1][0], .164/.218)

    def test_long_sequence(self):
        output = infer(np.log([.5,.5]), [np.array([-1000.,-1001.]) for _ in range(1000)],
                       [np.log([[.9,.1],[.1,.9]]) for _ in range(999)])
        self.assertTrue(np.isfinite(output["log_evidence"]))
        for posterior in output["posterior"]:
            self.assertAlmostEqual(posterior.sum(), 1.)

    def test_impossible(self):
        with self.assertRaises(NoPathError):
            infer(np.array([0.]),[np.array([0.]),np.array([0.])],[np.array([[-np.inf]])])

    def test_empty_and_bad_shape(self):
        with self.assertRaises(NoPathError):
            infer(np.array([]),[np.array([])],[])
        with self.assertRaises(ValueError):
            infer(np.array([0.]),[np.array([0.]),np.array([0.])],[np.zeros((2,1))])


class RoadTests(unittest.TestCase):
    def test_partial_directed_distance(self):
        roads = RoadMap({"a":(0,0),"b":(100,0),"c":(200,0),"d":(0,50)},
                        [Edge("ab","ab","a","b"), Edge("bc","bc","b","c")])
        a = Candidate(roads.edges["ab"],20.,np.array([20.,0]),0.)
        b = Candidate(roads.edges["ab"],40.,np.array([40.,0]),0.)
        c = Candidate(roads.edges["bc"],30.,np.array([130.,0]),0.)
        self.assertAlmostEqual(roads.distance(a,b),20.)
        self.assertAlmostEqual(roads.distance(a,c),110.)
        self.assertTrue(np.isinf(roads.distance(b,a)))
        self.assertTrue(np.isinf(roads.shortest("a","d")))


    def test_bidirectional_jitter(self):
        roads = synthetic_map()
        a = next(c for c in roads.candidates(np.array([40.,0.]),1.) if c.edge.segment=="m0")
        b = next(c for c in roads.candidates(np.array([35.,0.]),1.) if c.edge.segment=="m0")
        self.assertAlmostEqual(roads.distance(a,b),5.)
        self.assertEqual(len({c.edge.segment for c in roads.candidates(np.array([40.,0.]),60.)}),
                         len(roads.candidates(np.array([40.,0.]),60.)))

    def test_projection(self):
        roads = synthetic_map()
        candidate = next(c for c in roads.candidates(np.array([25.,4.]),5.) if c.edge.id=="m0+")
        np.testing.assert_allclose(candidate.point,[25.,0.])
        self.assertAlmostEqual(candidate.offset,25.)
        self.assertAlmostEqual(candidate.residual,4.)


class PipelineTests(unittest.TestCase):
    def test_reproducible(self):
        a,b = run_pipeline(seed=7),run_pipeline(seed=7)
        self.assertEqual(a["rows"],b["rows"])

    def test_noiseless_all_routes(self):
        for variant in range(6):
            result = run_pipeline(Config(noise_sigma=0.,assumed_sigma=.1,route_variant=variant),seed=3)
            self.assertIsNone(result["failure"])
            self.assertEqual(result["metrics"]["hmm_accuracy"],1.)

    def test_gap_preserves_timestamps(self):
        roads = synthetic_map()
        truth = journey(roads,np.random.default_rng(2))
        obs = corrupt(truth,np.random.default_rng(3),"gap")
        self.assertGreater(np.max(np.diff(obs["time"])),1.)
        self.assertLess(len(obs["time"]),len(truth["time"]))

    def test_matched_rmse(self):
        a = run_pipeline(Config(noise_kind="burst"),seed=3)
        b = run_pipeline(Config(noise_kind="matched_iid"),seed=3)
        self.assertAlmostEqual(a["metrics"]["gps_rmse"],b["metrics"]["gps_rmse"])

    def test_excluded_candidates_visible(self):
        result = run_pipeline(Config(noise_sigma=10000.,candidate_radius=.001),seed=4)
        self.assertIsNotNone(result["failure"])
        self.assertEqual(result["metrics"]["matched_fraction"],0.)
        self.assertEqual(result["metrics"]["hmm_accuracy"],0.)
        self.assertIsNone(result["metrics"]["brier_given_match"])

    def test_confidence_bounded(self):
        for kind in ("independent","burst","gap"):
            result = run_pipeline(Config(noise_kind=kind),seed=42)
            self.assertIsNone(result["failure"])
            for row in result["rows"]:
                self.assertGreaterEqual(row["confidence"],0.)
                self.assertLessEqual(row["confidence"],1.+1e-12)
                self.assertGreaterEqual(row["entropy"],-1e-12)
                self.assertLessEqual(row["entropy"],1.+1e-12)

    def test_invalid_configuration(self):
        for config in (Config(assumed_sigma=0),Config(sample_interval=-1),Config(noise_sigma=-1)):
            with self.assertRaises(ValueError):
                run_pipeline(config)


    def test_projection_uncertainty_allowance(self):
        roads = RoadMap({"a":(0,0),"b":(100,0)},
                        [Edge("ab","ab","a","b"),Edge("ba","ab","b","a")])
        observations = np.array([[20.,0.],[60.,0.]])
        with self.assertRaises(NoPathError):
            match(roads,np.array([0.,1.]),observations,Config(max_speed=10.,projection_slack_sigma=0.))
        output = match(roads,np.array([0.,1.]),observations,Config(max_speed=10.,projection_slack_sigma=3.))
        self.assertEqual(len(output["path"]),2)

    def test_config_specific_ids(self):
        a = run_pipeline(Config(noise_sigma=3.),seed=4)
        b = run_pipeline(Config(noise_sigma=4.),seed=4)
        self.assertNotEqual(a["trajectory_id"],b["trajectory_id"])

    def test_invalid_timestamps(self):
        with self.assertRaises(ValueError):
            match(synthetic_map(),np.array([1.,1.]),np.zeros((2,2)),Config())


if __name__ == "__main__":
    unittest.main()
