# Provider-Compatible Structured Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Hyper-Extract 在百炼、DeepSeek、OpenAI 和自定义 OpenAI-compatible provider 上通过统一 adapter 构造结构化抽取链路，避免 provider-specific prompt 散落到 YAML 模板中。

**Architecture:** 新增 `hyperextract/utils/structured_output.py` 作为唯一 structured extraction adapter。`client.py` 给 LLM client 附加轻量 provider metadata，`BaseAutoType`、`AutoGraph`、`AutoHypergraph` 等调用点改为通过 adapter 创建 runnable。

**Tech Stack:** Python 3.11、Pydantic v2、LangChain `ChatPromptTemplate` / `with_structured_output`、pytest、Typer CLI。

---

## 文件结构

- Create: `hyperextract/utils/structured_output.py`
  - 负责 JSON 指令注入、provider metadata 读取、strategy 选择、DeepSeek fallback runnable、统一错误类型。
- Modify: `hyperextract/utils/client.py`
  - 在 `create_llm(...)` 返回的 `ChatOpenAI` 实例上附加 `_provider` 和 `_structured_output_strategy`。
- Modify: `hyperextract/utils/__init__.py`
  - 导出 adapter 入口，便于类型层统一 import。
- Modify: `hyperextract/types/base.py`
  - 用 adapter 替换通用 `data_extractor` 构造。
- Modify: `hyperextract/types/graph.py`
  - 用 adapter 替换 one-stage、node、edge structured extractor 构造。
- Modify: `hyperextract/types/hypergraph.py`
  - 用 adapter 替换 hypergraph 的 one-stage、node、edge structured extractor 构造。
- Modify: `hyperextract/types/temporal_graph.py`
  - 确认使用继承的 adapter-backed extractor，不新增 direct `with_structured_output`。
- Modify: `hyperextract/types/spatial_graph.py`
  - 确认使用继承的 adapter-backed extractor，不新增 direct `with_structured_output`。
- Modify: `hyperextract/types/spatio_temporal_graph.py`
  - 确认使用继承的 adapter-backed extractor，不新增 direct `with_structured_output`。
- Create: `tests/utils/test_structured_output.py`
  - 覆盖 prompt 注入、provider strategy、DeepSeek fallback、错误分类。
- Modify: `tests/utils/test_client.py`
  - 覆盖 provider metadata。
- Modify: existing AutoType tests only if adapter changes mock assumptions.
- Modify: `docs/en/resources/troubleshooting.md` and `docs/zh/resources/troubleshooting.md`
  - 增加 provider structured output 兼容性排障说明。

---

### Task 1: 新增 adapter 的失败测试

**Files:**
- Create: `tests/utils/test_structured_output.py`
- No production files modified in this task.

- [ ] **Step 1: 写入 adapter 行为测试**

Create `tests/utils/test_structured_output.py` with:

