"""Live model checks using temporary, synthetic memories. No QQ messages sent."""

import asyncio
import importlib.util
import json
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
from astrbot.api.event import filter
from astrbot.core.agent.tool import ToolSet


async def main():
    spec = importlib.util.spec_from_file_location("dafeiyu_companion_check", "/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with open("/AstrBot/data/cmd_config.json", encoding="utf-8-sig") as source:
        config = json.load(source)
    item = next(p for p in config["provider"] if p.get("enable"))
    source = next(p for p in config["provider_sources"] if p["id"] == item["provider_source_id"])
    provider = ProviderOpenAIOfficial({**source, **item}, config["provider_settings"])
    try:
        with tempfile.TemporaryDirectory() as temp:
            plugin = object.__new__(module.Main)
            path = Path(temp) / "synthetic-memory.db"
            plugin.state = module.CompanionStore(path)

            async def command(text):
                event = SimpleNamespace(
                    get_platform_id=lambda: "napcat", get_sender_id=lambda: module.OWNER_QQ,
                    is_private_chat=lambda: True, message_str=text,
                    stop_event=lambda: None, plain_result=lambda text: text,
                )
                return [r async for r in plugin.handle_companion_commands(event)]

            await command("记住 饮料=不喝咖啡")
            plugin.state = module.CompanionStore(path)
            response = await provider.text_chat(
                prompt="我不喝什么来着？", contexts=[],
                system_prompt=plugin._persona() + plugin._memory_prompt(), request_max_retries=1,
            )
            assert "咖啡" in response.completion_text, "Persisted explicit fact was not recalled"
            print("Live model: persisted fact recall PASS")

            await command("记住 饮料=喜欢红茶")
            response = await provider.text_chat(
                prompt="我喜欢喝什么？", contexts=[],
                system_prompt=plugin._persona() + plugin._memory_prompt(), request_max_retries=1,
            )
            assert "红茶" in response.completion_text and "咖啡" not in response.completion_text
            print("Live model: corrected fact replaces old value PASS")
            forget_text = "把饮料这条记忆忘记"
            response = await provider.text_chat(
                prompt=forget_text, contexts=[], system_prompt=plugin._persona() + plugin._memory_prompt(),
                func_tool=ToolSet([filter.llm_tool.__globals__["llm_tools"].get_func("forget_owner_fact")]),
                request_max_retries=1,
            )
            assert response.tools_call_name == ["forget_owner_fact"], "Explicit forgetting was only a spoken promise"
            event = SimpleNamespace(
                get_platform_id=lambda: "napcat", get_sender_id=lambda: module.OWNER_QQ,
                is_private_chat=lambda: True, message_str=forget_text,
            )
            result = await plugin.forget_owner_fact(event, **response.tools_call_args[0])
            assert "已删除" in result
            assert not plugin.state.facts() and "红茶" not in plugin._memory_prompt()
            print("Live model: explicit forgetting invokes real deletion and removes retrieval PASS")

            sent = []

            async def isolated_send(_, chain):
                sent.append("".join(c.text for c in chain.chain))
                return True

            plugin.context = SimpleNamespace(
                get_using_provider=lambda _: provider, send_message=isolated_send,
                conversation_manager=SimpleNamespace(
                    get_curr_conversation_id=AsyncMock(return_value="synthetic-session"),
                    get_conversation=AsyncMock(return_value=SimpleNamespace(history=[
                        {"role": "user", "content": "我今天跑了五公里，腿好酸"},
                        {"role": "assistant", "content": "跑完歇歇"},
                    ])),
                ),
            )
            result = await plugin._proactive(force=True)
            assert re.search("跑|腿|酸|歇|休息|五公里|走", result), "Proactive reply ignored the recent topic"
            assert sent and all("\n" not in part for part in sent)
            print("Live model: proactive message follows recent topic and splits delivery PASS")
            print("Synthetic memories discarded; no real QQ messages sent")
    finally:
        await provider.terminate()


if __name__ == "__main__":
    asyncio.run(main())
