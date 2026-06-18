# Provider-Compatible Structured Output 设计

## 背景

Hyper-Extract 当前通过 LangChain 的 `with_structured_output(...)` 创建结构化抽取链路。这个路径在 OpenAI 上成立，但在 OpenAI-compatible provider 上暴露出兼容性差异：

- 百炼在使用 `response_format` 的 JSON-object 模式时，要求 messages 中明确包含 `json` 字样，否则返回 400。
- DeepSeek 当前拒绝现有 structured-output 路径使用的 response-format 模式。

目标是在统一 prompt 构造层解决这些问题，而不是逐个修改 YAML 模板。

## 目标

- 在内部统一构造 structured extraction prompt 和 schema runnable。
- 自动、幂等地为结构化抽取 prompt 注入 JSON 输出指令。
- 为不同 provider 选择兼容的 structured output strategy。
- DeepSeek 优先使用 tool/function calling；不支持时再 fallback 到 JSON prompt + Pydantic 校验。
- 保持 `Template.create(...)`、`parse(...)`、`feed_text(...)` 和 CLI `he parse` 的现有接口不变。

## 非目标

- 不重设计 YAML 模板格式。
- 不把 provider-specific 文案加入每个 preset template。
- 不替换 LangChain。
- 不保证所有未知 OpenAI-compatible endpoint 自动可用。
- 不修改 knowledge abstract 持久化格式。

## 推荐架构

新增一个内部 structured extraction adapter，例如 `hyperextract/utils/structured_output.py`。现有调用点从直接构造：

```python
ChatPromptTemplate.from_template(prompt) | llm.with_structured_output(schema)
```

改为通过 adapter：

```python
create_structured_extractor(
    prompt=prompt,
    schema=schema,
    llm_client=llm,
    operation="graph.node_extraction",
)
```

adapter 负责：

- 规范化 prompt，并在需要时注入 JSON 指令；
- 读取 provider metadata；
- 选择结构化输出策略；
- 返回兼容 `.invoke(...)` 和 `.batch(...)` 的 runnable。

## Provider Metadata

`create_llm(...)` 创建 client 后，应附加轻量内部 metadata：

```text
_provider = "openai" | "bailian" | "deepseek" | "vllm" | ""
_structured_output_strategy = optional override
```

`client.py` 只负责记录 provider 信息，不负责决定结构化输出策略。策略选择由 structured extraction adapter 统一完成。

## 策略选择

```text
provider=bailian
  -> LangChain structured output
  -> prompt 自动注入 JSON 指令

provider=openai
  -> 保持当前 LangChain structured output 路径
  -> prompt 自动注入 JSON 指令，兼容更严格 endpoint

provider=deepseek
  -> 优先 tool/function calling
  -> 如果明确不支持，再 fallback 到 JSON prompt + Pydantic validation

provider=unknown/custom
  -> 默认当前行为
  -> 允许通过 override 指定 strategy
```

## DeepSeek Fallback

DeepSeek 的 fallback 必须严格，不允许把非结构化文本猜测性合并进知识库：

```text
tool/function calling
  ├─ 成功：返回 schema 实例
  └─ 失败且属于 unsupported strategy：
        JSON prompt
          -> raw text
          -> 提取 JSON object
          -> Pydantic schema 校验
          -> 返回 schema 实例
```

只有明确属于 unsupported strategy 的错误可以 fallback。认证失败、网络错误、rate limit、余额不足、server error 不应 fallback。

## 错误处理

错误分三类：

- `strategy_unsupported`: provider 明确拒绝某种 structured-output strategy，可按规则 fallback。
- `provider_api_failure`: 认证、网络、限流、余额或 server error，直接抛出。
- `schema_validation_failed`: fallback 输出无法解析或不符合 Pydantic schema，直接抛出。

错误信息应包含安全元信息，不包含 API key：

```text
Structured extraction failed:
provider=deepseek
strategy=json_prompt_parser
operation=graph.node_extraction
reason=schema_validation_failed
```

## 迁移范围

需要替换直接使用 `with_structured_output(...)` 的构造点：

- `BaseAutoType` 通用抽取；
- `AutoGraph` one-stage 抽取；
- `AutoGraph` two-stage node 抽取；
- `AutoGraph` two-stage edge 抽取；
- 图派生类型和 method class 中剩余的直接 structured-output 构造。

抽取、merge、index、dump/load 生命周期保持不变。

## 测试策略

### Prompt 注入测试

- prompt 不含 JSON 时，输出 prompt 包含 JSON 指令。
- prompt 已含 JSON/json 时，不重复追加。
- 中文 prompt 也能正确追加 JSON 指令。

### Provider 策略选择测试

- `provider=bailian` 选择 LangChain structured output。
- `provider=openai` 选择现有 structured output。
- `provider=deepseek` 优先 tool/function calling。
- `provider=unknown` 保持默认行为。
- 显式 override 可以强制指定 strategy。

### DeepSeek fallback 测试

- tool calling 成功时不进入 fallback。
- tool calling 遇到 unsupported strategy 时进入 fallback。
- auth/rate limit/network error 不 fallback。
- fallback 返回非法 JSON 时抛错。
- fallback 返回 schema 不匹配 JSON 时抛错。
- fallback 返回合法 JSON 时返回 Pydantic schema 实例。

### 回归测试

- 现有 `BaseAutoType` mock 抽取测试继续通过。
- `AutoGraph` two-stage node/edge 抽取继续通过。
- `Template.create(...).parse(...)` 和 `feed_text(...)` 调用接口不变。

## Smoke Test

百炼配置下至少验证：

```bash
uv run he parse examples/zh/sushi.md -t general/biography_graph -o ./output/ -l zh -f
```

DeepSeek smoke test 可以先文档化；如果要执行，需要可用 DeepSeek key，并确认会产生真实 API 调用。

## 验收标准

- 百炼不再因为 messages 缺少 JSON 字样触发 400。
- DeepSeek 不再走已知不支持的 response-format mode。
- DeepSeek tool/function calling 不可用时，fallback 结果必须经过 Pydantic 校验。
- 无效 provider 输出不会 merge 进 knowledge abstract。
- 公开 CLI 和 Python API 保持兼容。
