"""Unit tests for the 3-tier dynamic prompt pack injection and SillyTavern/CLI prompt toolkit."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _support import load_plugin_module  # noqa: E402
import prompt_tool  # noqa: E402

module = load_plugin_module("dafeiyu_prompt_packs_test_target")


class PromptPackInjectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.plugin = object.__new__(module.Main)
        self.plugin.state = module.CompanionStore(Path(self.temp.name) / "state.db")

    def tearDown(self):
        self.temp.cleanup()

    def _event(self, text: str):
        return SimpleNamespace(message_str=text)

    async def test_default_mode_injects_only_huorengan_anti_ai_pack(self):
        req = SimpleNamespace(system_prompt="基础人设")
        await self.plugin._inject_packs(self._event("今天吃什么"), req)
        self.assertIn("去AI味 · 活人感日常对话规则", req.system_prompt)
        self.assertNotIn("【当前玩法：", req.system_prompt)
        self.assertNotIn("强制词汇表", req.system_prompt)

    async def test_mode_trigger_switches_and_persists_until_exit_safeword(self):
        # 1. Enter momo mode
        req1 = SimpleNamespace(system_prompt="基础人设")
        await self.plugin._inject_packs(self._event("玩嬷嬷"), req1)
        self.assertEqual(self.plugin.state.get("pack_mode"), "momo")
        self.assertIn("【当前玩法：嬷嬷】", req1.system_prompt)
        self.assertIn("他看她的顺序是胸→腰→腿→脸", req1.system_prompt)
        self.assertIn("强制词汇表", req1.system_prompt)

        # 2. Subsequent normal message stays in momo mode
        req2 = SimpleNamespace(system_prompt="基础人设")
        await self.plugin._inject_packs(self._event("你看我今天穿的裙子"), req2)
        self.assertEqual(self.plugin.state.get("pack_mode"), "momo")
        self.assertIn("【当前玩法：嬷嬷】", req2.system_prompt)

        # 3. Switch to DDLG mode
        req3 = SimpleNamespace(system_prompt="基础人设")
        await self.plugin._inject_packs(self._event("玩DDLG"), req3)
        self.assertEqual(self.plugin.state.get("pack_mode"), "ddlg")
        self.assertIn("【当前玩法：DDLG】", req3.system_prompt)
        self.assertNotIn("【当前玩法：嬷嬷】", req3.system_prompt)

        # 4. Safeword "出戏" exits immediately back to default
        req4 = SimpleNamespace(system_prompt="基础人设")
        await self.plugin._inject_packs(self._event("出戏"), req4)
        self.assertIsNone(self.plugin.state.get("pack_mode"))
        self.assertNotIn("【当前玩法：", req4.system_prompt)


class PromptToolCliTests(unittest.TestCase):
    def test_stats_shows_over_75_percent_token_saving_in_default_mode(self):
        stats = prompt_tool.compute_stats()
        saving = stats["default_l0_l1"]["token_saving_vs_monolithic_pct"]
        self.assertGreater(saving, 75.0)
        self.assertEqual(set(stats["modes"].keys()), {"ddlg", "momo", "chihan", "gongkai", "ntr"})

    def test_lint_passes_all_structural_and_negative_constraint_checks(self):
        report = prompt_tool.lint_prompts()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["issues"], [])

    def test_export_sillytavern_writes_valid_v2_card_and_worldbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "st"
            res = prompt_tool.export_sillytavern(out_dir, owner_qq="10001")
            card = json.loads(Path(res["character_card"]).read_text(encoding="utf-8"))
            wb = json.loads(Path(res["worldbook"]).read_text(encoding="utf-8"))
            self.assertEqual(card["spec"], "chara_card_v2")
            self.assertEqual(card["data"]["name"], "大肥鱼")
            self.assertIn("10001", card["data"]["description"])
            self.assertEqual(len(wb["entries"]), 8)


if __name__ == "__main__":
    unittest.main()