```python
from typing import Any

import pytest
from pydantic import BaseModel
from langchain_core.runnables import RunnableSerializable

from hyperextract.utils.structured_output import (
    StructuredExtractionError,
    create_structured_extractor,
    ensure_json_instruction,
    get_provider_name,
)


class SampleSchema(BaseModel):
    name: str


class StaticRunnable(RunnableSerializable):
    result: Any

    def invoke(self, input: Any, config: Any = None) -> Any:
        return self.result

    def batch(self, inputs: list[Any], config: Any = None, **kwargs: Any) -> list[Any]:
        return [self.invoke(item, config) for item in inputs]


class RecordingLLM:
    def __init__(self, provider: str = "", strategy_error: Exception | None = None):
        self._provider = provider
        self.strategy_error = strategy_error
        self.calls: list[dict[str, Any]] = []

    def with_structured_output(self, schema: type[BaseModel], **kwargs: Any) -> StaticRunnable:
        self.calls.append({"schema": schema, "kwargs": kwargs})
        if self.strategy_error:
            raise self.strategy_error
        return StaticRunnable(result=schema(name="structured"))

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "RecordingLLM":
        self.calls.append({"tools": tools, "kwargs": kwargs})
        if self.strategy_error:
            raise self.strategy_error
        return self


def test_ensure_json_instruction_adds_json_once():
    prompt = "Extract entities from {source_text}."
    result = ensure_json_instruction(prompt)
    assert "JSON" in result
    assert result.count("Return the structured output as valid JSON.") == 1


def test_ensure_json_instruction_is_idempotent():
    prompt = "Extract entities and return valid JSON."
    result = ensure_json_instruction(prompt)
    assert result == prompt


def test_get_provider_name_reads_client_metadata():
    llm = RecordingLLM(provider="bailian")
    assert get_provider_name(llm) == "bailian"


def test_bailian_uses_structured_output_with_json_prompt():
    llm = RecordingLLM(provider="bailian")
    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    result = extractor.invoke({"source_text": "Ada Lovelace"})

    assert result == SampleSchema(name="structured")
    assert llm.calls[0]["schema"] is SampleSchema


def test_deepseek_prefers_tool_strategy():
    llm = RecordingLLM(provider="deepseek")
    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    result = extractor.invoke({"source_text": "Ada Lovelace"})

    assert result == SampleSchema(name="structured")
    assert llm.calls[0]["kwargs"].get("method") == "function_calling"


def test_deepseek_json_fallback_validates_schema():
    llm = RecordingLLM(provider="deepseek")
    llm._structured_output_strategy = "json_prompt_parser"

    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    result = extractor._parse_json_response('{"name": "Ada"}')

    assert result == SampleSchema(name="Ada")


def test_json_fallback_rejects_invalid_schema():
    llm = RecordingLLM(provider="deepseek")
    llm._structured_output_strategy = "json_prompt_parser"
    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    with pytest.raises(StructuredExtractionError) as exc:
        extractor._parse_json_response('{"unknown": "Ada"}')

    assert "schema_validation_failed" in str(exc.value)
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run pytest tests/utils/test_structured_output.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'hyperextract.utils.structured_output'`.

- [ ] **Step 3: Commit 测试**

```bash
git add tests/utils/test_structured_output.py
git commit -m "test: characterize structured output adapter behavior"
```

---

### Task 2: 实现 structured output adapter 最小骨架

**Files:**
- Create: `hyperextract/utils/structured_output.py`
- Modify: `hyperextract/utils/__init__.py`
- Test: `tests/utils/test_structured_output.py`

- [ ] **Step 1: 创建 adapter 模块**

Create `hyperextract/utils/structured_output.py` with:

