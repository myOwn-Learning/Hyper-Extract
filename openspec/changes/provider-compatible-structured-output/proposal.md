## 为什么

Hyper-Extract 当前通过 LangChain structured output 构造抽取链路，但这个实现默认所有 OpenAI-compatible provider 都支持同一种 `response_format` 行为。实际使用中，百炼在 JSON-object 响应格式下要求 messages 明确包含 JSON 字样，DeepSeek 则会拒绝现有抽取流程使用的 response-format 模式，导致配置有效但抽取无法完成。

## 变更内容

- 新增统一的结构化输出 prompt 构造层，在不逐个修改 YAML 模板的前提下，为抽取 prompt 自动加入 provider 兼容的 JSON 输出指令。
- 引入 provider-aware 的结构化输出策略选择，让 OpenAI-compatible provider 使用各自支持的结构化输出模式，而不是假设一种 response format 可以覆盖所有 provider。
- 支持百炼：确保 JSON response-format 请求发送前，生成的 messages 中包含明确的 JSON 指令。
- 支持 DeepSeek：优先通过 tool/function calling 进行结构化抽取；如果不可用，再回退到 JSON prompt + Pydantic 校验，而不是继续使用 DeepSeek 不支持的 response-format 模式。
- 保持模板作者体验不变：YAML 模板继续只描述抽取目标、字段、标识符、展示和选项，不包含 provider 专属样板文本。

## 能力

### 新增能力

- `provider-compatible-structured-extraction`: 覆盖 LLM-backed AutoType parsing 的 provider-aware 结构化抽取 prompt 构造与输出策略选择。

### 修改能力

无。

## 影响

- 受影响代码：`hyperextract/types/base.py`、`hyperextract/types/graph.py` 中的图抽取构造逻辑及图派生类型、`hyperextract/utils/template_engine/` 中的模板解析和工厂构造、`hyperextract/utils/client.py` / `hyperextract/cli/config.py` 中的 client/provider 配置。
- 受影响行为：抽取流程应根据 provider 选择兼容的结构化输出策略，同时保持现有 `Template.create(...)`、CLI `he parse` 和 YAML 模板接口稳定。
- 测试重点：prompt 生成、provider 策略选择、百炼 JSON 指令注入、DeepSeek tool calling 优先和 fallback 行为。
