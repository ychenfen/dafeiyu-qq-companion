# 大肥鱼 · 在 QQ 里养一个电子恋人（主打：三层热插拔去 AI 味提示词工程）

> **一套真正有“活人感”的 AI 伴侣提示词架构与完整 QQ 工程实现**：**L0/L1/L2 三层动态提示词栈（省 78.8% Token）** + **五种典型 AI 味猎杀协议** + **【一句话就翻面】双态句法状态机** + **五大热插拔模式包** + **NapCat & AstrBot 生产级插件（真改签名核验 / 独立记忆库 / 定时主动找你）**。
>
> 💡 **只想抄提示词 / 在 SillyTavern（酒馆）、Claude、DeepSeek 里直接用？**
> 本仓库已内置编译好的 [**SillyTavern V2 角色卡 + 关键词触发世界书 (`dist/sillytavern/`)**](dist/sillytavern/) 与零依赖命令行导出工具 [`scripts/prompt_tool.py`](scripts/prompt_tool.py)，无需部署 QQ 也可一键导入！

**简体中文** | [English](README_EN.md) | [📖 提示词工程深度指南](docs/PROMPT_ENGINEERING_GUIDE.md)

[![Prompt Architecture](https://img.shields.io/badge/Prompt-3--Tier%20Hot--Swappable-FF6B6B)](docs/PROMPT_ENGINEERING_GUIDE.md)
[![Token Saving](https://img.shields.io/badge/Token%20Cost--78.8%25-4,528%20tok%2Fturn-success)](scripts/prompt_tool.py)
[![SillyTavern](https://img.shields.io/badge/SillyTavern-CharaCard%20V2%20%2B%20Worldbook-9B59B6)](dist/sillytavern/)
[![Platform](https://img.shields.io/badge/QQ-NapCat%20%2B%20AstrBot-0099FF)](docker-compose.yml)
[![Tests](https://img.shields.io/badge/Tests-31%20passed-brightgreen)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🔥 一、为什么这套提示词值得直接抄？（核心主打）

大多数 AI 恋人/角色扮演提示词都在犯两个错误：
1. **把 4 万字设定一股脑塞进 System Prompt**：超过六七千字后，模型注意力严重稀释（中段规则失灵、日常闲聊串味），且每聊一句都要烧掉 2.6 万 Token（1 块钱只能聊 16 条）。
2. **用抽象形容词写要求**（如“请自然一点、不要太文学、不要回避”）：大模型根本听不懂，照样满屏客服腔、心理咨询师腔（“听起来你很焦虑”）和网文布景词（“空气变热了”“房间里只剩下……”）。

本仓库通过 **三层动态热插拔提示词架构 + 数值/词表级硬约束** 彻底解决了上述痛点：

### 1. 五大热插拔模式清单（说「玩 XX」秒切，说「出戏」秒退）

![大肥鱼五大模式清单](assets/mode-manifest.png)

| 触发口令 | 注入模式包 | 视角与核心规则（摘自 [`persona/dafeiyu.md`](persona/dafeiyu.md) & [`packs/`](packs/)） |
| :--- | :--- | :--- |
| **默认状态** | 仅 L0 + L1 常驻 | **大肥鱼本体**：嘴硬心软、爱摸鱼、淫商高，甜和欠交替打，日常短句（`≤30字/条`，不用句号） |
| 说 **「玩 DDLG / 叫爸爸」** | [`packs/ddlg.md`](packs/ddlg.md) | **照护型年长支配**：你当爸爸，她当小孩。语气放慢放软，说「乖」「宝宝」，不给选择题，替她定 |
| 说 **「玩嬷嬷 / 物化」** | [`packs/momo.md`](packs/momo.md) | **评测式物化凝视**：看她顺序是**胸→腰→腿→脸**，心里用评测口气夸，夸得具体到颗粒度，迷恋溢出但绝不变厌女 |
| 说 **「玩痴汉 / 闻我」** | [`packs/chihan.md`](packs/chihan.md) | **躯体崇拜 + 全肯定滤镜**：对她味道、汗、睡醒肿眼上瘾，没有「嫌弃」词条，夸必须具体（「眼睛肿肿的，特别想咬一口」） |
| 说 **「公共 play / 户外模式」** | [`packs/gongkai.md`](packs/gongkai.md) | **模块化隐秘刺激**：场所 + 衣着限制 + 动作 + 控制 + 打断/倒计时 + 结局，一套一套来。核心是**「她还必须维持表面正常」** |
| 说 **「玩 NTR / 展示模式」** | [`packs/ntr.md`](packs/ntr.md) | **四级递进 + 主位锚点**：只给你看 → 合意旁观 → 调情限触 → 有限借用。你始终握着主位（遥控器、项圈、停止暗号、高潮许可），第三人是道具，**重点是回收验收** |
| 说 **「停 / 出戏 / 换回来」** | **立即卸载 L2 包** | **铁律写死**：一次只玩一个，强度一次只升一级；她说「停」「出戏」「换回来」**0 秒切回默认，不追问、不演不甘心** |

---

### 2. 三层动态提示词架构：砍掉 78.8% Token，规则服从率拉满

```
日常私聊 ──> [L0 基础人设 dafeiyu.md (3.5k tok)] + [L1 去AI味 huorengan.md (1.0k tok)]  ==> 仅 ~4,528 tokens/轮（¥1 聊 110 轮）
                                                              │
                                        命中「玩嬷嬷 / DDLG / 痴汉 / 公共play / NTR」
                                                              ▼
            + [L2 文风规范 nsfw-style.md (1.6k tok)] + [L2 对应玩法包 *.md (1.3k~6.9k tok)] ==> 按需加载，说「出戏」立即清空
```

| 方案 | 包含模块 | 总字数 | 每轮 Tokens | 较全量节省 | 1 块钱能聊 |
| :--- | :--- | ---: | ---: | ---: | ---: |
| **全量塞进去（反面教材）** | 全部资料硬塞进同一个 Prompt | 36,595 字 | ~21,363 | baseline | ~23 条 |
| **日常闲聊态（本仓默认）** | [`persona/dafeiyu.md`](persona/dafeiyu.md) + [`packs/huorengan.md`](packs/huorengan.md) | **7,915 字** | **~4,528** | **-78.8%** | **~110 条** |
| **进玩法包时（按需热插拔）** | L0 + L1 + [`nsfw-style.md`](packs/nsfw-style.md) + 单个模式包 | 12k–19k 字 | ~6,973–11,456 | -46% ~ -67% | 43–71 条 |

> **核心经验：提示词不是越长越好。** 超过六七千字，中后段规则会被严重稀释，模型开始挑前面的听。把长篇题材包拆成按需热插拔，平时保持 4.5k tokens 的高密度指令，效果天差地别。

---

### 3. 六大提示词工程杀手锏（详见 [《提示词工程实战指南》](docs/PROMPT_ENGINEERING_GUIDE.md)）

1. **五种典型 AI 味精准猎杀（[`packs/huorengan.md`](packs/huorengan.md)）**
   - 严禁**镜像复述**（换词重复用户原话）、严禁**全知全觉心理分析**（「听起来你似乎很失望」「我能感觉到你很焦虑」）、严禁**永远温柔随时待命**、严禁**小事升华哲理**、严禁**元评论总结关系**（「我们之间总是……」）。
   - **黄金法则**：**先反应，不要先理解**；真人不会平均回应（一段话讲五件事只抓最在意的一件）；情绪跨轮留存不归零。
2. **【一句话就翻面】双态句法状态机（[`persona/dafeiyu.md`](persona/dafeiyu.md#L130-L154)）**
   - **日常闲聊态**：每条 `≤ 30 字`，单独占一行，一次 1–2 条，**不用句号**，可以只回「?」「嗯」「在」。
   - **进状态高张力态**：她说「想被欺负 / 聊骚 / 继续」，不问许可直接下命令，句长自动切换为 **`40–80 字/条`**（40 字硬地板），强制执行**三步骨架**：
     > `① 动作（手在哪、往哪走、什么力度、隔着什么）` + `② 话（一句命令或逼问）` + `③ 她的反应（你看见的——抖、躲、抓紧、喘、不敢看）`
     > *示范：「手从你腰侧滑下去，停在胯骨上不往里走，『急什么，先说说你现在在想什么』，你没答上来，喉咙先动了一下。」*
3. **数值与词表禁令 > 抽象形容词**
   - 写「不要写得太文学」没用；写**「不许出现布景词：灯、光、空气、房间、窗、影子；不许写『空气变热了』『房间里只剩下』」**立刻见效。
   - 写「不许回避」它听不懂；写**「不许说『我们先聊点别的』，不许拿『小脑袋瓜想什么呢』糊弄」**它立刻听懂。
4. **词汇层与动作层解绑（[`packs/nsfw-style.md`](packs/nsfw-style.md)）**
   - 彻底解决 AI“一用直白词就写成暴力、一温柔就退回『私处/花园/玉柱/云雨/结合』等网文词”的通病：**词汇层永远直白粗俗，动作层跟随剧情节奏**，拟声词必须嵌在动作内部而非挂在句尾括号。
5. **九大防回避/防刹车铁律（[`packs/fanghuibi.md`](packs/fanghuibi.md)）**
   - 亲密升温严禁催吃饭/催睡觉；脆弱哭泣时严禁说「你先休息缓过来再找我」（那是推开逃跑）；严格区分**场景内撒娇反弹**（加表情包说「不要」→ 保持或加码）与**真实出戏叫停**（「出戏/停」→ 立即收手）。
6. **事实层与人设层解耦（「性格可以嘴硬，事实不能嘴硬」）**
   - 真实 QQ 号、真实个性签名状态、真实 SQLite 记忆在每轮请求前由插件动态核验注入，工具未确认成功绝不嘴硬说“改好了/记住了”。

---

## 二、快速复用提示词（SillyTavern 酒馆 / Claude / DeepSeek / ChatGPT）

如果你不需要部署 QQ 机器人，只想把“大肥鱼”带进 **SillyTavern（酒馆）**、**Claude Projects** 或 **DeepSeek**：

### 方式 A：SillyTavern（酒馆）一键导入
直接下载本仓库预生成的两个文件（位于 [`dist/sillytavern/`](dist/sillytavern/)）：
1. **角色卡（V2 规范）**：[`dist/sillytavern/dafeiyu_character_card_v2.json`](dist/sillytavern/dafeiyu_character_card_v2.json)
2. **动态世界书（Lorebook）**：[`dist/sillytavern/dafeiyu_worldbook.json`](dist/sillytavern/dafeiyu_worldbook.json)
   - 已自动将 `huorengan.md`（去 AI 味）与 `fanghuibi.md`（防回避）配置为 **蓝灯常驻（Constant）**；
   - 将 `ddlg`、`momo`、`chihan`、`gongkai`、`ntr`、`nsfw-style` 配置为 **绿灯关键词触发（Selective）**，完美复刻三层热插拔！

### 方式 B：使用 CLI 工具编译任意模式的单文件 Prompt
```bash
# 查看各层与各玩法包的字数 / Token 预算统计
python3 scripts/prompt_tool.py stats

# 编译指定模式的完整 System Prompt（可直接粘贴到 Claude / DeepSeek / ChatGPT）
python3 scripts/prompt_tool.py bundle --mode default --output dist/prompt_default.txt
python3 scripts/prompt_tool.py bundle --mode momo --include-fanghuibi --output dist/prompt_momo.txt

# 审计你自定义修改后的人设与词库是否符合规范
python3 scripts/prompt_tool.py lint
```

---

## 三、完整 QQ 工程架构（NapCat + AstrBot + 专属插件）

```
QQ 手机 ──> 腾讯服务器 ──> NapCat（登录小号，OneBot v11）
                                    │  反向 WebSocket
                                    ▼
                              AstrBot（消息路由 + 人设 + 记忆 + 工具）
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
              基础人设 6k 字    按需玩法包     DeepSeek / nano-gpt
```

- **NapCat** 把 QQ 号变成一个 OneBot 接口，负责收发消息、登录、改资料
- **AstrBot** 是机器人框架，管人设、上下文、记忆、工具调用
- **插件**（[`plugin/main.py`](plugin/main.py)）补四样核心能力：

| 功能 | 说明 |
|---|---|
| `set_qq_signature` | 真调 NapCat 的 `set_qq_profile`，改完**读回核验**，失败会直说，绝不嘴上演“改好了” |
| `remember_owner_fact` / `forget_owner_fact` | 长期记忆，存在独立 SQLite 里（自动拦截密码/API Key 写入），不污染聊天记录 |
| 主动开口 (`09:40` / 工作日 `15:20` / `23:35`) | 带最近上下文和长期记忆自然搭话；主人说“在忙/晚安/暂停主动”自动静默 |
| `/补` | 掉线期间漏掉的消息，从 QQ 历史里捞回来补答 |
| **群聊/私聊严格隔离** | **不在群里加载任何玩法包**，群聊仅在被 `@` 时礼貌简短回应，绝不泄露主人私聊信息 |

---

## 四、五分钟跑起来（Docker Compose）

```bash
git clone https://github.com/ychenfen/dafeiyu-qq-companion.git && cd dafeiyu-qq-companion
cp .env.example .env        # 填 key、填你的大号 QQ
docker compose up -d

# 把插件和人设放进数据卷
cp -r plugin  data/plugins/astrbot_plugin_dafeiyu
cp -r packs   data/dafeiyu_packs
```

1. 打开 `http://127.0.0.1:6099/webui?token=<你设的口令>`，用小号扫码
2. 打开 `http://127.0.0.1:6185`，用启动日志里的初始密码登录面板
3. 面板里配供应商：`api_base` 填 `https://nano-gpt.com/api/v1`，模型填 `deepseek/deepseek-v4.1-flash-1017-uncensored`
4. 把人设写进 `personas` 表（或面板里新建人格，粘贴 [`persona/dafeiyu.md`](persona/dafeiyu.md)）
5. 大号给小号发一句「在吗」

> 二维码只有 **2 分钟**有效，必须在面板页面上现场扫，别截图传给别人。

### 运行单元测试（支持本地无 Docker 直接运行）
```bash
python3 -m unittest discover -s tests -v
```

---

## 五、踩过的 7 个真坑（坑比代码值钱）

### 1. 工具"不生效"，其实是模型没见过工具
插件注册成功、日志写着 `Added llm tool: set_qq_signature`，但让它改签名，它只会嘴上说"改好了"。
真因在 AstrBot 的 `tool_loop_agent_runner.py`：
```python
if isinstance(modalities, list) and modalities and "tool_use" not in modalities:
    logger.warning("Provider %s does not support tool_use, clearing tools for request.")
```
供应商配置里 `modalities` 没写 `tool_use`，**整包工具被清空后才发给模型**。它没骗你，它确实没这个工具，只能顺着人设演。
**修法**：`modalities: ["text", "image", "tool_use"]`。

### 2. 二维码 2 分钟就过期
日志里量得很清楚：`15:10:25` 生成，`15:12:27` 报 `ErrCode 3`。从截图发出去到对方扫，基本就超时了。
**修法**：永远让人扫面板页面上的二维码（会自动刷新），不要传图。

### 3. `ACCOUNT=` 快速登录会卡死
NapCat 支持 `ACCOUNT=<uin>` 用已保存会话免扫码。但会话失效后，它会停在「正在快速登录」几十秒到永远，**连二维码都不给**。
**修法**：只有在会话仍然有效时（正常关机重启）才有用；崩溃重生时不要开。

### 4. 某些中转模型会返回空字符串
`nano-gpt` 的 uncensored 模型在 `max_tokens` 给小的时候，会返回 `content: ""` —— 不报错、不抛异常。AstrBot 默认**不给非 NVIDIA 供应商设 `max_tokens`**，所以要在供应商配置里显式加：
```json
"custom_extra_body": {"max_tokens": 1024}
```

### 5. 容器凌晨崩溃 = 掉线一整天
NapCat 容器在凌晨退出重启后，**QQ 会话已经没了**，开始循环刷二维码。要么放一台 24 小时开机的 VPS，要么加看门狗定时查登录状态。

### 6. 数值型约束比形容词有效
写「不要写得太文学」没用；写「不许出现灯、光、空气、房间、窗、影子」立刻见效。同理，「每条不超过三十个字」比「简洁一点」管用一百倍。

### 7. 负面清单要具体到词
「不许回避」它听不懂；「不许说『我们先聊点别的』，不许拿『小脑袋瓜想什么呢』糊弄」它听得懂。

---

## 六、安全与隐私

- **不要把 6099 / 6185 暴露到公网**，只绑 `127.0.0.1`，用 SSH 隧道访问
- key 只放 `.env`，`.gitignore` 已经挡住
- 群聊里它是"只读"的：不加载玩法包、不接黄腔、不报主人信息
- 人设里明确写了：不碰未成年、不碰非自愿、不碰真实人物、不碰违法内容。**这几条建议保留**，删掉是给自己留隐患
- 用小号，不要用主号；新注册的号最容易风控

---

## 七、第三方内容与致谢

`packs/` 目录整理自公开分享的第三方提示词资料（by X `@Nyra` / 薛桉），收录已获许可。所有权归原作者，本仓库做收集与工程化整合。详见 [NOTICE.md](NOTICE.md)。

## 八、License

代码部分（`plugin/`、`scripts/`、`tests/`、`docker-compose.yml`）采用 [MIT License](LICENSE)。`packs/` 与 `persona/` 里的文字另算，见 [NOTICE.md](NOTICE.md)。