```python
"""Provider-compatible structured output helpers."""

from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel, ValidationError
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable


JSON_INSTRUCTION = "Return the structured output as valid JSON."


class StructuredExtractionError(RuntimeError):
    """Raised when provider-compatible structured extraction fails."""

    def __init__(
        self,
        *,
        provider: str,
        strategy: str,
        operation: str,
        reason: str,
        detail: str = "",
    ) -> None:
        self.provider = provider
        self.strategy = strategy
        self.operation = operation
        self.reason = reason
        self.detail = detail
        message = (
            "Structured extraction failed: "
            f"provider={provider or 'unknown'} "
            f"strategy={strategy} "
            f"operation={operation} "
            f"reason={reason}"
        )
        if detail:
            message = f"{message} detail={detail}"
        super().__init__(message)


def ensure_json_instruction(prompt: str) -> str:
    """Append a JSON instruction unless the prompt already mentions JSON."""
    if "json" in prompt.lower():
        return prompt
    return f"{prompt.rstrip()}\n\n{JSON_INSTRUCTION}"


def get_provider_name(llm_client: Any) -> str:
    """Read provider metadata from an LLM client."""
    return str(getattr(llm_client, "_provider", "") or "").lower()


def get_strategy_override(llm_client: Any) -> str:
    """Read an optional structured-output strategy override from an LLM client."""
    return str(getattr(llm_client, "_structured_output_strategy", "") or "").lower()


def select_strategy(llm_client: Any) -> str:
    """Select the structured-output strategy for an LLM client."""
    override = get_strategy_override(llm_client)
    if override:
        return override

    provider = get_provider_name(llm_client)
    if provider == "deepseek":
        return "tool_calling"
    return "langchain_structured"


def create_structured_extractor(
    *,
    prompt: str,
    schema: Type[BaseModel],
    llm_client: Any,
    operation: str,
) -> RunnableSerializable:
    """Create a provider-compatible structured extraction runnable."""
    strategy = select_strategy(llm_client)

    if strategy == "json_prompt_parser":
        return JsonPromptParserRunnable(
            prompt=ensure_json_instruction(prompt),
            schema=schema,
            llm_client=llm_client,
            operation=operation,
        )

    prompt_template = ChatPromptTemplate.from_template(ensure_json_instruction(prompt))

    if strategy == "tool_calling":
        try:
            return prompt_template | llm_client.with_structured_output(
                schema,
                method="function_calling",
            )
        except TypeError:
            return prompt_template | llm_client.with_structured_output(schema)

    return prompt_template | llm_client.with_structured_output(schema)


class JsonPromptParserRunnable(RunnableSerializable):
    """Runnable fallback that asks for JSON and validates it with Pydantic."""

    prompt: str
    schema: Type[BaseModel]
    llm_client: Any
    operation: str

    class Config:
        arbitrary_types_allowed = True

    def invoke(self, input: Any, config: Any = None) -> BaseModel:
        prompt_template = ChatPromptTemplate.from_template(self.prompt)
        response = (prompt_template | self.llm_client).invoke(input, config=config)
        content = getattr(response, "content", response)
        return self._parse_json_response(str(content))

    def batch(self, inputs: list[Any], config: Any = None, **kwargs: Any) -> list[BaseModel]:
        return [self.invoke(item, config=config) for item in inputs]

    def _parse_json_response(self, content: str) -> BaseModel:
        provider = get_provider_name(self.llm_client)
        try:
            payload = json.loads(_extract_json_object(content))
        except ValueError as exc:
            raise StructuredExtractionError(
                provider=provider,
                strategy="json_prompt_parser",
                operation=self.operation,
                reason="json_parse_failed",
                detail=str(exc),
            ) from exc

        try:
            return self.schema.model_validate(payload)
        except ValidationError as exc:
            raise StructuredExtractionError(
                provider=provider,
                strategy="json_prompt_parser",
                operation=self.operation,
                reason="schema_validation_failed",
                detail=str(exc.errors()[0]) if exc.errors() else str(exc),
            ) from exc


def _extract_json_object(content: str) -> str:
    """Extract the first JSON object from a model response."""
    text = content.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in provider response")
    return text[start : end + 1]
```

- [ ] **Step 2: 导出 adapter API**

Modify `hyperextract/utils/__init__.py`:

```python
"""Hyperextract utilities module."""

from .logging import get_logger, configure_logging, set_log_level
from .client import get_client
from .structured_output import (
    StructuredExtractionError,
    create_structured_extractor,
)

__all__ = [
    "get_logger",
    "configure_logging",
    "set_log_level",
    "get_client",
    "StructuredExtractionError",
    "create_structured_extractor",
]
```

- [ ] **Step 3: 运行 adapter 测试**

Run:

