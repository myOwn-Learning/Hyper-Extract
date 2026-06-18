"""Provider-compatible structured output helpers."""

from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel, ConfigDict, ValidationError
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


def is_strategy_unsupported_error(exc: Exception) -> bool:
    """Return True only for provider errors indicating unsupported structured mode."""
    text = str(exc).lower()
    markers = [
        "response_format",
        "unavailable",
        "unsupported",
        "not support",
        "invalid_parameter_error",
    ]
    return any(marker in text for marker in markers)


def _is_list_wrapper_schema(schema: Type[BaseModel]) -> bool:
    """Detect list-wrapper schemas with a single 'items' field."""
    if not getattr(schema, "model_fields", None):
        return False
    field_names = list(schema.model_fields.keys())
    return field_names == ["items"]


def create_structured_extractor(
    *,
    prompt: str,
    schema: Type[BaseModel],
    llm_client: Any,
    operation: str,
) -> RunnableSerializable:
    """Create a provider-compatible structured extraction runnable."""
    strategy = select_strategy(llm_client)

    if strategy == "json_prompt_parser" or _is_list_wrapper_schema(schema):
        return JsonPromptParserRunnable(
            prompt=ensure_json_instruction(prompt),
            target_schema=schema,
            llm_client=llm_client,
            operation=operation,
        )

    prompt_template = ChatPromptTemplate.from_template(ensure_json_instruction(prompt))

    if strategy == "tool_calling":
        try:
            structured_chain = prompt_template | llm_client.with_structured_output(
                schema,
                method="function_calling",
            )
        except TypeError:
            structured_chain = prompt_template | llm_client.with_structured_output(schema)
        except Exception as exc:
            if get_provider_name(llm_client) == "deepseek" and is_strategy_unsupported_error(exc):
                return JsonPromptParserRunnable(
                    prompt=ensure_json_instruction(prompt),
                    target_schema=schema,
                    llm_client=llm_client,
                    operation=operation,
                )
            raise
        fallback = JsonPromptParserRunnable(
            prompt=ensure_json_instruction(prompt),
            target_schema=schema,
            llm_client=llm_client,
            operation=operation,
        )
        return RuntimeFallbackRunnable(
            primary=structured_chain,
            fallback=fallback,
            provider=get_provider_name(llm_client),
        )

    return prompt_template | llm_client.with_structured_output(schema)


class RuntimeFallbackRunnable(RunnableSerializable):
    """Fallback to JSON parsing when a provider rejects a strategy at runtime."""

    primary: RunnableSerializable
    fallback: RunnableSerializable
    provider: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def invoke(self, input: Any, config: Any = None) -> BaseModel:
        try:
            return self.primary.invoke(input, config=config)
        except Exception as exc:
            # Fall back to JSON parser only for unsupported structured-output errors.
            if self.provider == "deepseek" and is_strategy_unsupported_error(exc):
                return self.fallback.invoke(input, config=config)
            raise

    def batch(
        self,
        inputs: list[Any],
        config: Any = None,
        **kwargs: Any,
    ) -> list[BaseModel]:
        try:
            return self.primary.batch(inputs, config=config, **kwargs)
        except Exception as exc:
            if self.provider == "deepseek" and is_strategy_unsupported_error(exc):
                return self.fallback.batch(inputs, config=config, **kwargs)
            raise


class JsonPromptParserRunnable(RunnableSerializable):
    """Runnable fallback that asks for JSON and validates it with Pydantic."""

    prompt: str
    target_schema: Type[BaseModel]
    llm_client: Any
    operation: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def invoke(self, input: Any, config: Any = None) -> BaseModel:
        prompt_template = ChatPromptTemplate.from_template(self.prompt)
        response = (prompt_template | self.llm_client).invoke(input, config=config)
        content = getattr(response, "content", response)
        return self._parse_json_response(str(content))

    def batch(
        self,
        inputs: list[Any],
        config: Any = None,
        **kwargs: Any,
    ) -> list[BaseModel]:
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

        if isinstance(payload, list) and getattr(self.target_schema, "model_fields", None):
            if list(self.target_schema.model_fields.keys()) == ["items"]:
                payload = {"items": payload}

        try:
            return self.target_schema.model_validate(payload)
        except ValidationError as exc:
            raise StructuredExtractionError(
                provider=provider,
                strategy="json_prompt_parser",
                operation=self.operation,
                reason="schema_validation_failed",
                detail=str(exc.errors()[0]) if exc.errors() else str(exc),
            ) from exc


def _extract_json_object(content: str) -> str:
    """Extract the first JSON object or array from a model response."""
    text = content.strip()
    if not text:
        raise ValueError("No JSON object or array found in provider response")

    if text[0] in ("{", "["):
        closing_char = "}" if text[0] == "{" else "]"
        if text.endswith(closing_char):
            return text

    start_positions = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
    if not start_positions:
        raise ValueError("No JSON object or array found in provider response")

    start = min(start_positions)
    closing_char = "}" if text[start] == "{" else "]"
    end = text.rfind(closing_char)
    if end == -1 or end <= start:
        raise ValueError("No JSON object or array found in provider response")
    return text[start : end + 1]
