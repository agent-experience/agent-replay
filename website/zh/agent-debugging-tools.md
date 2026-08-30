---
title: AI Agent 调试工具指南：从可观测到根因分析
description: AI Agent 开发中最常被忽视的环节是调试。本文介绍 Agent 调试的核心问题、主流工具对比（Langfuse、LangSmith、Agent Replay）以及如何用确定性检测器定位静默失败。
head:
  - - meta
    - property: og:title
      content: AI Agent 调试工具指南：从可观测到根因分析
  - - meta
    - property: og:description
      content: AI Agent 开发中最常被忽视的环节是调试。本文介绍 Agent 调试的核心问题、主流工具对比以及如何用确定性检测器定位静默失败。
  - - meta
    - property: og:type
      content: article
  - - meta
    - name: keywords
      content: AI Agent调试, AI Agent开发工具, AI Agent工具, Agent调试工具, LLM调试, Agent可观测性
---

# AI Agent 调试工具指南

## Agent 为什么难调试

传统软件出错会抛异常、打印堆栈。AI Agent 不一样——它可以在报告"任务完成"的同时，忽略了关键的工具返回结果、编造了不存在的参数、或者用错误的证据得出了正确格式的结论。

四个核心难点：

**不可复现。** 同样的 prompt、同样的 temperature，跑 1000 次可能出 80 种不同结果。你看到的 bug 不会再出现。

**日志没用。** 几百行 token 输入输出只能告诉你发生了什么，但无法解释 Agent 为什么在第 7 步做了错误决策。

**重跑很贵。** Agent 在第 9 步失败，你要从第 1 步重新跑。每次重跑都要调用模型和工具，一天 100 美元的调试成本并不少见。

**没有根因分析。** 现有可观测工具告诉你"失败了"，但不告诉你"为什么失败"。

## 三类工具解决三个问题

| 工具类型 | 解决什么问题 | 代表工具 |
|---|---|---|
| 可观测平台 | 生产环境监控、团队协作、告警 | Langfuse、LangSmith |
| 评估工具 | 输出质量打分、回归测试 | Langfuse Evals、LangSmith Evaluations、Arize Phoenix |
| 调试工具 | 定位单次运行中的具体错误原因 | Agent Replay |

大多数团队先部署了可观测平台，但在排查具体问题时发现：看到 trace 只是开始，找到根因才是目标。

## 主流工具对比

| | Langfuse | LangSmith | Agent Replay |
|---|---|---|---|
| **核心定位** | 可观测 + 评估 | 可观测 + 评估 + 部署 | 调试 + 失败检测 |
| **Trace 采集** | 支持 | 支持 | 支持 |
| **失败检测** | 手动查看 | Engine 自动分析（需 LLM） | [10 个确定性检测器](/failure-patterns)，无需 LLM |
| **重放** | 重新调用模型 | 重新调用模型 | 确定性重放，零 API 调用 |
| **数据位置** | 云端或自部署 | 云端或自部署（企业版） | 本地 SQLite |
| **开源协议** | MIT | 专有 | Apache 2.0 |
| **免费额度** | 5 万 units/月 | 5000 traces/月 | 无限制，完全免费 |
| **付费方案** | ¥200+/月起 | $39/seat/月起 | 无 |

详细对比见 [Langfuse vs LangSmith vs Agent Replay](/compare)。

## Agent 最常见的 10 种静默失败

Agent 不会告诉你它错了。Agent Replay 内置 10 个确定性检测器，从录制的 trace 中自动识别这些失败模式：

| 失败模式 | 严重度 | 说明 |
|---|---|---|
| 幻觉工具参数 | 高 | Agent 编造不存在的参数、ID 或类型 |
| 忽略工具结果 | 高 | 工具返回了正确数据，但 Agent 没有使用 |
| 不安全写操作 | 高 | 执行删除/发送等操作前没有确认步骤 |
| 权限不匹配 | 高 | 被拒绝后无意义地重试或继续执行 |
| 最终答案矛盾 | 高 | 结论与执行过程中收集的证据矛盾 |
| 检索质量差 | 中 | 检索到的上下文与查询不相关 |
| 过期记忆 | 中 | 使用了已被后续步骤更新的旧数据 |
| 循环检测 | 中 | 相同的操作重复执行，没有进展 |
| 上下文污染 | 低 | 无关信息堆积，影响后续决策 |
| 过度重试 | 低 | 失败操作反复重试但策略不变 |

每个模式的详细说明、代码示例和检测规则：[10 AI Agent Failure Patterns](/failure-patterns)。

## 快速开始

```bash
pip install agent-replay
```

```python
from agent_replay import trace, event

with trace("research-agent", task="查找最新定价"):
    event.llm_call(
        provider="openai", model="gpt-4o",
        input_messages=[{"role": "user", "content": "查找最新定价"}],
        output_message={"role": "assistant", "content": "我来搜索定价页面。"},
        usage={"input_tokens": 800, "output_tokens": 200},
    )
    event.tool_call(
        name="browser.search",
        input={"query": "定价页面"},
        output={"url": "https://example.com/pricing"},
    )
```

```bash
agent-replay analyze latest
```

```text
Likely root cause:
  • Tool 'ticketing.update' returned an error but the agent continued
    and treated the run as successful. — ignored_tool_result
Severity: high   Confidence: 0.70
```

Agent 报告了"成功"，但 Agent Replay 检测到了真正的失败原因。

## 选择建议

- **生产环境监控** → Langfuse 或 LangSmith
- **开发阶段调试** → Agent Replay
- **数据不能离开本地** → Agent Replay
- **团队协作** → Langfuse
- **端到端平台** → LangSmith

这三类工具不互斥。用 Langfuse/LangSmith 做生产监控，用 Agent Replay 做本地调试，是目前最务实的组合。

完整功能对比 → [Langfuse vs LangSmith vs Agent Replay](/compare)
入门指南 → [Getting Started](/guide/getting-started)
GitHub → [agent-experience/agent-replay](https://github.com/agent-experience/agent-replay)