```bash
uv run pytest tests/utils/test_structured_output.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit adapter 骨架**

```bash
git add hyperextract/utils/structured_output.py hyperextract/utils/__init__.py tests/utils/test_structured_output.py
git commit -m "feat: add structured output adapter"
```

---

### Task 3: 添加 provider metadata

**Files:**
- Modify: `hyperextract/utils/client.py`
- Modify: `tests/utils/test_client.py`

- [ ] **Step 1: 写 provider metadata 测试**

Append to `tests/utils/test_client.py`:

```python
class TestLLMProviderMetadata:
    def test_create_llm_attaches_provider_metadata(self):
        from hyperextract.utils.client import create_llm

        llm = create_llm(
            {
                "provider": "bailian",
                "model": "qwen-plus",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key": "sk-test",
            }
        )

        assert llm._provider == "bailian"
        assert llm._structured_output_strategy == ""
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run pytest tests/utils/test_client.py::TestLLMProviderMetadata -v
```

Expected: FAIL with missing `_provider` attribute.

- [ ] **Step 3: 修改 `create_llm(...)` 附加 metadata**

In `hyperextract/utils/client.py`, replace the `return ChatOpenAI(...)` block in `create_llm` with:

```python
    llm = ChatOpenAI(
        model=config["model"],
        api_key=config["api_key"] or os.environ.get("OPENAI_API_KEY", ""),
        base_url=config.get("base_url") or None,
        temperature=config.get("temperature", 0),
    )
    llm._provider = config.get("provider", "")
    llm._structured_output_strategy = config.get("structured_output_strategy", "")
    return llm
```

- [ ] **Step 4: 运行 provider metadata 测试**

Run:

```bash
uv run pytest tests/utils/test_client.py::TestLLMProviderMetadata -v
```

Expected: PASS.

- [ ] **Step 5: Commit provider metadata**

```bash
git add hyperextract/utils/client.py tests/utils/test_client.py
git commit -m "feat: attach llm provider metadata"
```

---

### Task 4: 迁移 `BaseAutoType`

**Files:**
- Modify: `hyperextract/types/base.py`
- Test: `tests/types/test_model_basic.py`, `tests/types/test_list_operations.py`, `tests/types/test_set_operations.py`

- [ ] **Step 1: 修改 import**

In `hyperextract/types/base.py`, remove:

```python
from langchain_core.prompts import ChatPromptTemplate
```

Add:

```python
from hyperextract.utils.structured_output import create_structured_extractor
```

- [ ] **Step 2: 替换 data extractor 构造**

Replace:

```python
        # Initialize template
        self.prompt_template = ChatPromptTemplate.from_template(self.prompt)
        self.data_extractor = (
            self.prompt_template
            | self.llm_client.with_structured_output(self._data_schema)
        )
```

with:

```python
        # Initialize structured extractor
        self.data_extractor = create_structured_extractor(
            prompt=self.prompt,
            schema=self._data_schema,
            llm_client=self.llm_client,
            operation=f"{self.__class__.__name__}.data_extraction",
        )
```

- [ ] **Step 3: 运行基础类型测试**

Run:

```bash
uv run pytest tests/types/test_model_basic.py tests/types/test_list_operations.py tests/types/test_set_operations.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit BaseAutoType 迁移**

```bash
git add hyperextract/types/base.py
git commit -m "refactor: route base extraction through adapter"
```

---

### Task 5: 迁移 `AutoGraph`

**Files:**
- Modify: `hyperextract/types/graph.py`
- Test: `tests/types/test_graph_extraction.py`, `tests/types/test_graph_dangling.py`, `tests/types/test_graph_search.py`

- [ ] **Step 1: 修改 imports**

In `hyperextract/types/graph.py`, remove:

```python
from langchain_core.prompts import ChatPromptTemplate
```

Add:

```python
from hyperextract.utils.structured_output import create_structured_extractor
```

- [ ] **Step 2: 替换 node extractor 构造**

Replace:

```python
        self.prompt_template = ChatPromptTemplate.from_template(self.node_prompt)
        self.node_extractor = (
            self.prompt_template
            | self.llm_client.with_structured_output(self.node_list_schema)
        )
```

with:

```python
        self.node_extractor = create_structured_extractor(
            prompt=self.node_prompt,
            schema=self.node_list_schema,
            llm_client=self.llm_client,
            operation="AutoGraph.node_extraction",
        )
```

