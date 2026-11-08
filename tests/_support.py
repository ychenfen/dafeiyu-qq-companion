"""Shared test loader that works both inside /AstrBot container and in local checkout."""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINER_PLUGIN = Path("/AstrBot/data/plugins/astrbot_plugin_dafeiyu/main.py")
LOCAL_PLUGIN = REPO_ROOT / "plugin" / "main.py"


def _ensure_astrbot_stubs() -> None:
    """Install lightweight module stubs when running outside the AstrBot Docker container."""
    try:
        import aiocqhttp.exceptions  # noqa: F401
    except ImportError:
        aiocq = ModuleType("aiocqhttp")
        aiocq_exc = ModuleType("aiocqhttp.exceptions")

        class ApiNotAvailable(Exception):
            pass

        aiocq_exc.ApiNotAvailable = ApiNotAvailable
        aiocq.exceptions = aiocq_exc
        sys.modules["aiocqhttp"] = aiocq
        sys.modules["aiocqhttp.exceptions"] = aiocq_exc

    try:
        import astrbot.api  # noqa: F401
    except ImportError:
        def _passthrough_decorator(*_args, **_kwargs):
            def _wrap(fn):
                return fn
            return _wrap

        filter_ns = SimpleNamespace(
            EventMessageType=SimpleNamespace(PRIVATE_MESSAGE="PRIVATE_MESSAGE"),
            event_message_type=_passthrough_decorator,
            regex=_passthrough_decorator,
            llm_tool=_passthrough_decorator,
            on_llm_request=_passthrough_decorator,
            command=_passthrough_decorator,
        )

        class Star:
            def __init__(self, context=None):
                self.context = context

        @dataclass
        class Plain:
            text: str

        @dataclass
        class MessageChain:
            chain: list

        astrbot_mod = ModuleType("astrbot")
        api_mod = ModuleType("astrbot.api")
        api_mod.logger = logging.getLogger("dafeiyu_test")
        event_mod = ModuleType("astrbot.api.event")
        event_mod.AstrMessageEvent = object
        event_mod.filter = filter_ns
        provider_mod = ModuleType("astrbot.api.provider")
        provider_mod.ProviderRequest = object
        star_mod = ModuleType("astrbot.api.star")
        star_mod.Context = object
        star_mod.Star = Star
        core_mod = ModuleType("astrbot.core")
        msg_mod = ModuleType("astrbot.core.message")
        comp_mod = ModuleType("astrbot.core.message.components")
        comp_mod.Plain = Plain
        res_mod = ModuleType("astrbot.core.message.message_event_result")
        res_mod.MessageChain = MessageChain

        for name, mod in {
            "astrbot": astrbot_mod,
            "astrbot.api": api_mod,
            "astrbot.api.event": event_mod,
            "astrbot.api.provider": provider_mod,
            "astrbot.api.star": star_mod,
            "astrbot.core": core_mod,
            "astrbot.core.message": msg_mod,
            "astrbot.core.message.components": comp_mod,
            "astrbot.core.message.message_event_result": res_mod,
        }.items():
            sys.modules[name] = mod


def load_plugin_module(module_name: str = "dafeiyu_plugin_test_target"):
    _ensure_astrbot_stubs()
    target = CONTAINER_PLUGIN if CONTAINER_PLUGIN.exists() else LOCAL_PLUGIN
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not module.PACK_DIR.exists():
        module.PACK_DIR = REPO_ROOT / "packs"
    return module
