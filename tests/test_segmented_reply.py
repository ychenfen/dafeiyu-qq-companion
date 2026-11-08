"""Exercise AstrBot's real decorate/respond stages with the current config."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageEventResult, ResultContentType
from astrbot.core.pipeline.result_decorate.stage import ResultDecorateStage
from astrbot.core.pipeline.respond.stage import RespondStage
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent


class SegmentedReplyTests(unittest.IsolatedAsyncioTestCase):
    async def deliver(self, text):
        with open("/AstrBot/data/cmd_config.json", encoding="utf-8-sig") as source:
            config = json.load(source)
        context = SimpleNamespace(
            astrbot_config=config,
            plugin_manager=SimpleNamespace(context=SimpleNamespace(
                get_using_tts_provider_async=AsyncMock(return_value=None),
            )),
        )
        message = AstrBotMessage()
        message.type = MessageType.FRIEND_MESSAGE
        message.self_id = "test-bot"
        message.sender = MessageMember("test-owner", "test-owner")
        message.message = [Plain("test")]
        message.message_str = "test"
        message.message_id = "test-id"
        event = AiocqhttpMessageEvent(
            "test", message, PlatformMetadata("aiocqhttp", "test", "napcat"),
            "test-owner", None,
        )
        result = MessageEventResult().message(text)
        result.result_content_type = ResultContentType.LLM_RESULT
        event.set_result(result)
        sent = []

        async def send(chain):
            sent.append("".join(c.text for c in chain.chain if isinstance(c, Plain)))

        event.send = send
        decorate = ResultDecorateStage()
        respond = RespondStage()
        await decorate.initialize(context)
        await respond.initialize(context)
        async for _ in decorate.process(event):
            pass
        with patch("astrbot.core.pipeline.respond.stage.asyncio.sleep", new=AsyncMock()):
            await respond.process(event)
        return sent

    async def test_each_line_becomes_a_separate_message(self):
        self.assertEqual(await self.deliver("在\n又熬夜？\n快去睡"), ["在", "又熬夜？", "快去睡"])

    async def test_sentences_in_one_line_are_also_separated(self):
        self.assertEqual(await self.deliver("在呢。怎么啦？今天好点了吗"), ["在呢。", "怎么啦？", "今天好点了吗"])


if __name__ == "__main__":
    unittest.main()
