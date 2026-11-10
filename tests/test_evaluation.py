import csv
import tempfile
import unittest
from pathlib import Path
import numpy as np
from gpsmatch import evaluation as ev
from gpsmatch.calibration import PlattCalibrator, IsotonicCalibrator, from_dict
from gpsmatch.pipeline import Config, run_pipeline
from gpsmatch.demo_server import run_demo


def row(conf, correct, status="matched", tid="t0", entropy=0.):
    matched = status == "matched"
    return {"trajectory_id": tid, "status": status, "confidence": conf if matched else None,
            "entropy": entropy if matched else None, "correct": bool(correct and matched),
            "nearest_correct": False, "true_segment_present": True}


class MetricTests(unittest.TestCase):
    def test_csv_booleans_are_parsed_explicitly(self):
        self.assertIs(ev.parse_bool("False"), False)
        self.assertIs(ev.parse_bool("True"), True)
        with self.assertRaises(ValueError):
            ev.parse_bool("false")

    def test_round_trip_and_schema(self):
        result = run_pipeline(Config(noise_kind="burst"), 7)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"p.csv"
            with path.open("w", newline="", encoding="utf8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(result["rows"][0]))
                writer.writeheader()
                writer.writerows(result["rows"])
            rows = ev.load_rows(path)
        self.assertTrue(ev.check_rows(rows))
        self.assertEqual([r["correct"] for r in rows], [r["correct"] for r in result["rows"]])
        # Metrics recomputed independently agree with the pipeline summary.
        point = ev.point_metrics(rows)
        self.assertAlmostEqual(point["accuracy"], result["metrics"]["hmm_accuracy"])
        self.assertAlmostEqual(point["candidate_recall"], result["metrics"]["candidate_recall"])
        p, y = ev.matched_arrays(rows)
        self.assertAlmostEqual(ev.probability_metrics(p, y)["brier"], result["metrics"]["brier_given_match"])

    def test_failures_stay_in_denominators(self):
        rows = [row(.9, True), row(.8, False), row(None, False, "unmatched", "t1"),
                row(None, False, "unmatched", "t1")]
        point = ev.point_metrics(rows)
        self.assertEqual(point["accuracy"], .25)
        self.assertEqual(point["accuracy_given_match"], .5)
        self.assertEqual(point["failed_trajectories"], 1)
        s, c = ev.matched_arrays(rows)
        _, coverage, risk = ev.risk_coverage(s, c, len(rows))
        np.testing.assert_allclose(coverage, [.25, .5])
        np.testing.assert_allclose(risk, [0., .5])
        self.assertEqual(ev.risk_at_coverage(s, c, len(rows), .9), (None, .5))

    def test_ties_are_accepted_together(self):
        s = np.array([1., 1., 1., .5])
        c = np.array([True, False, True, True])
        thresholds, coverage, risk = ev.risk_coverage(s, c, 4)
        np.testing.assert_allclose(coverage, [.75, 1.])
        np.testing.assert_allclose(risk, [1/3, .25])
        self.assertEqual(ev.threshold_for_risk(s, c, 4, .3), .5)
        self.assertEqual(ev.threshold_for_risk(s, c, 4, .1), float("inf"))
        self.assertIsNone(ev.apply_threshold(s, c, 4, 2.)["accepted_risk"])

    def test_probability_metrics(self):
        m = ev.probability_metrics([1., 0., .5, .5], [1, 0, 1, 0])
        self.assertAlmostEqual(m["brier"], .125)
        self.assertAlmostEqual(m["ece"], 0.)
        table = ev.reliability_table([0., 1., .05], [0, 1, 0], bins=10)
        self.assertEqual(table[0]["count"], 2)
        self.assertEqual(table[-1]["count"], 1)

    def test_group_bootstrap(self):
        groups = [[row(.9, True)]*5, [row(.9, False)]*5]
        ci = ev.bootstrap_groups(groups, lambda rows: ev.point_metrics(rows)["accuracy"], draws=200)
        self.assertLessEqual(ci[0], .5)
        self.assertGreaterEqual(ci[1], .5)


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.p = rng.uniform(.3, 1., 4000)
        # True accuracy is lower than the reported confidence: overconfident.
        self.y = rng.uniform(size=4000) < self.p**2

    def test_platt_improves_overconfident_scores_and_preserves_order(self):
        cal = PlattCalibrator().fit(self.p, self.y)
        q = cal.predict(self.p)
        self.assertGreater(cal.a, 0)
        self.assertLess(np.mean((q-self.y)**2), np.mean((self.p-self.y)**2))
        order = np.argsort(self.p)
        self.assertTrue(np.all(np.diff(q[order]) >= -1e-12))
        # Same risk-coverage curve: a strictly increasing map keeps the ranking.
        a = ev.risk_coverage(self.p, self.y, len(self.p))
        b = ev.risk_coverage(q, self.y, len(self.p))
        np.testing.assert_allclose(a[1], b[1])
        np.testing.assert_allclose(a[2], b[2])
        clone = from_dict(cal.to_dict())
        np.testing.assert_allclose(clone.predict(self.p), q)

    def test_isotonic_is_monotone_and_fits_training_means(self):
        cal = IsotonicCalibrator().fit(self.p, self.y)
        q = cal.predict(np.sort(self.p))
        self.assertTrue(np.all(np.diff(q) >= 0))
        self.assertAlmostEqual(float(np.mean(cal.predict(self.p))), float(np.mean(self.y)), places=3)
        clone = from_dict(cal.to_dict())
        np.testing.assert_allclose(clone.predict(self.p), cal.predict(self.p))

    def test_empty_fit_refused(self):
        with self.assertRaises(ValueError):
            PlattCalibrator().fit([], [])


class DemoTests(unittest.TestCase):
    def test_demo_uses_pipeline_predictions(self):
        query = {"seed": ["5"], "noise_kind": ["burst"], "threshold": [".8"]}
        payload = run_demo(query, study_dir=Path("does-not-exist"))
        reference = run_pipeline(Config(noise_kind="burst"), 5)
        self.assertEqual([p["selected_segment"] for p in payload["points"]],
                         [r["selected_segment"] for r in reference["rows"]])
        accepted = [p for p in payload["points"] if p["accepted"]]
        self.assertAlmostEqual(payload["metrics"]["coverage"], len(accepted)/len(reference["rows"]))
        self.assertAlmostEqual(payload["metrics"]["accuracy"], reference["metrics"]["hmm_accuracy"])

    def test_demo_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            run_demo({"threshold": ["2"]}, study_dir=Path("does-not-exist"))
        with self.assertRaises(ValueError):
            run_demo({"model": ["nope"]}, study_dir=Path("does-not-exist"))


if __name__ == "__main__":
    unittest.main()
