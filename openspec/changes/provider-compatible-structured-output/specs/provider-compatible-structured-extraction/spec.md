## ADDED Requirements

### Requirement: 统一结构化抽取 prompt 构造
系统 SHALL 通过共享内部层构造结构化抽取 prompt，而不是要求 YAML 模板包含 provider-specific 输出指令。

#### Scenario: 百炼自动注入 JSON 指令
- **WHEN** 为百炼 LLM 创建 structured extraction chain，且源模板 prompt 不包含 JSON 字样
- **THEN** 发送 provider 请求前，生成的 model messages SHALL 包含带有 JSON 字样的输出指令

#### Scenario: 已有 JSON 指令保持不重复
- **WHEN** 从已经包含 JSON 输出说明的 prompt 创建 structured extraction chain
- **THEN** 系统 SHALL NOT 追加重复 JSON 指令

#### Scenario: YAML 模板保持 provider neutral
- **WHEN** 加载 preset 或 custom YAML template
- **THEN** 模板 SHALL NOT 需要包含 provider-specific JSON 或 DeepSeek 文案，也能参与结构化抽取

### Requirement: Provider-aware 结构化输出策略选择
系统 SHALL 根据配置的 LLM provider 选择兼容的 structured output strategy。

#### Scenario: OpenAI-compatible JSON mode provider
- **WHEN** 配置的 provider 支持用于 structured output 的 JSON response formatting
- **THEN** 系统 SHALL 使用现有 LangChain structured-output 路径，并确保 prompt 中包含 provider-safe JSON 指令

#### Scenario: DeepSeek provider
- **WHEN** 配置的 provider 是 DeepSeek
- **THEN** 系统 SHALL 避免使用已知会被 DeepSeek 拒绝的 response-format 模式，并使用受支持的 structured extraction strategy

#### Scenario: 不支持的 provider strategy
- **WHEN** 配置的 provider 无法匹配到受支持的 structured output strategy
- **THEN** 系统 SHALL 抛出可操作错误，明确指出 provider 和尝试使用的 structured-output strategy

### Requirement: 结构化输出校验保持 schema-driven
系统 SHALL 使用从模板或 method class 生成的同一套 Pydantic schema 校验 provider 响应。

#### Scenario: Fallback JSON parsing 校验 schema
- **WHEN** 某个 provider 使用 JSON-prompt parsing fallback
- **THEN** 解析后的对象 SHALL 在 merge 到 knowledge abstract 前通过目标 Pydantic schema 校验

#### Scenario: 无效 provider 输出被拒绝
- **WHEN** provider 返回无法解析或无法通过目标 schema 校验的输出
- **THEN** 系统 SHALL 抛出 structured extraction error，而不是静默 merge 无效数据

### Requirement: 现有抽取接口保持稳定
系统 SHALL 在改变内部 structured-output handling 的同时，保持公开 CLI 和 Python 抽取接口稳定。

#### Scenario: CLI parse 命令保持不变
- **WHEN** 用户运行 `he parse <input> -t <template> -o <output> -l <language>`
- **THEN** 命令 SHALL 使用 provider-compatible structured extraction path，且不要求新增 CLI flags

#### Scenario: Python Template API 保持不变
- **WHEN** 调用方使用 `Template.create(...).parse(...)` 或 `feed_text(...)`
- **THEN** 调用签名 SHALL 与现有用户代码兼容
