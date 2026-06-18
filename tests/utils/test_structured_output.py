from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, create_model
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


class FailingRunnable(RunnableSerializable):
    error: Exception
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def invoke(self, input: Any, config: Any = None) -> Any:
        raise self.error

    def batch(self, inputs: list[Any], config: Any = None, **kwargs: Any) -> list[Any]:
        return [self.invoke(item, config) for item in inputs]


class RecordingLLM:
    def __init__(
        self,
        provider: str = "",
        strategy_error: Exception | None = None,
        invoke_error: Exception | None = None,
    ):
        self._provider = provider
        self.strategy_error = strategy_error
        self.invoke_error = invoke_error
        self.calls: list[dict[str, Any]] = []

    def with_structured_output(
        self, schema: type[BaseModel], **kwargs: Any
    ) -> StaticRunnable:
        self.calls.append({"schema": schema, "kwargs": kwargs})
        if self.strategy_error:
            raise self.strategy_error
        if self.invoke_error:
            return FailingRunnable(error=self.invoke_error)
        return StaticRunnable(result=schema(name="structured"))

    def invoke(self, input: Any, config: Any = None) -> Any:
        return '{"name": "Runtime Fallback"}'

    def __call__(self, input: Any) -> Any:
        return self.invoke(input)

    def batch(self, inputs: list[Any], config: Any = None, **kwargs: Any) -> list[Any]:
        return [self.invoke(item, config) for item in inputs]


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


def test_json_fallback_accepts_top_level_array_for_list_wrapper_schema():
    class NodeSchema(BaseModel):
        name: str

    list_schema = create_model("NodeSchemaList", items=(list[NodeSchema], []))

    llm = RecordingLLM(provider="deepseek")
    llm._structured_output_strategy = "json_prompt_parser"
    extractor = create_structured_extractor(
        prompt="Extract node list from {source_text}.",
        schema=list_schema,
        llm_client=llm,
        operation="test.sample",
    )

    result = extractor._parse_json_response('[{"name": "Ada"}]')

    assert result.items == [NodeSchema(name="Ada")]


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


def test_deepseek_unsupported_strategy_falls_back_to_json_parser():
    llm = RecordingLLM(
        provider="deepseek",
        strategy_error=RuntimeError("response_format is unavailable"),
    )

    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    assert extractor._parse_json_response('{"name": "Grace"}') == SampleSchema(
        name="Grace"
    )


def test_deepseek_runtime_unsupported_strategy_falls_back_to_json_parser():
    llm = RecordingLLM(
        provider="deepseek",
        invoke_error=RuntimeError("response_format is unsupported"),
    )

    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    result = extractor.invoke({"source_text": "Ada Lovelace"})

    assert result == SampleSchema(name="Runtime Fallback")


def test_runtime_api_failure_does_not_fallback_to_json_parser():
    llm = RecordingLLM(
        provider="deepseek",
        invoke_error=RuntimeError("401 invalid api key"),
    )

    extractor = create_structured_extractor(
        prompt="Extract a name from {source_text}.",
        schema=SampleSchema,
        llm_client=llm,
        operation="test.sample",
    )

    with pytest.raises(RuntimeError) as exc:
        extractor.invoke({"source_text": "Ada Lovelace"})

    assert "401 invalid api key" in str(exc.value)
