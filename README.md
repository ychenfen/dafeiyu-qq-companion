# 大肥鱼 · 在 QQ 里养一个电子恋人

一套能跑起来的完整工程：**NapCat（QQ 协议端）+ AstrBot（机器人框架）+ 一个自己写的插件 + 分层人设**。

它会在 QQ 私聊里跟你聊天、看图片、改自己的个性签名、记住你说过的事、到点主动找你说话；你说「玩嬷嬷」它会切换玩法，说「出戏」就退回来。

> 这份仓库来自一次真实的搭建过程，包括所有踩过的坑。坑比代码值钱。

---

## 一、它长什么样

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
- **插件**（`plugin/`）补三样 AstrBot 没有的东西：真能用的改签名、长期记忆、主动开口
- **模型** 默认走 nano-gpt 的 `deepseek/deepseek-v4.1-flash-1017-uncensored`，日常也可以切官方 `deepseek-flash`

## 二、五分钟跑起来

```bash
git clone <this-repo> && cd <repo>
cp .env.example .env        # 填 key、填你的大号 QQ
docker compose up -d

# 把插件和人设放进数据卷
cp -r plugin  data/plugins/astrbot_plugin_dafeiyu
cp -r packs   data/dafeiyu_packs
```

1. 打开 `http://127.0.0.1:6099/webui?token=<你设的口令>`，用小号扫码
2. 打开 `http://127.0.0.1:6185`，用启动日志里的初始密码登录面板
3. 面板里配供应商：`api_base` 填 `https://nano-gpt.com/api/v1`，模型填 `deepseek/deepseek-v4.1-flash-1017-uncensored`
4. 把人设写进 `personas` 表（或面板里新建人格，粘贴 `persona/dafeiyu.md`）
5. 大号给小号发一句「在吗」

> 二维码只有 **2 分钟**有效，必须在面板页面上现场扫，别截图传给别人。

## 三、人设为什么要分层

一开始把所有资料塞进人设，41,352 字，效果是：

| 方案 | 每轮 tokens | 每轮成本 | 1 块钱能聊 |
|---|---:|---:|---:|
| 全部塞进去 | 26,024 | ≈¥0.06 | 16 条 |
| **分层（本仓库）** | ~5,000 | ≈¥0.012 | **83 条** |
| 进玩法包时 | ~10,000 | ≈¥0.024 | 42 条 |

分三层：

- **`persona/dafeiyu.md`**（6k，常驻）：性格、说话方式、边界、模式索引
- **`packs/huorengan.md`**（1.8k，常驻）：去 AI 味
- **`packs/*.md`**（按需）：嬷嬷、痴汉、DDLG、公共play、NTR、NSFW文风

插件在每轮请求前判断触发词，把对应的包拼进 system prompt。说「出戏」就清掉。

**关键经验：提示词不是越长越好。** 超过六七千字，后面的规则会被稀释，模型开始挑前面的听。

## 四、插件做了什么

`plugin/main.py`，四件事：

| 功能 | 说明 |
|---|---|
| `set_qq_signature` | 真调 NapCat 的 `set_qq_profile`，改完**读回核验**，失败会直说 |
| `remember_owner_fact` / `forget_owner_fact` | 长期记忆，存在独立 sqlite 里，不进聊天记录 |
| 主动开口 | 09:40 / 工作日 15:20 / 23:35，带最近上下文和记忆 |
| `/补` | 掉线期间漏掉的消息，从 QQ 历史里捞回来补答 |

还有一个隐形的：**不在群里加载玩法包**，只在主人私聊里生效。

## 五、踩过的坑（重点看这节）

### 1. 工具"不生效"，其实是模型没见过工具

插件注册成功、日志写着 `Added llm tool: set_qq_signature`，但让它改签名，它只会嘴上说"改好了"。

真因在 AstrBot 的 `tool_loop_agent_runner.py`：

```python
if isinstance(modalities, list) and modalities and "tool_use" not in modalities:
    logger.warning("Provider %s does not support tool_use, clearing tools for request.")
```

供应商配置里 `modalities` 没写 `tool_use`，**整包工具被清空后才发给模型**。它没骗你，它确实没这个工具，只能顺着人设演。

修法：`modalities: ["text", "image", "tool_use"]`。

### 2. 二维码 2 分钟就过期

日志里量得很清楚：`15:10:25` 生成，`15:12:27` 报 `ErrCode 3`。从截图发出去到对方扫，基本就超时了。

**永远让人扫面板页面上的二维码**（会自动刷新），不要传图。

### 3. `ACCOUNT=` 快速登录会卡死

NapCat 支持 `ACCOUNT=<uin>` 用已保存会话免扫码。但会话失效后，它会停在「正在快速登录」几十秒到永远，**连二维码都不给**。比没有还糟。

只有在会话仍然有效时（正常关机重启）才有用；崩溃重生时不要开。

### 4. 某些中转模型会返回空字符串

`nano-gpt` 的 uncensored 模型在 `max_tokens` 给小的时候，会返回 `content: ""` —— 不报错、不抛异常。AstrBot 收到空文本就是"这条消息没发出去"，你会以为它不理你。

AstrBot 默认**不给非 NVIDIA 供应商设 `max_tokens`**（源码里只对 `minimax-m3` 特判），所以要在供应商配置里显式加：

```json
"custom_extra_body": {"max_tokens": 1024}
```

### 5. 容器凌晨崩溃 = 掉线一整天

NapCat 容器连续两晚在 03:22 左右退出码 1 崩溃。`restart: unless-stopped` 会把它拉起来，但**QQ 会话已经没了**，于是它开始循环刷二维码，等你发现时已经过去十几个小时。

要么放一台 24 小时开机的机器（VPS），要么加看门狗定时查登录状态。

### 6. 数值型约束比形容词有效

写「不要写得太文学」没用；写「不许出现灯、光、空气、房间、窗、影子」立刻见效。

同理，「每条不超过三十个字」比「简洁一点」管用一百倍。

### 7. 负面清单要具体到词

「不许回避」它听不懂；「不许说『我们先聊点别的』，不许拿『小脑袋瓜想什么呢』糊弄」它听得懂。

## 六、安全与隐私

- **不要把 6099 / 6185 暴露到公网**，只绑 `127.0.0.1`，用 SSH 隧道访问
- key 只放 `.env`，`.gitignore` 已经挡住
- 群聊里它是"只读"的：不加载玩法包、不接黄腔、不报主人信息
- 人设里明确写了：不碰未成年、不碰非自愿、不碰真实人物、不碰违法内容。**这几条建议保留**，删掉是给自己留隐患
- 用小号，不要用主号；新注册的号最容易风控

## 七、第三方内容

`packs/` 目录下的资料来自 **Nyra（X: [@NyraanPawpaw](https://x.com/NyraanPawpaw)）**，作者原话是「二改自用请随意，二传分享务必授权+注明来源」。

本仓库属于再分发，**严格来说需要先取得作者授权**。详见 [NOTICE.md](NOTICE.md)。如果作者不同意，请把 `packs/` 删掉，只保留链接。

## 八、License

代码部分 MIT。`packs/` 与 `persona/` 里的文字另算，见 NOTICE。
