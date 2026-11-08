import importlib.util
import unittest
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location(
    "dafeiyu_context_test_target", "/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SignatureContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_chat_request_changes_the_signature_before_replying(self):
        state = {"signature": ""}

        async def action(name, **params):
            if name == "get_stranger_info":
                return {"long_nick": state["signature"]}
            if name == "get_login_info":
                return {"nickname": "原昵称"}
            if name == "set_qq_profile":
                state["signature"] = params["personal_note"]
                return {"result": 0, "errMsg": ""}
            raise ValueError(name)

        plugin = object.__new__(module.Main)
        plugin.context = SimpleNamespace(get_platform_inst=lambda _: SimpleNamespace(
            bot=SimpleNamespace(call_action=action)
        ))
        stopped = []
        event = SimpleNamespace(
            get_platform_id=lambda: "napcat",
            get_sender_id=lambda: module.OWNER_QQ,
            get_self_id=lambda: "test-bot",
            is_private_chat=lambda: True,
            message_str="把你的签名改成「主人的专属小肥鱼」",
            stop_event=lambda: stopped.append(True),
            plain_result=lambda text: text,
        )
        replies = [r async for r in plugin.handle_signature_message(event)]
        self.assertEqual(state["signature"], "主人的专属小肥鱼")
        self.assertTrue(stopped)
        self.assertIn("已核验", "".join(replies))

    async def test_live_account_state_overrides_conflicting_chat_history(self):
        async def action(name, **params):
            if name == "get_stranger_info":
                return {"long_nick": ""}
            raise ValueError(name)

        plugin = object.__new__(module.Main)
        plugin.context = SimpleNamespace(get_platform_inst=lambda _: SimpleNamespace(
            bot=SimpleNamespace(call_action=action)
        ))
        event = SimpleNamespace(
            get_platform_id=lambda: "napcat",
            get_sender_id=lambda: module.OWNER_QQ,
            get_self_id=lambda: "test-bot",
            is_private_chat=lambda: True,
            message_str="你签名也没改",
        )
        req = SimpleNamespace(system_prompt="原有人设", func_tool=None)
        await plugin.inject_verified_account_state(event, req)
        self.assertIn("test-bot", req.system_prompt)
        self.assertIn("签名为空", req.system_prompt)
        self.assertIn("set_qq_signature", req.system_prompt)
        self.assertIn("不能", req.system_prompt)


if __name__ == "__main__":
    unittest.main()
