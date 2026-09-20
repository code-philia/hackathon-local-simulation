from __future__ import annotations

from contextlib import redirect_stdout
from decimal import Decimal
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

from local_submit import (
    MeterUsageClient,
    MeterUsageSnapshot,
    calculate_submission_score,
    read_result,
)


class ScoringTests(unittest.TestCase):
    def test_zero_pass_rate_scores_zero(self) -> None:
        self.assertEqual(calculate_submission_score(0, 10), 0.0)

    def test_expected_cost_scores_the_pass_rate(self) -> None:
        self.assertAlmostEqual(calculate_submission_score(50, 60), 50.0)

    def test_lower_cost_is_rewarded_and_higher_cost_is_penalized(self) -> None:
        self.assertGreater(calculate_submission_score(50, 30), 50)
        self.assertLess(calculate_submission_score(50, 120), 50)

    def test_missing_or_singular_cost_has_no_score(self) -> None:
        self.assertIsNone(calculate_submission_score(50, None))
        self.assertIsNone(calculate_submission_score(50, 0))

    def test_known_reward_and_penalty_values(self) -> None:
        cases = [
            # pass rate, cost, independently calculated expected score
            (25, 15, 26.79433656340733),
            (25, 60, 21.7637640824031),
            (50, 6, 62.94627058970838),
            (50, 600, 31.547867224009664),
            (100, 12, 125.89254117941675),
            (100, 1200, 63.09573444801933),
        ]
        for pass_rate, cost, expected in cases:
            with self.subTest(pass_rate=pass_rate, cost=cost):
                self.assertAlmostEqual(calculate_submission_score(pass_rate, cost), expected)

    def test_score_decreases_as_cost_increases(self) -> None:
        costs = [6, 12, 30, 60, 120, 600]
        scores = [calculate_submission_score(50, cost) for cost in costs]
        self.assertTrue(all(score is not None for score in scores))
        self.assertTrue(all(left > right for left, right in zip(scores, scores[1:])))

    def test_score_is_continuous_at_expected_cost_boundary(self) -> None:
        below = calculate_submission_score(50, 59.999999)
        boundary = calculate_submission_score(50, 60)
        above = calculate_submission_score(50, 60.000001)
        self.assertLess(abs(below - boundary), 0.000001)
        self.assertLess(abs(above - boundary), 0.000001)

    def test_equal_cost_ratios_scale_with_pass_rate(self) -> None:
        # Both costs are half their respective expected costs.
        score_25 = calculate_submission_score(25, 15)
        score_50 = calculate_submission_score(50, 30)
        self.assertAlmostEqual(score_50, score_25 * 2)

    def test_scores_are_finite_across_dense_valid_matrix(self) -> None:
        for pass_rate in range(1, 101):
            expected_cost = 1.2 * pass_rate
            for ratio in (0.01, 0.1, 0.5, 1.0, 1.01, 2.0, 10.0, 100.0):
                with self.subTest(pass_rate=pass_rate, ratio=ratio):
                    score = calculate_submission_score(pass_rate, expected_cost * ratio)
                    self.assertIsNotNone(score)
                    self.assertTrue(math.isfinite(score))
                    self.assertGreater(score, 0)


class MeterDeltaTests(unittest.TestCase):
    def test_delta_uses_non_negative_token_and_cost_differences(self) -> None:
        start = MeterUsageSnapshot("key-1", 100, Decimal("1.25"), "CNY", 10)
        end = MeterUsageSnapshot("key-1", 350, Decimal("3.75"), "CNY", 10)
        delta = MeterUsageClient.delta(start, end)
        self.assertEqual(delta.token_count, 250)
        self.assertEqual(delta.cost, Decimal("2.50"))
        self.assertEqual(delta.currency, "CNY")


class ResultOutputTests(unittest.TestCase):
    def test_result_contains_meter_metrics_and_cost_adjusted_score(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            arc_dir = workspace / "template" / ".arc"
            arc_dir.mkdir(parents=True)
            (workspace / "local-run.json").write_text(
                json.dumps(
                    {
                        "container_exit_code": 0,
                        "token_count": 1234,
                        "token_cost": 120.0,
                        "token_cost_currency": "CNY",
                        "meter_error": None,
                    }
                ),
                encoding="utf-8",
            )
            (workspace / "local-submission.json").write_text(
                json.dumps({"evaluation_enabled": True}),
                encoding="utf-8",
            )
            (arc_dir / "agent-execution.json").write_text(
                json.dumps({"duration_seconds": 1.5}),
                encoding="utf-8",
            )
            (arc_dir / "playwright-report.json").write_text(
                json.dumps(
                    {
                        "suites": [
                            {
                                "file": "REQ-1.spec.ts",
                                "specs": [
                                    {
                                        "title": "passes",
                                        "tests": [{"results": [{"status": "passed", "duration": 5}]}],
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                self.assertEqual(read_result(workspace), 0)

            result = json.loads((workspace / "local-result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["test_pass_rate"], 100.0)
            self.assertAlmostEqual(result["score"], 100.0)
            self.assertEqual(result["token_count"], 1234)
            self.assertEqual(result["token_cost"], 120.0)
            self.assertEqual(result["token_cost_usd"], 120.0)
            self.assertEqual(result["token_cost_currency"], "CNY")

    def test_result_scores_using_exact_unrounded_pass_rate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            arc_dir = workspace / "template" / ".arc"
            arc_dir.mkdir(parents=True)
            (workspace / "local-run.json").write_text(
                json.dumps({"container_exit_code": 1, "token_cost": 80.0}),
                encoding="utf-8",
            )
            (workspace / "local-submission.json").write_text(
                json.dumps({"evaluation_enabled": True}),
                encoding="utf-8",
            )
            results = ["passed", "passed", "failed"]
            (arc_dir / "playwright-report.json").write_text(
                json.dumps(
                    {
                        "suites": [
                            {
                                "file": "REQ-1.spec.ts",
                                "specs": [
                                    {
                                        "title": f"case-{index}",
                                        "tests": [{"results": [{"status": status}]}],
                                    }
                                    for index, status in enumerate(results)
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                self.assertEqual(read_result(workspace), 1)

            result = json.loads((workspace / "local-result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["test_pass_rate"], 66.7)
            self.assertAlmostEqual(result["score"], 200 / 3)

    def test_failed_result_still_contains_meter_metrics_and_score(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            (workspace / "template" / ".arc").mkdir(parents=True)
            (workspace / "local-run.json").write_text(
                json.dumps(
                    {
                        "container_exit_code": 1,
                        "token_count": 50,
                        "token_cost": 2.5,
                        "token_cost_currency": "CNY",
                    }
                ),
                encoding="utf-8",
            )
            (workspace / "local-submission.json").write_text(
                json.dumps({"evaluation_enabled": True}),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                self.assertEqual(read_result(workspace), 2)

            result = json.loads((workspace / "local-result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["evaluation_status"], "failed")
            self.assertEqual(result["score"], 0.0)
            self.assertEqual(result["token_count"], 50)
            self.assertEqual(result["token_cost"], 2.5)


if __name__ == "__main__":
    unittest.main()
