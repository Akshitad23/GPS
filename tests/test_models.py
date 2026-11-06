"""Regression and mathematical checks for optional HMM variants."""
import itertools
import unittest
import numpy as np
from scipy.special import logsumexp
from gpsmatch import Config, run_pipeline
from gpsmatch.pipeline import match
from gpsmatch.roads import synthetic_map
from gpsmatch.models import distance_matrix, motion_estimates, emission_scores


class ModelTests(unittest.TestCase):
    def test_vectorised_routing_matches_scalar(self):
        roads = synthetic_map()
        a = roads.candidates(np.array([95.,5.]),90.)
        b = roads.candidates(np.array([205.,25.]),90.)
        expected = np.array([[roads.distance(x,y) for y in b] for x in a])
        np.testing.assert_allclose(distance_matrix(roads,a,b),expected)

    def test_constant_motion_without_truth(self):
        times = np.arange(12,dtype=float)
        xy = np.column_stack([8.*times, np.ones(12)*15.])
        velocity,speed = motion_estimates(times,xy)
        np.testing.assert_allclose(velocity,np.tile([8.,0.],(12,1)))
        np.testing.assert_allclose(speed,8.)

    def test_robust_tail(self):
        gaussian = emission_scores([0.,100.],8.)
        robust = emission_scores([0.,100.],8.,"student",4.)
        self.assertEqual(robust[0],0.)
        self.assertGreater(robust[1],gaussian[1])

    def test_zero_bias_grid_reduces_to_motion(self):
        roads = synthetic_map()
        times = np.arange(4,dtype=float)
        xy = np.array([[30.,2.],[40.,0.],[45.,-1.],[55.,2.]])
        motion = match(roads,times,xy,Config(model="motion"))
        bias = match(roads,times,xy,Config(model="bias",bias_levels=(0.,)))
        self.assertEqual(motion["path"],bias["path"])
        for a,b in zip(motion["posterior"],bias["posterior"]):
            np.testing.assert_allclose(a,b)

    def test_augmented_lattice_exhaustive(self):
        roads = synthetic_map()
        output = match(roads,np.array([0.,1.]),np.array([[30.,1.],[38.,2.]]),
                       Config(model="bias",bias_levels=(-15.,0.,15.),candidate_radius=25.))
        initial,emissions,transitions = output["log_initial"],output["log_emissions"],output["transitions"]
        paths = list(itertools.product(range(len(emissions[0])),range(len(emissions[1]))))
        scores = [initial[i]+emissions[0][i]+transitions[0][i,j]+emissions[1][j] for i,j in paths]
        evidence = logsumexp(scores)
        self.assertAlmostEqual(output["log_evidence"],evidence)
        self.assertEqual(output["path"],list(paths[int(np.argmax(scores))]))
        for t in (0,1):
            for j in range(len(emissions[t])):
                marginal = np.exp(logsumexp([s for p,s in zip(paths,scores) if p[t]==j])-evidence)
                self.assertAlmostEqual(output["posterior"][t][j],marginal)

    def test_bias_projection_precedes_candidate_generation(self):
        roads = synthetic_map()
        times = np.array([0.])
        xy = np.array([[40.,30.]])
        # Raw point is >5m from both horizontal roads; bias hypotheses recover them.
        output = match(roads,times,xy,Config(model="bias",candidate_radius=5.))
        self.assertTrue(any(c.edge.segment=="m0" for c in output["candidates"][0]))
        for candidate,bias in zip(output["candidates"][0],output["state_biases"][0]):
            self.assertAlmostEqual(candidate.residual,np.linalg.norm(xy[0]-bias-candidate.point))

    def test_direction_and_rmse_controls(self):
        positive = run_pipeline(Config(noise_kind="burst",burst_angle_degrees=90.),5)
        negative = run_pipeline(Config(noise_kind="burst",burst_angle_degrees=-90.),5)
        matched = run_pipeline(Config(noise_kind="matched_iid",burst_angle_degrees=-90.),5)
        self.assertNotEqual([r["gps_y"] for r in positive["rows"]],[r["gps_y"] for r in negative["rows"]])
        self.assertAlmostEqual(negative["metrics"]["gps_rmse"],matched["metrics"]["gps_rmse"])

    def test_model_data_are_paired(self):
        results = [run_pipeline(Config(model=m,noise_kind="burst"),7)
                   for m in ("baseline","motion","robust","bias")]
        reference = [(r["gps_x"],r["gps_y"],r["true_segment"]) for r in results[0]["rows"]]
        for result in results:
            self.assertEqual(reference,[(r["gps_x"],r["gps_y"],r["true_segment"]) for r in result["rows"]])
            self.assertIsNone(result["failure"])
            for row in result["rows"]:
                self.assertTrue(0<=row["confidence"]<=1.+1e-12)


    def test_baseline_regression(self):
        result = run_pipeline(Config(noise_kind="burst"),42)
        self.assertAlmostEqual(result["metrics"]["hmm_accuracy"],35/37)
        self.assertAlmostEqual(result["metrics"]["gps_rmse"],17.38525865741981)

    def test_comparison_metrics_boolean_targets(self):
        from gpsmatch.compare import aggregate
        result = run_pipeline(Config(),5)
        output = aggregate([result])
        self.assertTrue(np.isfinite(output["log_loss_given_match"]))
        self.assertGreaterEqual(output["confident_wrong_count"],0)

    def test_invalid_options(self):
        for config in (Config(model="other"),Config(student_df=0.),Config(bias_jump_probability=1.),
                       Config(bias_levels=(1.,)),Config(initial_bias_sigma=0.)):
            with self.assertRaises(ValueError):
                config.validate()


if __name__=="__main__":
    unittest.main()