- [ ] **Step 3: 替换 edge extractor 构造**

Replace:

```python
        self.edge_prompt_template = ChatPromptTemplate.from_template(self.edge_prompt)
        self.edge_extractor = (
            self.edge_prompt_template
            | self.llm_client.with_structured_output(self.edge_list_schema)
        )
```

with:

```python
        self.edge_extractor = create_structured_extractor(
            prompt=self.edge_prompt,
            schema=self.edge_list_schema,
            llm_client=self.llm_client,
            operation="AutoGraph.edge_extraction",
        )
```

- [ ] **Step 4: 运行 graph 测试**

Run:

```bash
uv run pytest tests/types/test_graph_extraction.py tests/types/test_graph_dangling.py tests/types/test_graph_search.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit AutoGraph 迁移**

```bash
git add hyperextract/types/graph.py
git commit -m "refactor: route graph extraction through adapter"
```

---

### Task 6: 迁移 `AutoHypergraph`

**Files:**
- Modify: `hyperextract/types/hypergraph.py`
- Test: existing type tests plus direct import smoke.

- [ ] **Step 1: 修改 imports**

In `hyperextract/types/hypergraph.py`, remove:

```python
from langchain_core.prompts import ChatPromptTemplate
```

Add:

```python
from hyperextract.utils.structured_output import create_structured_extractor
```

- [ ] **Step 2: 替换 node extractor 构造**

Replace:

```python
        self.prompt_template = ChatPromptTemplate.from_template(self.node_prompt)
        self.node_extractor = (
            self.prompt_template
            | self.llm_client.with_structured_output(self.node_list_schema)
        )
```

with:

```python
        self.node_extractor = create_structured_extractor(
            prompt=self.node_prompt,
            schema=self.node_list_schema,
            llm_client=self.llm_client,
            operation="AutoHypergraph.node_extraction",
        )
```

- [ ] **Step 3: 替换 edge extractor 构造**

Replace:

```python
        self.edge_prompt_template = ChatPromptTemplate.from_template(self.edge_prompt)
        self.edge_extractor = (
            self.edge_prompt_template
            | self.llm_client.with_structured_output(self.edge_list_schema)
        )
```

with:

```python
        self.edge_extractor = create_structured_extractor(
            prompt=self.edge_prompt,
            schema=self.edge_list_schema,
            llm_client=self.llm_client,
            operation="AutoHypergraph.edge_extraction",
        )
