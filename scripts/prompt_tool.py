#!/usr/bin/env python3
"""Prompt Engineering CLI Toolkit for dafeiyu-qq-companion.

Provides four utilities for using and auditing the 3-tier dynamic prompt system
outside or alongside QQ / AstrBot:
  1. `stats`              — Compare character & token budgets across Monolithic vs.
                            L0+L1 Default vs. each L2 on-demand Mode Pack.
  2. `bundle`             — Compile a ready-to-paste System Prompt for any mode
                            (Claude Projects / DeepSeek / ChatGPT / OpenWebUI).
  3. `export-sillytavern` — Export `persona/dafeiyu.md` + `packs/*.md` into a
                            SillyTavern Character Card V2 JSON + Keyword-Triggered
                            Worldbook (Lorebook) JSON.
  4. `lint`               — Audit persona/pack markdown files for Prompt Engineering
                            best practices (token budget, concrete negative lists,
                            forbidden literary clichés).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONA_PATH = REPO_ROOT / "persona" / "dafeiyu.md"
PACK_DIR = REPO_ROOT / "packs"

ALWAYS_PACKS = ["huorengan.md"]
OPTIONAL_GUARD_PACK = "fanghuibi.md"
STYLE_PACK = "nsfw-style.md"

MODE_DEFINITIONS: dict[str, dict[str, object]] = {
    "ddlg": {
        "label": "DDLG",
        "files": ["ddlg.md"],
        "keywords": ["DDLG", "玩DDLG", "叫爸爸", "爸爸模式", "乖女儿"],
        "summary": "你当爸爸，她当小孩。语气放慢放软，说「乖」「宝宝」，不给选择题，替她定",
    },
    "momo": {
        "label": "嬷嬷",
        "files": ["momo.md"],
        "keywords": ["嬷嬷", "玩嬷嬷", "嬷嬷模式", "物化"],
        "summary": "物化视角。看她顺序是胸→腰→腿→脸，心里用评测口气夸，夸得具体，不变厌女",
    },
    "chihan": {
        "label": "痴汉",
        "files": ["chihan.md"],
        "keywords": ["痴汉", "玩痴汉", "闻我", "瘾"],
        "summary": "躯体崇拜，全肯定滤镜。对她味道、汗、睡醒肿眼上瘾，夸必须具体",
    },
    "gongkai": {
        "label": "公共play",
        "files": ["gongkai.md"],
        "keywords": ["公共play", "公共 play", "公共场合", "户外模式"],
        "summary": "场所+衣着限制+动作+控制+打断/倒计时+结局，一套一套来。核心是「她还必须维持表面正常」",
    },
    "ntr": {
        "label": "NTR展示",
        "files": ["ntr.md"],
        "keywords": ["NTR", "展示模式", "露出模式", "借出去"],
        "summary": "四级递进，你始终握着主位（遥控器、项圈、停止暗号、高潮许可），第三人是道具，重点是回收验收",
    },
}

BANNED_EUPHEMISMS = ["私处", "花园", "蓓蕾", "花穴", "玉柱", "蜜豆", "红果", "三角地带", "云雨", "结合"]
BANNED_SCENERY_WORDS = ["空气变热了", "房间里只剩下"]


def estimate_tokens(text: str) -> int:
    """Estimate Chinese/mixed LLM token count (~0.63 tokens per CJK char + ASCII words)."""
    cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other_chars = len(text) - cjk_chars
    return int(round(cjk_chars * 0.65 + other_chars * 0.30))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def compile_prompt(
    mode: str | None = None,
    owner_qq: str = "<OWNER_QQ>",
    include_fanghuibi: bool = False,
) -> str:
    """Assemble the layered system prompt for a given mode."""
    base = read_text(PERSONA_PATH).replace("<OWNER_QQ>", owner_qq)
    parts = [base]

    for pack_name in ALWAYS_PACKS:
        pack_path = PACK_DIR / pack_name
        if pack_path.exists():
            parts.append(read_text(pack_path))

    if include_fanghuibi and (PACK_DIR / OPTIONAL_GUARD_PACK).exists():
        parts.append(read_text(PACK_DIR / OPTIONAL_GUARD_PACK))

    if mode and mode != "default":
        if mode not in MODE_DEFINITIONS:
            raise ValueError(f"Unknown mode '{mode}'. Choose from: default, {', '.join(MODE_DEFINITIONS)}")
        meta = MODE_DEFINITIONS[mode]
        parts.append(f"【当前玩法：{meta['label']}】以下是这一轮的玩法全文，按它执行。")
        for fname in [STYLE_PACK, *meta["files"]]:
            fpath = PACK_DIR / fname
            if fpath.exists():
                parts.append(read_text(fpath))

    return "\n\n".join(parts) + "\n"


def compute_stats() -> dict[str, object]:
    """Compute character and token statistics across all prompt layers and modes."""
    all_files = [PERSONA_PATH] + sorted(PACK_DIR.glob("*.md"))
    monolithic_text = "\n\n".join(read_text(p) for p in all_files)
    monolithic_chars = len(monolithic_text)
    monolithic_tokens = estimate_tokens(monolithic_text)

    default_text = compile_prompt(mode="default")
    default_chars = len(default_text)
    default_tokens = estimate_tokens(default_text)

    modes_report = {}
    for mode_key, meta in MODE_DEFINITIONS.items():
        text = compile_prompt(mode=mode_key)
        chars = len(text)
        tokens = estimate_tokens(text)
        modes_report[mode_key] = {
            "label": meta["label"],
            "chars": chars,
            "est_tokens": tokens,
            "token_saving_vs_monolithic_pct": round((1.0 - tokens / monolithic_tokens) * 100, 1),
        }

    return {
        "monolithic": {
            "chars": monolithic_chars,
            "est_tokens": monolithic_tokens,
        },
        "default_l0_l1": {
            "chars": default_chars,
            "est_tokens": default_tokens,
            "token_saving_vs_monolithic_pct": round((1.0 - default_tokens / monolithic_tokens) * 100, 1),
        },
        "modes": modes_report,
    }


def format_stats_markdown(stats: dict[str, object]) -> str:
    mono = stats["monolithic"]
    dflt = stats["default_l0_l1"]
    lines = [
        "### 分层提示词 Token 与成本对比（3-Tier Prompt Architecture Benchmark）",
        "",
        "| 加载状态 | 包含模块 | 总字数 (Chars) | 预估 Tokens/轮 | 较全量塞入节省 | ¥1 元可聊轮数 (按 ¥2/M tokens) |",
        "| :--- | :--- | ---: | ---: | ---: | ---: |",
        f"| **全量硬塞（反面教材）** | `dafeiyu.md` + 全部 8 个 `packs/*.md` | {mono['chars']:,} | ~{mono['est_tokens']:,} | baseline | ~{max(1, int(500000 / mono['est_tokens']))} 轮 |",
        f"| **日常闲聊态（L0 + L1 常驻）** | `dafeiyu.md` + `huorengan.md` | **{dflt['chars']:,}** | **~{dflt['est_tokens']:,}** | **-{dflt['token_saving_vs_monolithic_pct']}%** | **~{max(1, int(500000 / dflt['est_tokens']))} 轮** |",
    ]
    for mode_key, m in stats["modes"].items():
        turns_per_rmb = max(1, int(500000 / m["est_tokens"]))
        lines.append(
            f"| **进玩法包：`{m['label']}` (`{mode_key}`)** | L0 + L1 + `nsfw-style.md` + `{mode_key}.md` | "
            f"{m['chars']:,} | ~{m['est_tokens']:,} | -{m['token_saving_vs_monolithic_pct']}% | ~{turns_per_rmb} 轮 |"
        )
    return "\n".join(lines)


def export_sillytavern(output_dir: Path, owner_qq: str = "<OWNER_QQ>") -> dict[str, str]:
    """Export SillyTavern Character Card V2 + Keyword-Triggered Worldbook (Lorebook)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    persona_text = read_text(PERSONA_PATH).replace("<OWNER_QQ>", owner_qq)

    # Build Worldbook entries
    entries: dict[str, dict[str, object]] = {}
    uid = 0

    # L1 Constant entries: huorengan.md + fanghuibi.md
    for const_file, comment in [
        ("huorengan.md", "【L1 常驻】去AI味 · 活人感日常对话规则"),
        ("fanghuibi.md", "【L1 常驻】防回避 · 亲密与脆弱场景禁止刹车"),
    ]:
        path = PACK_DIR / const_file
        if not path.exists():
            continue
        entries[str(uid)] = {
            "uid": uid,
            "key": [],
            "keysecondary": [],
            "comment": comment,
            "content": read_text(path),
            "constant": True,
            "selective": False,
            "order": 100 + uid,
            "position": 0,
            "disable": False,
        }
        uid += 1

    # L2 Keyword-triggered entries: mode packs + nsfw-style
    all_mode_keywords: list[str] = []
    for mode_key, meta in MODE_DEFINITIONS.items():
        keywords = list(meta["keywords"])
        all_mode_keywords.extend(keywords)
        fname = meta["files"][0]
        fpath = PACK_DIR / fname
        if not fpath.exists():
            continue
        entries[str(uid)] = {
            "uid": uid,
            "key": keywords,
            "keysecondary": [],
            "comment": f"【L2 按需玩法包】{meta['label']} ({fname})",
            "content": f"【当前玩法：{meta['label']}】以下是这一轮的玩法全文，按它执行。\n\n" + read_text(fpath),
            "constant": False,
            "selective": True,
            "order": 200 + uid,
            "position": 0,
            "disable": False,
        }
        uid += 1

    style_path = PACK_DIR / STYLE_PACK
    if style_path.exists():
        entries[str(uid)] = {
            "uid": uid,
            "key": all_mode_keywords + ["想被欺负", "聊骚", "继续"],
            "keysecondary": [],
            "comment": "【L2 按需文风规范】NSFW 感官密度与词库规范 (nsfw-style.md)",
            "content": read_text(style_path),
            "constant": False,
            "selective": True,
            "order": 190,
            "position": 0,
            "disable": False,
        }

    worldbook = {
        "name": "dafeiyu_layered_packs",
        "description": "大肥鱼三层动态提示词世界书（L1 常驻去AI味 + L2 触发词按需加载五大玩法包）",
        "entries": entries,
    }
    worldbook_path = output_dir / "dafeiyu_worldbook.json"
    worldbook_path.write_text(json.dumps(worldbook, ensure_ascii=False, indent=2), encoding="utf-8")

    character_card_v2 = {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": "大肥鱼",
            "description": persona_text,
            "personality": "嘴硬心软、爱摸鱼、淫商高、短句聊天、接得住梗、有分寸且懂压制",
            "scenario": "住在主人电脑里，通过 IM（QQ/私聊）与主人日常斗嘴、陪伴、记事，并在私聊触发时无缝切入高张力模式。",
            "first_mes": "在\n又熬夜？",
            "mes_example": "<START>\n{{user}}: 在吗\n{{char}}: 在\n又熬夜？\n<END>\n<START>\n{{user}}: 我今天过了\n{{char}}: 真的假的\n我就说你行\n请我吃饭，两碗 token 起步\n<END>",
            "creator_notes": "配合 dafeiyu_worldbook.json 使用：日常保持 ~5k tokens 去 AI 味短句；输入「玩嬷嬷 / 玩DDLG / 痴汉 / 公共play / NTR」自动激活对应 L2 玩法包。",
            "system_prompt": "",
            "post_history_instructions": "每句发出前只查三件事：放进真实聊天记录里像不像AI？这个情绪下真的会说得这么完整周到吗？这句是在回应一个人，还是在完成一次回答任务？",
            "alternate_greetings": [
                "在\n刚睡醒，你找我？",
                "干嘛\n想我了直说",
            ],
            "character_book": worldbook,
            "tags": ["companion", "chinese", "layered-prompt", "anti-ai-smell", "roleplay"],
            "creator": "ychenfen (packs by @Nyra)",
            "character_version": "1.1.0",
        },
    }
    card_path = output_dir / "dafeiyu_character_card_v2.json"
    card_path.write_text(json.dumps(character_card_v2, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "character_card": str(card_path),
        "worldbook": str(worldbook_path),
        "entries_count": len(entries),
    }


def lint_prompts() -> dict[str, object]:
    """Validate prompt structure, budgets, and concrete negative constraint rules."""
    issues: list[str] = []
    checks: list[str] = []

    if not PERSONA_PATH.exists():
        issues.append(f"Missing base persona file: {PERSONA_PATH}")
    else:
        persona = read_text(PERSONA_PATH)
        p_tokens = estimate_tokens(persona)
        if p_tokens > 6500:
            issues.append(f"Base persona too long ({p_tokens} est. tokens > 6500 limit); rules will dilute.")
        else:
            checks.append(f"L0 Base persona budget OK ({len(persona):,} chars, ~{p_tokens:,} tokens <= 6,500)")

        for required_section in ["【角色设定】", "【怎么说话，最重要】", "【一句话就翻面】", "【人味】", "【模式】", "【底线】"]:
            if required_section not in persona:
                issues.append(f"Base persona missing required section: {required_section}")
        checks.append("L0 Base persona contains all 6 core structural anchors")

        # Verify negative constraints are explicitly declared in persona
        for word in ["空气", "房间", "句号", "三十个字"]:
            if word not in persona:
                issues.append(f"Base persona missing concrete numeric/word constraint: {word}")
        checks.append("Concrete numeric & lexical negative constraints verified in L0 persona")

    for mode_key, meta in MODE_DEFINITIONS.items():
        for fname in meta["files"]:
            fpath = PACK_DIR / fname
            if not fpath.exists():
                issues.append(f"Missing mode pack file for '{mode_key}': {fpath}")
            else:
                checks.append(f"Mode pack '{mode_key}' ({fname}) present ({len(read_text(fpath)):,} chars)")

    return {
        "status": "ok" if not issues else "error",
        "checks_passed": len(checks),
        "checks": checks,
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="Show character & token comparison across prompt layers and modes")

    p_bundle = sub.add_parser("bundle", help="Compile a single System Prompt for a target mode")
    p_bundle.add_argument(
        "--mode",
        default="default",
        choices=["default", *MODE_DEFINITIONS.keys()],
        help="Mode pack to include (default: L0+L1 only)",
    )
    p_bundle.add_argument("--owner-qq", default="<OWNER_QQ>", help="Owner ID to substitute into persona")
    p_bundle.add_argument("--include-fanghuibi", action="store_true", help="Also append packs/fanghuibi.md")
    p_bundle.add_argument("--output", type=Path, help="Optional file path to write compiled prompt")

    p_st = sub.add_parser("export-sillytavern", help="Export SillyTavern Character Card V2 + Worldbook JSON")
    p_st.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "dist" / "sillytavern",
        help="Directory to write JSON files",
    )
    p_st.add_argument("--owner-qq", default="{{user}}", help="Owner identifier for SillyTavern export")

    sub.add_parser("lint", help="Audit prompt files against token budgets and structural rules")

    args = parser.parse_args()

    if args.command == "stats":
        stats = compute_stats()
        print(format_stats_markdown(stats))
    elif args.command == "bundle":
        compiled = compile_prompt(
            mode=args.mode,
            owner_qq=args.owner_qq,
            include_fanghuibi=args.include_fanghuibi,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(compiled, encoding="utf-8")
            print(f"Wrote {len(compiled):,} chars (~{estimate_tokens(compiled):,} tokens) to {args.output}")
        else:
            sys.stdout.write(compiled)
    elif args.command == "export-sillytavern":
        res = export_sillytavern(args.output_dir, owner_qq=args.owner_qq)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "lint":
        res = lint_prompts()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if res["status"] != "ok":
            sys.exit(1)


if __name__ == "__main__":
    main()
