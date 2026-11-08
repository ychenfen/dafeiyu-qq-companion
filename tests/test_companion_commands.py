import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _support import load_plugin_module

module = load_plugin_module("dafeiyu_command_test_target")


class CompanionCommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.plugin = object.__new__(module.Main)
        self.plugin.state = module.CompanionStore(Path(self.temp.name) / "state.db")

    def tearDown(self):
        self.temp.cleanup()

    def event(self, text, owner=True):
        return SimpleNamespace(
            get_platform_id=lambda: "napcat", get_sender_id=lambda: module.OWNER_QQ if owner else "stranger",
            is_private_chat=lambda: True, message_str=text, stop_event=lambda: None, plain_result=lambda x: x,
        )

    async def command(self, text, owner=True):
        return [reply async for reply in self.plugin.handle_companion_commands(self.event(text, owner))]

    async def test_save_correct_recall_and_forget(self):
        await self.command("记住 饮料=不喝咖啡")
        await self.command("记住 饮料=喜欢红茶")
        self.assertIn("喜欢红茶", self.plugin._memory_prompt())
        self.assertNotIn("不喝咖啡", self.plugin._memory_prompt())
        fact = self.plugin.state.facts()[0]
        await self.command(f"记忆 修改 {fact['id']}=喜欢绿茶")
        self.assertIn("喜欢绿茶", self.plugin._memory_prompt())
        await self.command(f"忘记 {fact['id']}")
        self.assertEqual(self.plugin.state.facts(), [])

    async def test_stranger_cannot_read_or_write_owner_memory(self):
        await self.command("记住 饮料=喜欢红茶")
        self.assertEqual(await self.command("记忆", owner=False), [])
        self.assertEqual(await self.command("记住 饮料=不喝茶", owner=False), [])
        self.assertEqual(self.plugin.state.facts()[0]["value"], "喜欢红茶")

    async def test_busy_pause_and_explicit_resume(self):
        await self.plugin.record_owner_activity(self.event("我现在在忙"))
        self.assertGreater(self.plugin.state.get("paused_until"), 0)
        await self.command("恢复主动")
        self.assertEqual(self.plugin.state.get("paused_until"), 0)

    async def test_natural_forget_tool_deletes_only_an_explicit_owner_target(self):
        self.plugin.state.remember("饮料", "喜欢红茶")
        result = await self.plugin.forget_owner_fact(self.event("把饮料这条记忆忘记"), "饮料")
        self.assertIn("已删除", result)
        self.assertEqual(self.plugin.state.facts(), [])

    async def test_ambiguous_forget_does_not_remove_arbitrary_facts(self):
        self.plugin.state.remember("饮料", "喜欢红茶")
        self.plugin.state.remember("天气", "喜欢下雨")
        result = await self.plugin.forget_owner_fact(self.event("忘记那个"), "饮料")
        self.assertEqual(len(self.plugin.state.facts()), 2)
        self.assertIn("明确", result)


if __name__ == "__main__":
    unittest.main()
