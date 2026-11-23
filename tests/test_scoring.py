import unittest
from copy import deepcopy

from catalogue import CRITERIA, ISSUES, ACTIONS, ACTION_BY_ID
from scoring import (new_assessment, default_weights, evaluate, default_action,
                     project_scenario, cost_totals, validate_snapshot)


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.assessment = new_assessment()
        self.weights = default_weights()

    def rate_all(self, rating):
        for item in self.assessment.values():
            item.update(status="Assessed", rating=rating)

    def test_initial_assessment_has_no_invented_score(self):
        r = evaluate(self.assessment, self.weights)
        self.assertIsNone(r["score"])
        self.assertEqual(r["coverage"], 0)
        self.assertEqual((r["lower"], r["upper"]), (0, 100))

    def test_original_weighted_scale_is_preserved(self):
        self.rate_all(2)
        self.assertEqual(evaluate(self.assessment, self.weights)["score"], 50)
        for issue in CRITERIA[0]["issues"]:
            self.assessment[issue["id"]]["rating"] = 4
        self.assertAlmostEqual(evaluate(self.assessment, self.weights)["score"], 57.5)
        scaled = {key: value / 2 for key, value in self.weights.items()}
        self.assertAlmostEqual(evaluate(self.assessment, scaled)["score"], 57.5)

    def test_missing_items_remain_in_bounds_and_denominator(self):
        self.assessment["dark_gaps"].update(status="Assessed", rating=4)
        r = evaluate(self.assessment, self.weights)
        self.assertAlmostEqual(r["coverage"], 15 / 4)
        self.assertAlmostEqual(r["lower"], 15 / 4)
        self.assertEqual(r["upper"], 100)
        self.assertIsNone(r["score"])

    def test_all_na_and_zero_weights_do_not_divide_by_zero(self):
        for item in self.assessment.values():
            item["status"] = "Not applicable"
        self.assertIsNone(evaluate(self.assessment, self.weights)["score"])
        self.rate_all(4)
        r = evaluate(self.assessment, {key: 0 for key in self.weights})
        self.assertIsNone(r["score"])
        self.assertEqual(r["total_weight"], 0)

    def test_na_theme_is_removed_and_partial_na_keeps_theme_weight(self):
        self.rate_all(4)
        self.assessment["dark_gaps"]["status"] = "Not applicable"
        r = evaluate(self.assessment, self.weights)
        self.assertEqual(r["score"], 100)
        self.assertEqual(r["rows"][1]["normalised_weight"], 15)
        for issue in CRITERIA[1]["issues"]:
            self.assessment[issue["id"]]["status"] = "Not applicable"
        r = evaluate(self.assessment, self.weights)
        self.assertAlmostEqual(r["rows"][0]["normalised_weight"], 15 / 85 * 100)

    def test_multiple_actions_do_not_double_count_gain_or_mutate_baseline(self):
        self.rate_all(1)
        plan = {}
        for key, target in [("light_adjust", 3), ("light_replace", 4)]:
            plan[key] = {**default_action(ACTION_BY_ID[key]), "selected": True, "target": target}
        projected = project_scenario(self.assessment, plan)
        self.assertEqual(projected["dark_gaps"]["rating"], 4)
        self.assertEqual(self.assessment["dark_gaps"]["rating"], 1)
        gain = evaluate(projected, self.weights)["score"] - evaluate(self.assessment, self.weights)["score"]
        self.assertAlmostEqual(gain, 3 / 4 * 15 / 4)

    def test_unknown_and_zero_quantity_get_no_speculative_gain(self):
        config = {**default_action(ACTION_BY_ID["light_adjust"]), "selected": True, "target": 4}
        self.assertEqual(project_scenario(self.assessment, {"light_adjust": config})["dark_gaps"]["status"], "Not assessed")
        self.rate_all(1)
        config["quantity"] = 0
        self.assertEqual(project_scenario(self.assessment, {"light_adjust": config})["dark_gaps"]["rating"], 1)

    def test_side_effect_can_reduce_net_score(self):
        self.rate_all(3)
        plan = {"light_replace": {**default_action(ACTION_BY_ID["light_replace"]), "selected": True, "target": 4}}
        future = project_scenario(self.assessment, plan, {"glare": 0})
        self.assertLess(evaluate(future, self.weights)["score"], evaluate(self.assessment, self.weights)["score"])
        self.assertEqual(self.assessment["glare"]["rating"], 3)
        self.assertEqual(project_scenario(self.assessment, {}, {"glare": 0})["glare"]["rating"], 3)

    def test_investment_and_recurring_costs_use_actual_quantities(self):
        plan = {"light_adjust": {**default_action(ACTION_BY_ID["light_adjust"]), "selected": True,
                 "quantity": 3, "low": 100, "high": 200, "annual": 10}}
        costs = cost_totals(plan, 5)
        self.assertEqual(costs, {"low": 300, "high": 600, "annual": 30, "lifecycle_low": 450, "lifecycle_high": 750})

    def valid_snapshot(self):
        return {"schema_version": 1, "project": {"name": "Test", "stage": "Planning", "area": 100, "budget": 10000, "years": 5},
                "assessment": self.assessment, "weights": self.weights, "plan": {}, "adjustments": {}}

    def test_backup_round_trip_and_reject_malformed_data(self):
        valid = self.valid_snapshot()
        self.assertEqual(validate_snapshot(valid), valid)
        for mutate in [lambda d: d["weights"].update(lighting=float("nan")),
                       lambda d: d["assessment"]["dark_gaps"].update(rating=True),
                       lambda d: d.update(plan={"unknown": {}}),
                       lambda d: d.update(adjustments={"glare": 5})]:
            data = deepcopy(valid)
            mutate(data)
            with self.assertRaises(ValueError):
                validate_snapshot(data)

    def test_catalogue_covers_every_issue_with_complete_actions(self):
        self.assertEqual(len(ISSUES), 22)
        self.assertEqual({a["issue"] for a in ACTIONS}, set(ISSUES))
        self.assertEqual(len(ACTION_BY_ID), len(ACTIONS))
        for a in ACTIONS:
            self.assertLessEqual(a["low"], a["high"])
            self.assertTrue(a["tradeoff"] and a["prerequisite"] and a["cost_basis"])
        for item in ISSUES.values():
            self.assertEqual(len(item["rubric"]), 5)


if __name__ == "__main__":
    unittest.main()