```

- [ ] **Step 4: 运行 hypergraph import smoke**

Run:

```bash
uv run python -c "from hyperextract.types import AutoHypergraph; print(AutoHypergraph.__name__)"
```

Expected output includes:

```text
AutoHypergraph
```

- [ ] **Step 5: 运行类型测试全集**

Run:

```bash
uv run pytest tests/types -v
```

Expected: PASS.

- [ ] **Step 6: Commit AutoHypergraph 迁移**

```bash
git add hyperextract/types/hypergraph.py
git commit -m "refactor: route hypergraph extraction through adapter"
```

---

### Task 7: 审计派生图类型和 method class

**Files:**
- Inspect: `hyperextract/types/temporal_graph.py`
- Inspect: `hyperextract/types/spatial_graph.py`
- Inspect: `hyperextract/types/spatio_temporal_graph.py`
- Inspect: `hyperextract/methods/**/*.py`

- [ ] **Step 1: 搜索残留 direct structured-output 构造**

Run:

```bash
rg -n "with_structured_output|ChatPromptTemplate.from_template\\(.*prompt" hyperextract/types hyperextract/methods
```

Expected: `with_structured_output` only appears in adapter or not at all under `hyperextract/types` and `hyperextract/methods`.

- [ ] **Step 2: 如果派生类型只调用 `self.data_extractor` / `self.edge_extractor`，不改代码**

Verify these files use inherited adapter-backed extractors:

```bash
rg -n "self\\.data_extractor|self\\.edge_extractor|with_structured_output" hyperextract/types/temporal_graph.py hyperextract/types/spatial_graph.py hyperextract/types/spatio_temporal_graph.py
```

Expected: no `with_structured_output`; only `self.data_extractor` / `self.edge_extractor`.

- [ ] **Step 3: 如果 method class 有 direct structured output，迁移到 adapter**

For each match in `hyperextract/methods/**/*.py`, replace:

```python
ChatPromptTemplate.from_template(prompt) | self.llm_client.with_structured_output(schema)
```

with:

```python
create_structured_extractor(
    prompt=prompt,
    schema=schema,
    llm_client=self.llm_client,
    operation="<ClassName>.<operation_name>",
)
```

- [ ] **Step 4: 运行 methods import smoke**

Run:

```bash
uv run python -c "from hyperextract.methods import list_methods; print(sorted(list_methods()))"
```

Expected output includes method names such as `light_rag`, `graph_rag`, and `atom`.

- [ ] **Step 5: Commit 审计结果**

If code changed:

```bash
git add hyperextract/types hyperextract/methods
git commit -m "refactor: remove remaining direct structured output calls"
```

If no code changed:

```bash
git status --short
```

Expected: no staged changes for this task.

---

### Task 8: 完善 DeepSeek fallback 错误分类

**Files:**
- Modify: `hyperextract/utils/structured_output.py`
- Modify: `tests/utils/test_structured_output.py`

- [ ] **Step 1: 添加 unsupported-only fallback 测试**

Append to `tests/utils/test_structured_output.py`:

```python
def test_api_failure_does_not_fallback_to_json_parser():
    llm = RecordingLLM(
        provider="deepseek",
        strategy_error=RuntimeError("401 invalid api key"),
    )

    with pytest.raises(RuntimeError) as exc:
        create_structured_extractor(
            prompt="Extract a name from {source_text}.",
            schema=SampleSchema,
            llm_client=llm,
            operation="test.sample",
        )

    assert "401 invalid api key" in str(exc.value)


def test_explicit_json_prompt_parser_override_uses_fallback():
    llm = RecordingLLM(provider="deepseek")
    llm._structured_output_strategy = "json_prompt_parser"

    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    assert extractor._parse_json_response('{"name": "Grace"}') == SampleSchema(name="Grace")
```

- [ ] **Step 2: 添加 helper 判断 unsupported strategy**

In `hyperextract/utils/structured_output.py`, add:

```python
def is_strategy_unsupported_error(exc: Exception) -> bool:
    """Return True only for provider errors that indicate unsupported structured mode."""
    text = str(exc).lower()
    markers = [
        "response_format",
        "unavailable",
        "unsupported",
        "not support",
        "invalid_parameter_error",
    ]
    return any(marker in text for marker in markers)
```

- [ ] **Step 3: 调整 DeepSeek tool strategy fallback**

In `create_structured_extractor(...)`, replace the `tool_calling` branch with:

```python
    if strategy == "tool_calling":
        try:
            return prompt_template | llm_client.with_structured_output(
                schema,
                method="function_calling",
            )
        except TypeError:
            return prompt_template | llm_client.with_structured_output(schema)
        except Exception as exc:
            if get_provider_name(llm_client) == "deepseek" and is_strategy_unsupported_error(exc):
                return JsonPromptParserRunnable(
                    prompt=ensure_json_instruction(prompt),
                    schema=schema,
                    llm_client=llm_client,
                    operation=operation,
                )
            raise
```

- [ ] **Step 4: 运行 adapter 测试**

Run:

```bash
uv run pytest tests/utils/test_structured_output.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit fallback 错误分类**

```bash
git add hyperextract/utils/structured_output.py tests/utils/test_structured_output.py
git commit -m "fix: restrict deepseek structured output fallback"
```

