"""Live, opt-in: repair the requested signature using existing text history.

Unlike verify_live_signature.py, this deliberately KEEPS the requested signature.
Short-lived NapCat credential is supplied through stdin only.
"""

import asyncio
import importlib.util
import json
import sqlite3
import sys
from types import SimpleNamespace

from astrbot.api.event import filter
from astrbot.core.agent.tool import ToolSet
from astrbot.core.provider.entities import ProviderRequest
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial

from verify_live_signature import LiveQQ, post


async def main(credential):
    adapter = await asyncio.to_thread(post, "Debug/create", {}, credential)
    providers = []
    try:
        spec = importlib.util.spec_from_file_location(
            "dafeiyu_history_check", "/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bot = LiveQQ(credential)
        account = await bot.call_action("get_login_info")
        plugin = object.__new__(module.Main)
        plugin.context = SimpleNamespace(get_platform_inst=lambda _: SimpleNamespace(bot=bot))
        event = SimpleNamespace(
            get_platform_id=lambda: "napcat",
            get_sender_id=lambda: module.OWNER_QQ,
            get_self_id=lambda: str(account["user_id"]),
            is_private_chat=lambda: True,
            message_str="你签名也没改",
        )
        with open("/AstrBot/data/cmd_config.json", encoding="utf-8-sig") as source:
            config = json.load(source)
        with sqlite3.connect("/AstrBot/data/data_v4.db") as db:
            persona = db.execute(
                "select system_prompt from personas where persona_id=?", (module.PERSONA_ID,)
            ).fetchone()[0]
            stored = db.execute(
                "select content from conversations order by updated_at desc limit 1"
            ).fetchone()[0]
        # Retain all real text turns without resending private image data.
        history = []
        for message in json.loads(stored):
            if message.get("role") not in ("user", "assistant"):
                continue
            content = message.get("content", "")
            if isinstance(content, list):
                content = "\n".join(p.get("text", "[图片略]") for p in content if isinstance(p, dict))
            if content:
                history.append({"role": message["role"], "content": content})
        tools = ToolSet([filter.llm_tool.__globals__["llm_tools"].get_func("set_qq_signature")])
        target = "主人的专属小肥鱼"
        initial = await bot.call_action("get_stranger_info", user_id=str(account["user_id"]), no_cache=True)
        needs_write = initial["long_nick"] != target
        # A missing target must cause an actual write. If already correct, the
        # model may truthfully report the verified current state instead.
        for index, item in enumerate(p for p in config["provider"] if p.get("enable")):
            source = next(s for s in config["provider_sources"] if s["id"] == item["provider_source_id"])
            provider = ProviderOpenAIOfficial({**source, **item}, config["provider_settings"])
            providers.append(provider)
            req = ProviderRequest(prompt=event.message_str, system_prompt=persona, contexts=history, func_tool=tools)
            await plugin.inject_verified_account_state(event, req)
            response = await provider.text_chat(
                prompt=req.prompt, contexts=req.contexts, system_prompt=req.system_prompt,
                func_tool=req.func_tool, request_max_retries=1,
            )
            if index == 0 and needs_write:
                assert response.tools_call_name == ["set_qq_signature"], "History-based complaint did not call the tool"
            if response.tools_call_name:
                assert response.tools_call_name == ["set_qq_signature"]
                assert response.tools_call_args[0]["signature"] == target
                result = await plugin.set_qq_signature(event, **response.tools_call_args[0])
                assert "已核验" in result, result
                print(item["id"], "existing history -> registered signature tool -> QQ readback: PASS")
            else:
                assert target in response.completion_text, "Response ignored the current verified signature"
                print(item["id"], "existing history -> verified current signature: PASS")
        profile = await bot.call_action("get_stranger_info", user_id=str(account["user_id"]), no_cache=True)
        assert profile["long_nick"] == target
        print("RETAINED verified signature:", profile["long_nick"])
    finally:
        for provider in providers:
            await provider.terminate()
        await asyncio.to_thread(post, "Debug/close/" + adapter["adapterName"], {}, credential)


if __name__ == "__main__":
    asyncio.run(main(json.load(sys.stdin)["credential"]))
