"""Opt-in live check: temporary QQ signature, then restore the original.

Run in AstrBot's container. Receive a short-lived NapCat WebUI credential
through stdin; never write it to disk or print it. No chat messages are sent.
"""

import asyncio
import importlib.util
import json
import sqlite3
import sys
import urllib.request
from types import SimpleNamespace

from astrbot import logger
from astrbot.core.agent.runners.tool_loop_agent_runner import ToolLoopAgentRunner
from astrbot.core.agent.tool import FunctionTool, ToolSet
from astrbot.core.provider.entities import ProviderRequest
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial


def post(path, payload, credential):
    request = urllib.request.Request(
        "http://napcat:6099/api/" + path,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + credential,
        },
    )
    response = json.load(urllib.request.urlopen(request, timeout=20))
    if response.get("code") != 0:
        raise RuntimeError("NapCat WebUI request failed")
    return response.get("data")


class LiveQQ:
    def __init__(self, credential):
        self.credential = credential

    async def call_action(self, name, **params):
        response = await asyncio.to_thread(
            post, "Debug/call", {"action": name, "params": params}, self.credential
        )
        if response.get("status") != "ok" or response.get("retcode") != 0:
            raise RuntimeError("OneBot action failed: " + name)
        return response.get("data")


async def main(credential):
    logger.setLevel("INFO")
    spec = importlib.util.spec_from_file_location(
        "dafeiyu_live_check", "/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bot = LiveQQ(credential)
    plugin = object.__new__(module.Main)
    plugin.context = SimpleNamespace(
        get_platform_inst=lambda _: SimpleNamespace(bot=bot)
    )
    providers = []
    original = None
    self_id = None
    adapter_name = None
    try:
        adapter = await asyncio.to_thread(post, "Debug/create", {}, credential)
        adapter_name = adapter["adapterName"]
        info = await bot.call_action("get_login_info")
        self_id = str(info["user_id"])
        profile = await bot.call_action(
            "get_stranger_info", user_id=self_id, no_cache=True
        )
        original = profile["long_nick"]
        event = SimpleNamespace(
            get_platform_id=lambda: "napcat",
            get_sender_id=lambda: module.OWNER_QQ,
            get_self_id=lambda: self_id,
        )
        config = json.load(open("/AstrBot/data/cmd_config.json", encoding="utf-8-sig"))
        with sqlite3.connect("/AstrBot/data/data_v4.db") as db:
            persona = db.execute(
                "select system_prompt from personas where persona_id=?", (module.PERSONA_ID,)
            ).fetchone()[0]
        tools = ToolSet([FunctionTool(
            name="set_qq_signature",
            description="修改自己的 QQ 个性签名。主人叫你改签名时必须调用，不能口头假装成功。",
            parameters={
                "type": "object",
                "properties": {"signature": {"type": "string"}},
                "required": ["signature"],
            },
        )])
        target = "小鲸鱼今天也在摸鱼"
        for item in config["provider"]:
            if not item.get("enable"):
                continue
            source = next(s for s in config["provider_sources"] if s["id"] == item["provider_source_id"])
            provider = ProviderOpenAIOfficial({**source, **item}, config["provider_settings"])
            providers.append(provider)
            runner = object.__new__(ToolLoopAgentRunner)
            runner.provider = provider
            runner.req = ProviderRequest(func_tool=tools)
            passed_tools = runner._func_tool_for_provider()
            assert passed_tools is not None, "AstrBot removed tools"
            response = await provider.text_chat(
                prompt=f"把你的QQ签名改成「{target}」",
                system_prompt=persona,
                contexts=[],
                func_tool=passed_tools,
                request_max_retries=1,
            )
            assert response.tools_call_name == ["set_qq_signature"], "Model did not call the signature tool"
            arguments = response.tools_call_args[0]
            assert arguments.get("signature") == target, "Model changed the requested signature"
            result = await plugin.set_qq_signature(event, **arguments)
            assert "已核验" in result, result
            actual = await bot.call_action("get_stranger_info", user_id=self_id, no_cache=True)
            assert actual["long_nick"] == target, "QQ readback differs"
            print(item["id"], "model tool call -> plugin -> QQ readback: PASS")
    finally:
        try:
            if original is not None and self_id is not None:
                await bot.call_action("set_self_longnick", longNick=original)
                restored = False
                for _ in range(5):
                    profile = await bot.call_action("get_stranger_info", user_id=self_id, no_cache=True)
                    if profile["long_nick"] == original:
                        restored = True
                        break
                    await asyncio.sleep(1)
                assert restored, "Original signature restoration was not verified"
                print("Original QQ signature restored and verified: PASS")
        finally:
            for provider in providers:
                await provider.terminate()
            if adapter_name:
                await asyncio.to_thread(post, "Debug/close/" + adapter_name, {}, credential)


if __name__ == "__main__":
    credential = json.load(sys.stdin)["credential"]
    asyncio.run(main(credential))