---

### Task 9: 更新 troubleshooting 文档

**Files:**
- Modify: `docs/en/resources/troubleshooting.md`
- Modify: `docs/zh/resources/troubleshooting.md`

- [ ] **Step 1: 更新中文排障文档**

Append to `docs/zh/resources/troubleshooting.md`:

```markdown
## Provider structured output 兼容性

### 百炼返回 messages must contain the word json

如果百炼返回类似错误：

```text
'messages' must contain the word 'json'
```

说明 provider 使用 JSON response format 时要求 prompt 明确包含 JSON 字样。Hyper-Extract 会在统一 structured extraction adapter 中自动注入 JSON 输出指令；不需要修改 YAML 模板。

### DeepSeek 拒绝 response_format

如果 DeepSeek 拒绝 response-format structured output，Hyper-Extract 会优先尝试 tool/function calling。只有在 provider 明确不支持该策略时，才会回退到 JSON prompt + Pydantic 校验。

认证失败、网络错误、限流、余额不足不会触发 fallback，应按 provider/API 配置问题处理。
```

- [ ] **Step 2: 更新英文排障文档**

Append to `docs/en/resources/troubleshooting.md`:

```markdown
## Provider structured output compatibility

### Bailian returns messages must contain the word json

If Bailian returns an error like:

```text
'messages' must contain the word 'json'
```

The provider requires prompts to explicitly mention JSON when JSON response format is used. Hyper-Extract injects this instruction in the unified structured extraction adapter; YAML templates do not need provider-specific wording.

### DeepSeek rejects response_format

If DeepSeek rejects response-format structured output, Hyper-Extract first tries tool/function calling. It falls back to JSON prompt + Pydantic validation only when the provider clearly does not support the structured-output strategy.

Authentication failures, network errors, rate limits, and insufficient balance do not trigger fallback and should be treated as provider/API configuration issues.
```

- [ ] **Step 3: Commit 文档**

```bash
git add docs/en/resources/troubleshooting.md docs/zh/resources/troubleshooting.md
git commit -m "docs: add structured output troubleshooting"
```

---

### Task 10: 全量验证

**Files:**
- No file changes expected.

- [ ] **Step 1: 运行聚焦测试**

Run:

```bash
uv run pytest tests/utils/test_structured_output.py tests/utils/test_client.py tests/types -v
```

Expected: PASS.

- [ ] **Step 2: 搜索 direct structured-output 残留**

Run:

```bash
rg -n "with_structured_output" hyperextract
```

Expected: direct calls only remain in `hyperextract/utils/structured_output.py`.

- [ ] **Step 3: 百炼 CLI smoke test**

Run only when `~/.he/config.toml` points to Bailian LLM and Bailian embedder:

```bash
uv run he parse examples/zh/sushi.md -t general/biography_graph -o ./.tmp_bailian_smoke -l zh -f
```

Expected: extraction succeeds and writes `./.tmp_bailian_smoke/data.json`.

- [ ] **Step 4: 检查 smoke 输出**

Run:

```bash
uv run he info ./.tmp_bailian_smoke
```

Expected: command prints KA metadata and does not raise provider JSON prompt errors.

- [ ] **Step 5: 清理 smoke 输出**

Run:

```bash
rm -rf ./.tmp_bailian_smoke
```

Expected: directory removed.

- [ ] **Step 6: 最终状态检查**

Run:

```bash
git status --short
```

Expected: only intentional changes remain.

---

## 自检

- Spec 覆盖：prompt 注入、provider strategy、DeepSeek fallback、schema validation、接口稳定性都映射到具体任务。
- 计划完整性扫描：本文没有未展开的实现步骤或延后填充内容。
- 类型一致性：核心入口统一为 `create_structured_extractor(...)`，错误类型统一为 `StructuredExtractionError`，metadata 属性统一为 `_provider` 和 `_structured_output_strategy`。
