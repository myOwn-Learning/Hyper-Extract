## 1. 刻画当前行为

- [ ] 1.1 添加失败单元测试，证明百炼 structured extraction prompt 缺少 JSON 字样时会触发 provider 拒绝条件
- [ ] 1.2 添加失败单元测试，证明 DeepSeek provider 策略选择必须避开不支持的 response-format structured output
- [ ] 1.3 为现有 OpenAI-compatible structured extraction 行为添加回归测试覆盖

## 2. 结构化抽取 Adapter

- [ ] 2.1 创建内部 structured extraction adapter 模块，用于构造 prompt-to-schema runnable
- [ ] 2.2 在 adapter 层实现幂等 JSON 指令注入
- [ ] 2.3 实现 OpenAI-compatible JSON mode、百炼、DeepSeek 和未知 provider 的策略选择
- [ ] 2.4 为 JSON-prompt parsing fallback 实现 schema 校验
- [ ] 2.5 为不支持或失败的 structured-output strategy 添加可操作错误信息

## 3. Provider Metadata 与配置

- [ ] 3.1 确保 client 创建流程保留 adapter 需要的 provider metadata
- [ ] 3.2 为测试和 custom endpoint 添加显式内部 strategy override hook
- [ ] 3.3 验证 provider metadata 改动后，百炼默认 base URL 和 model 配置仍然可用

## 4. 迁移抽取调用点

- [ ] 4.1 将 `BaseAutoType` 中直接调用 `with_structured_output` 的 chain 构造替换为 adapter
- [ ] 4.2 将 `AutoGraph` one-stage structured extractor 构造替换为 adapter
- [ ] 4.3 将 `AutoGraph` two-stage node 和 edge extractor 构造替换为 adapter
- [ ] 4.4 审计图派生类型和 method class，移除剩余直接 structured-output 构造

## 5. 验证

- [ ] 5.1 运行模板解析、adapter 策略选择和 AutoType mock 抽取的聚焦单元测试
- [ ] 5.2 使用百炼配置和本地小 fixture 运行 `he parse` CLI smoke test
- [ ] 5.3 运行或记录 DeepSeek smoke test，确认不再使用 unsupported response-format mode
- [ ] 5.4 更新 provider structured-output 兼容性的用户侧 troubleshooting 文档
