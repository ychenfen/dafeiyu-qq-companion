"""Run inside AstrBot's container; isolate only the external QQ boundary."""

import importlib.util
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location(
    "dafeiyu_signature_test_target",
    Path("/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py"),
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class QQBoundary:
    def __init__(self, *, reject=False, stale=False):
        self.signature = "旧签名"
        self.nickname = "原来的昵称"
        self.reject = reject
        self.stale = stale

    async def call_action(self, action, **params):
        if action == "get_login_info":
            return {"user_id": "bot-id", "nickname": self.nickname}
        if action == "set_qq_profile":
            if params.get("nickname") != self.nickname:
                raise ValueError("existing nickname must be preserved")
            if self.reject:
                return {"result": 1, "errMsg": "rejected"}
            if not self.stale:
                self.signature = params["personal_note"]
            return {"result": 0, "errMsg": ""}
        elif action == "get_stranger_info":
            return {"long_nick": self.signature}
        raise ValueError("unsupported action")


class SignatureTests(unittest.IsolatedAsyncioTestCase):
    def plugin(self, **options):
        boundary = QQBoundary(**options)
        plugin = object.__new__(module.Main)
        plugin.context = SimpleNamespace(
            get_platform_inst=lambda _: SimpleNamespace(bot=boundary)
        )
        return plugin, boundary

    def event(self, owner=True):
        return SimpleNamespace(
            get_platform_id=lambda: "napcat",
            get_sender_id=lambda: "<OWNER_QQ>" if owner else "stranger",
            get_self_id=lambda: "bot-id",
        )

    async def test_owner_can_change_signature_without_changing_nickname(self):
        plugin, qq = self.plugin()
        result = await plugin.set_qq_signature(self.event(), "新的心情")
        self.assertEqual(qq.signature, "新的心情")
        self.assertEqual(qq.nickname, "原来的昵称")
        self.assertIn("已核验", result)

    async def test_strangers_cannot_change_the_bot_profile(self):
        plugin, qq = self.plugin()
        result = await plugin.set_qq_signature(self.event(owner=False), "陌生人修改")
        self.assertEqual(qq.signature, "旧签名")
        self.assertIn("只有主人", result)

    async def test_rejected_change_is_never_reported_as_success(self):
        plugin, qq = self.plugin(reject=True)
        result = await plugin.set_qq_signature(self.event(), "新的心情")
        self.assertEqual(qq.signature, "旧签名")
        self.assertIn("失败", result)

    async def test_existing_signature_is_verified_without_another_write(self):
        plugin, qq = self.plugin(reject=True)
        result = await plugin.set_qq_signature(self.event(), "旧签名")
        self.assertEqual(qq.signature, "旧签名")
        self.assertIn("已核验", result)

    async def test_unconfirmed_write_is_not_reported_as_verified(self):
        plugin, qq = self.plugin(stale=True)
        result = await plugin.set_qq_signature(self.event(), "新的心情")
        self.assertEqual(qq.signature, "旧签名")
        self.assertIn("未核验", result)

    async def test_autonomous_changes_are_limited_but_owner_requests_still_work(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin, qq = self.plugin()
            plugin.state = module.CompanionStore(Path(temp) / "state.db")
            event = self.event()
            event.message_str = "夸你一句"
            await plugin.set_qq_signature(event, "心情一")
            await plugin.set_qq_signature(event, "心情二")
            result = await plugin.set_qq_signature(event, "心情三")
            self.assertEqual(qq.signature, "心情二")
            self.assertIn("两次", result)
            event.message_str = "把签名改成主人指定的内容"
            await plugin.set_qq_signature(event, "主人指定的内容")
            self.assertEqual(qq.signature, "主人指定的内容")


if __name__ == "__main__":
    unittest.main()
