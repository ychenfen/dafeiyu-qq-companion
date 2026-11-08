"""Check proactive delivery outcomes without sending real QQ messages."""

import importlib.util
import unittest
import datetime
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiocqhttp.exceptions import ApiNotAvailable

spec = importlib.util.spec_from_file_location(
    "dafeiyu_proactive_test_target",
    "/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProactiveTests(unittest.IsolatedAsyncioTestCase):
    def plugin(self, send):
        plugin = object.__new__(module.Main)
        provider = SimpleNamespace(
            text_chat=AsyncMock(return_value=SimpleNamespace(completion_text="在干嘛"))
        )
        plugin.context = SimpleNamespace(
            get_using_provider=lambda _: provider,
            send_message=send,
        )
        plugin._persona = lambda: ""
        return plugin

    async def test_missing_platform_is_not_reported_as_sent(self):
        plugin = self.plugin(AsyncMock(return_value=False))
        self.assertEqual(await plugin._proactive(), "")

    async def test_reconnecting_platform_can_deliver_after_retry(self):
        plugin = self.plugin(AsyncMock(side_effect=[ApiNotAvailable(), True]))
        with patch.object(module.asyncio, "sleep", new=AsyncMock()):
            self.assertEqual(await plugin._proactive(), "在干嘛")

    async def test_persistent_disconnection_is_not_reported_as_sent(self):
        plugin = self.plugin(AsyncMock(side_effect=ApiNotAvailable()))
        with patch.object(module.asyncio, "sleep", new=AsyncMock()):
            self.assertEqual(await plugin._proactive(), "")

    async def test_each_proactive_sentence_is_sent_separately(self):
        sent = []

        async def send(_, chain):
            sent.append("".join(component.text for component in chain.chain))
            return True

        plugin = self.plugin(send)
        plugin.context.get_using_provider(None).text_chat.return_value.completion_text = "在干嘛\n想起你了。有没有偷懒？"
        with patch.object(module.asyncio, "sleep", new=AsyncMock()):
            await plugin._proactive()
        self.assertEqual(sent, ["在干嘛", "想起你了。", "有没有偷懒？"])

    async def test_paused_recent_and_unanswered_chats_do_not_generate_messages(self):
        now = datetime.datetime(2026, 11, 5, 15, 20, tzinfo=module.TZ)
        for reason in ("pause", "recent", "unanswered"):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                plugin = self.plugin(AsyncMock(return_value=True))
                plugin.state = module.CompanionStore(Path(temp) / "state.db")
                if reason == "pause":
                    plugin.state.set("paused_until", now.timestamp() + 3600)
                elif reason == "recent":
                    plugin.state.set("last_owner", now.timestamp() - 30)
                else:
                    plugin.state.set("last_owner", now.timestamp() - 10000)
                    plugin.state.set("last_proactive", now.timestamp() - 5000)
                self.assertEqual(await plugin._proactive(now), "")
                plugin.context.get_using_provider(None).text_chat.assert_not_awaited()

    async def test_proactive_generation_receives_owner_memory_and_recent_dialogue(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.plugin(AsyncMock(return_value=True))
            plugin.state = module.CompanionStore(Path(temp) / "state.db")
            plugin.state.remember("饮料", "喜欢红茶")
            history = [{"role": "user", "content": "今天赶作业有点累"}, {"role": "assistant", "content": "忙完歇一歇"}]
            plugin.context.conversation_manager = SimpleNamespace(
                get_curr_conversation_id=AsyncMock(return_value="owner-conversation"),
                get_conversation=AsyncMock(return_value=SimpleNamespace(history=history)),
            )
            await plugin._proactive(force=True)
            kwargs = plugin.context.get_using_provider(None).text_chat.call_args.kwargs
            self.assertEqual(kwargs["contexts"], history)
            self.assertIn("喜欢红茶", kwargs["system_prompt"])

    async def test_completed_slot_is_not_sent_again_after_restart(self):
        now = datetime.datetime(2026, 11, 5, 15, 20, tzinfo=module.TZ)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.db"
            first = self.plugin(AsyncMock(return_value=True))
            first.state = module.CompanionStore(path)
            first._last_fired = None
            first._proactive = AsyncMock(return_value="sent")
            await first._tick(now)
            second = self.plugin(AsyncMock(return_value=True))
            second.state = module.CompanionStore(path)
            second._last_fired = None
            second._proactive = AsyncMock(return_value="sent")
            await second._tick(now)
            second._proactive.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
