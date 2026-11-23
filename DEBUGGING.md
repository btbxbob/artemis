# 调试 ARTEMIS 的长时间卡顿

实测环境：Windows 11 + MuMu 模拟器（2556×1179）+ 本地 Ollama `local-vlm`（qwen3.5:9b, num_ctx 24576）。

## 症状

同一条导航目标，一次 50 秒跑完，一次跑 376 秒才报 `Task failed`，屏幕上什么都没发生。

## 先搞清一件事：`traces/web_*/steps.json` 是空的

这版（commit 351ca84）**所有会话的 steps.json 都是空数组**，PASS 的也一样 ——
别拿「0 步」当「一步没执行」的证据（我一开始就这么误判了）。

真正的执行记录在 **`traces/data_engine.db`**（SQLite）：

| 表 | 内容 |
|---|---|
| `sessions` | 每轮 `session_id / status / start_time / end_time` |
| `steps` | 每一步 `action_taken`（含坐标）、`summary`、前后截图 hash |
| `traces` | 每次子调用（`llm_call` / `agent` / `log`）的 `duration / status / payload` |
| `failed_outputs` | 模型输出解析失败时的原文（这一版通常为空） |

## 查法

```bash
# 最近 5 轮：状态 / 用时 / 步数 / llm 调用次数 / 报错摘要
python scripts/artemis_trace.py last

# 某一轮的每一步 + 报错
python scripts/artemis_trace.py show <session_id 前 8 位>

# 这一轮最慢的 trace（含失败 payload）
python scripts/artemis_trace.py slow <session_id 前 8 位>
```

`scripts/artemis_trace.py` 在 r1999-agent 项目里（读的是本机 artemis 的 traces 目录）。

## 2026-11-23 实测的两种卡死

### 1. 上下文溢出（376 秒的真凶）

```
FlashRunner (agent) 351.8s  failed
  … 16 × llm_call，prompt_tokens 从 2820 一路涨到 6590 …
llm_gave_up: Error code: 400 - request (24600 tokens) exceeds the available
             context size (24576 tokens)
```

模型每一步只回一段「Observation & Planning」文本、不出动作 → runner 重试 → 每轮都把历史
拼进 prompt → 最终超过 Ollama 的 `num_ctx`，400 直接判永久失败。

**根因**：`config/artemis.jsonc` 的 `memory.transcript.context_budget_tokens` 是 80000
（按云端大上下文写的），对 24k 的本地模型等于没有上限。

**已修**：local / cloud 两份配置都改成 **16000**。修完同样的目标从「376 秒失败」变成
「39 秒失败」，不会再白烧六分钟。

### 2. 坐标点空（本地模型的空间定位）

```
step1: click  "836, 459"      ← 想点大厅右侧「入场」，实际坐标是 (2060, 555)
step2: click  "836, 127"      ← 想点顶部「养成追踪」
```

截图是完整 2556×1179，所以不是缩放问题，是模型给的坐标本身偏了。加上这游戏是 Unity，
无障碍树里**只有一个 `Game view` 元素**（`The element list only shows one generic
"Game view" element`），没有元素索引可用，只能靠视觉定位 —— 9B 本地模型的定位能力不够。

缓解办法（按优先级）：

1. 目标措辞里明确写「无障碍树只有一个 Game view，请用 ask_explorer / 屏幕百分比坐标」；
2. 关键按钮先用坐标脚本点好，artemis 只负责「认页面 / 处理弹层」；
3. 换更强的视觉模型（云端 DeepSeek 的 pro 档实测 268 秒能到位，但更贵更慢）。

## 另一种失败：click 参数不合法

```
click: Error during click: Invalid target format: None. Use an element index from the
Visible UI Elements list (e.g. 3) or normalized [x, y] coordinates with a target_description.
```

模型给了 `click` 但没给坐标/索引。属于同一类问题（定位失败），不是执行器坏了。

## 现场取证工具

`scripts/artemis_debug.py`（r1999-agent）边跑边带时间戳落盘 stdout，超过 `--stall`
秒没输出就自动存当前屏幕 + 前台 Activity + ollama 驻留状态：

```bash
python scripts/artemis_debug.py --task target_page --stall 45 --timeout 420
# 产物：logs/artemis_debug_<时间>.log、state/artemis_stall_<n>.png
```
