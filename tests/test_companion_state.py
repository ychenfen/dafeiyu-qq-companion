import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "dafeiyu_state_test_target", "/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CompanionStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "companion.db"

    def tearDown(self):
        self.temp.cleanup()

    def test_fact_survives_restart_and_correction_replaces_old_value(self):
        store = module.CompanionStore(self.path)
        store.remember("饮料", "不喝咖啡")
        reopened = module.CompanionStore(self.path)
        reopened.remember("饮料", "喜欢红茶")
        facts = reopened.facts()
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["value"], "喜欢红茶")

    def test_forgotten_fact_is_not_retrieved_after_restart(self):
        store = module.CompanionStore(self.path)
        store.remember("饮料", "喜欢红茶")
        self.assertTrue(store.forget("饮料"))
        self.assertEqual(module.CompanionStore(self.path).facts(), [])

    def test_credentials_cannot_be_saved_as_memories(self):
        store = module.CompanionStore(self.path)
        with self.assertRaises(ValueError):
            store.remember("密码", "password=example-test-value")
        self.assertEqual(store.facts(), [])

    def test_pause_and_unanswered_message_state_survive_restart(self):
        store = module.CompanionStore(self.path)
        store.set("paused_until", 10000)
        store.set("last_proactive", 500)
        reopened = module.CompanionStore(self.path)
        self.assertEqual(reopened.get("paused_until"), 10000)
        self.assertEqual(reopened.get("last_proactive"), 500)


if __name__ == "__main__":
    unittest.main()
