import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP), default_timeout=20).run()
        self.assertFalse(self.app.exception)

    def navigate(self, route):
        self.app.radio(key="_route").set_value(route).run()
        self.assertFalse(self.app.exception)

    def sample(self):
        next(b for b in self.app.button if b.label.startswith("Load fictional sample")).click().run()
        self.assertFalse(self.app.exception)

    def test_navigation_and_assessment_survive_widget_cleanup(self):
        self.navigate("Assess the project")
        self.app.selectbox(key="_theme").select("Lighting and night-time safety").run()
        self.app.selectbox(key="_status_dark_gaps").select("Assessed").run()
        self.app.select_slider(key="_rating_dark_gaps").set_value(1).run()
        self.app.text_area(key="_observation_dark_gaps").input("Dark path at 22:00").run()
        self.app.text_area(key="_evidence_dark_gaps_False").input("Night audit 01").run()
        self.navigate("Overview")
        self.navigate("Assess the project")
        self.app.selectbox(key="_theme").select("Lighting and night-time safety").run()
        self.assertEqual(self.app.select_slider(key="_rating_dark_gaps").value, 1)
        self.assertEqual(self.app.text_area(key="_observation_dark_gaps").value, "Dark path at 22:00")
        self.assertEqual(self.app.text_area(key="_evidence_dark_gaps_False").value, "Night audit 01")

    def test_sample_plan_scenario_exports_and_budget(self):
        self.sample()
        self.navigate("Build an action plan")
        self.app.selectbox(key="_plan_theme").select("Lighting and night-time safety").run()
        self.app.checkbox(key="_action_light_adjust_selected").check().run()
        self.app.number_input(key="_action_light_adjust_quantity").set_value(4.0).run()
        self.app.slider(key="_action_light_adjust_target").set_value(3).run()
        self.assertFalse(self.app.exception)
        self.navigate("Report and save")
        self.assertGreater(len(self.app.get("download_button")), 2)
        self.navigate("Build an action plan")
        self.app.selectbox(key="_plan_theme").select("Lighting and night-time safety").run()
        self.assertEqual(self.app.number_input(key="_action_light_adjust_quantity").value, 4.0)
        self.assertEqual(self.app.slider(key="_action_light_adjust_target").value, 3)
        self.app.number_input(key="_action_light_adjust_low").set_value(10000.0).run()
        self.assertTrue(self.app.error)
        self.navigate("Report and save")
        self.assertTrue(self.app.error)
        self.assertEqual(len(self.app.get("download_button")), 0)

    def test_empty_report_all_zero_weights_and_reset(self):
        for key in self.app.session_state["weights"]:
            self.app.number_input(key="_weight_" + key).set_value(0.0)
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.warning)
        self.navigate("Report and save")
        self.assertFalse(self.app.exception)
        self.app.checkbox(key="_confirm_reset").check().run()
        next(b for b in self.app.button if b.label == "Reset assessment and plan").click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(all(x["status"] == "Not assessed" for x in self.app.session_state["assessment"].values()))


if __name__ == "__main__":
    unittest.main()
