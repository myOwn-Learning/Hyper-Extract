## 背景

Hyper-Extract 现在通过“生成的 prompt + `llm_client.with_structured_output(...)`”创建抽取链路。这个方式让模板作者可以专注于领域抽取语义，但也把 provider 兼容性假设放在了 LangChain structured-output 边界上。

已经暴露出两个 provider 差异：

- 百炼接受 OpenAI-compatible JSON-object response format，但要求请求 messages 明确包含 JSON 字样。
- DeepSeek 当前会拒绝现有 structured extraction 路径使用的 response-format 模式。

修复应放在统一构造路径中，避免要求每个 YAML 模板都加入 provider 专属样板文本。

## 目标 / 非目标

**目标：**

- 为所有 AutoType 抽取路径集中构造 structured extraction prompt。
- 在结构化输出边界统一、幂等地注入 provider-safe JSON 指令。
- 为 OpenAI、百炼、DeepSeek 和自定义 OpenAI-compatible endpoint 选择兼容的 structured-output 策略。
- 保持现有 `Template.create(...)`、CLI 用法和 YAML 模板语义稳定。
- 通过 mock LLM client 完成可测试设计，避免单元测试依赖真实 provider。

**非目标：**

- 重设计 YAML 模板格式。
- 在每个 preset template 中加入 provider-specific 文案。
- 替换 LangChain 作为模型抽象层。
- 保证所有第三方 OpenAI-compatible endpoint 无需配置即可工作。
- 修改 knowledge abstract 持久化格式。

## 决策

### 新增 structured extraction adapter

引入一个小型内部 adapter，专门负责创建 structured extraction chain。它接收：

- prompt 文本；
- Pydantic schema；
- LLM client；
- 可选 provider metadata 或 strategy override；
- 语义化 operation label，例如 `graph.node_extraction` 或 `model.extraction`。

adapter 返回一个兼容现有 `.invoke(...)` 和 `.batch(...)` 调用方式的 runnable。这样 `BaseAutoType`、`AutoGraph` 和图派生类不需要重复处理 provider 差异。

备选方案：逐个修改 YAML template guideline，加入 JSON 字样。该方案被拒绝，因为它会把传输层/provider 要求混入领域模板，也容易遗漏 custom template。

### 在 prompt assembly 阶段注入 JSON 指令

当使用 structured JSON mode 时，adapter 追加一句简短指令，例如：`Return the structured output as valid JSON.`。注入必须幂等：如果 prompt 已经包含 JSON 输出说明，就不重复追加。

备选方案：只针对百炼 prompt 修改。虽然可行，但 JSON 指令对所有 JSON-object structured-output 请求都有帮助，统一注入更简单、风险更低。

### 使用 provider-aware 策略选择

adapter 根据 client/config 中的 provider metadata 选择策略：

- OpenAI 和百炼：使用 LangChain structured output，并确保 prompt 包含 JSON 指令。
- DeepSeek：避免已知会被拒绝的 response-format 模式；优先使用 tool/function calling，如果不可用则回退到 JSON prompt + Pydantic parser。
- 未知自定义 endpoint：默认保留当前行为，同时提供显式 strategy override 作为逃生口。

备选方案：在 `create_llm` 里 special-case DeepSeek。该方案被拒绝，因为 structured extraction 策略会隐藏在 client factory 中，调用点仍然分散。

### 通过窄迁移保留现有调用方式

把直接构造 `prompt | llm.with_structured_output(schema)` 的位置替换为 adapter：

- `BaseAutoType` 通用抽取；
- `AutoGraph` one-stage 抽取；
- `AutoGraph` two-stage node 抽取；
- `AutoGraph` two-stage edge 抽取；
- 其他直接实例化独立 structured extractor 的图派生类或 method class。

抽取生命周期的其余部分保持不变。

## 风险 / 权衡

- Provider capability detection 可能不完整 -> 提供显式 strategy override，并在 provider 拒绝某种模式时抛出清晰错误。
- JSON prompt fallback 的可靠性弱于原生 structured output -> 仅在 provider 拒绝 native response formatting 时使用，并用现有 Pydantic schema 校验解析结果。
- 给 client 添加 provider metadata 可能暴露实现细节 -> metadata 保持可选，并尽量从现有配置中派生。
- 部分 custom prompt 可能已经限制输出格式 -> JSON 指令注入必须幂等且尽量短。
- Mock 测试无法覆盖所有 provider API 细节 -> 单元测试覆盖策略选择和 prompt 内容，同时保留每个 provider 的手动 smoke test 文档。
