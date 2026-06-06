"""Client Factory - Create OpenAI LLM and Embedder clients from config.

Provides three levels of API:
    - create_client(): Unified creation for both LLM and Embedder
    - create_llm() / create_embedder(): Separate creation for advanced use
    - get_client(): Read from config.toml (backward compatible)

String shorthand format: provider:model@url
    - "bailian"              → provider only, use preset defaults
    - "bailian:qwen-plus"    → provider + model, use preset URL
    - "vllm:Qwen3.5-9B@http://localhost:8000/v1" → full specification
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".he"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_LLM_TIMEOUT_SECONDS = 60.0
DEFAULT_LLM_MAX_RETRIES = 2

# Official OpenAI API base URL — only this endpoint accepts pre-tokenized input
OPENAI_API_URL = "https://api.openai.com/v1"

# Provider presets: base_url and default models for each provider
PROVIDER_PRESETS: Dict[str, Dict[str, str | None]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_llm": "gpt-4o-mini",
        "default_embedder": "text-embedding-3-small",
    },
    "bailian": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_llm": "qwen3.6-plus",
        "default_embedder": "text-embedding-v4",
    },
    "vllm": {
        "base_url": None,
        "default_llm": None,
        "default_embedder": None,
    },
}


class CompatibleEmbeddings(Embeddings):
    """Embeddings for OpenAI-compatible providers that only accept string input.

    langchain_openai's OpenAIEmbeddings with tiktoken_enabled=True sends
    pre-tokenized integer lists to the API, which OpenAI supports but most
    OpenAI-compatible providers (Ollama, LiteLLM, etc.) do not. This class
    works around that by always sending strings, using tiktoken for chunking
    with a fallback encoding when the model name isn't tiktoken-compatible.
    """

    def __init__(
        self,
        model: str = "text-embedding-ada-002",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_batch_size: int = 10,
        chunk_size: Optional[int] = None,
        max_retries: int = 2,
        **kwargs: Any,
    ):
        from openai import OpenAI

        self._client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
            base_url=base_url,
            max_retries=max_retries,
        )
        self._model = model

        # max_batch_size caps how many inputs are sent per embeddings request.
        # Many OpenAI-compatible providers reject large batches (e.g. Bailian /
        # DashScope caps at 10), so the default is intentionally conservative.
        # `chunk_size` is the legacy name for this knob and is kept as an alias.
        self._max_batch_size = chunk_size if chunk_size is not None else max_batch_size

        # Determine the tiktoken encoding to use for chunking
        import tiktoken

        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Model not recognized by tiktoken; use cl100k_base (used by
            # text-embedding-ada-002, text-embedding-3-small, etc.)
            logger.debug(
                "Model '%s' not recognized by tiktoken, using cl100k_base encoding",
                model,
            )
            self._encoding = tiktoken.get_encoding("cl100k_base")

        # Max tokens per request (8191 is the limit for most OpenAI embedders)
        self._max_tokens = kwargs.get("embedding_ctx_length", 8191)

    def _split_texts(self, texts: List[str]) -> List[Tuple[str, int]]:
        """Split texts into chunks that fit within token limits.

        Returns list of (text_chunk, original_index) tuples.
        """
        chunks: List[Tuple[str, int]] = []
        for i, text in enumerate(texts):
            tokens = self._encoding.encode(text)
            if len(tokens) <= self._max_tokens:
                chunks.append((text, i))
            else:
                # Split into chunks
                for j in range(0, len(tokens), self._max_tokens):
                    chunk_tokens = tokens[j : j + self._max_tokens]
                    chunk_text = self._encoding.decode(chunk_tokens)
                    chunks.append((chunk_text, i))
        return chunks

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        chunks = self._split_texts(texts)
        if not chunks:
            return []

        # Group chunks into batches no larger than max_batch_size
        all_embeddings: List[Optional[List[float]]] = [None] * len(texts)
        batch: List[Tuple[str, int]] = []

        def _embed_batch(b: List[Tuple[str, int]]) -> None:
            response = self._client.embeddings.create(
                input=[text for text, _ in b],
                model=self._model,
            )
            for (text, orig_idx), emb_data in zip(b, response.data, strict=False):
                if all_embeddings[orig_idx] is None:
                    all_embeddings[orig_idx] = emb_data.embedding
                else:
                    # Average embeddings for multi-chunk texts
                    prev = all_embeddings[orig_idx]
                    curr = emb_data.embedding
                    all_embeddings[orig_idx] = [
                        (a + b) / 2 for a, b in zip(prev, curr, strict=False)
                    ]

        for chunk in chunks:
            batch.append(chunk)
            if len(batch) >= self._max_batch_size:
                _embed_batch(batch)
                batch = []

        if batch:
            _embed_batch(batch)

        # Fill in any missing embeddings with empty-string embedding
        missing_indices = [i for i, e in enumerate(all_embeddings) if e is None]
        if missing_indices:
            response = self._client.embeddings.create(
                input="",
                model=self._model,
            )
            default_emb = response.data[0].embedding
            for i in missing_indices:
                all_embeddings[i] = default_emb

        return all_embeddings  # type: ignore[return-value]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


def _parse_client_spec(
    spec: str | dict,
    *,
    api_key: str = "",
    default_kind: str = "llm",
) -> Dict[str, Any]:
    """Parse a client specification string or dict into a config dict.

    String formats:
        - "bailian"              → provider only, use preset defaults
        - "bailian:qwen-plus"    → provider + model, use preset URL
        - "vllm:Qwen3.5-9B@http://localhost:8000/v1" → full specification

    Args:
        spec: String shorthand or dict config.
        api_key: Fallback API key.
        default_kind: "llm" or "embedder", used for default model selection.

    Returns:
        Dict with keys: provider, model, base_url, api_key
    """
    if isinstance(spec, dict):
        return {
            "provider": spec.get("provider", ""),
            "model": spec.get("model", ""),
            "base_url": spec.get("base_url", ""),
            "api_key": spec.get("api_key") or api_key,
            **{
                k: v
                for k, v in spec.items()
                if k not in ("provider", "model", "base_url", "api_key")
            },
        }

    # Parse string shorthand: provider:model@url
    provider = ""
    model = ""
    base_url = ""

    parts = spec.split(":", 1)
    provider = parts[0].strip()

    if len(parts) > 1:
        rest = parts[1].strip()
        if "@" in rest:
            model, base_url = rest.split("@", 1)
            model = model.strip()
            base_url = base_url.strip()
        else:
            model = rest.strip()

    # Fill defaults from preset
    preset = PROVIDER_PRESETS.get(provider, {})
    if not base_url:
        preset_url = preset.get("base_url")
        if preset_url is not None:
            base_url = preset_url
    if not model:
        default_key = f"default_{default_kind}"
        model = preset.get(default_key) or ""

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
    }


def create_llm(
    spec: str | dict,
    *,
    api_key: str = "",
    **kwargs: Any,
) -> BaseChatModel:
    """Create an LLM client from a specification string or dict.

    Args:
        spec: String shorthand (e.g. "bailian:qwen-plus") or dict config.
        api_key: API key fallback.
        **kwargs: Extra args forwarded to ChatOpenAI (e.g. temperature).

    Returns:
        Configured ChatOpenAI instance.

    Examples:
        >>> llm = create_llm("bailian:qwen-plus", api_key="sk-xxx")
        >>> llm = create_llm("vllm:Qwen3.5-9B@localhost:8000/v1", api_key="dummy")
        >>> llm = create_llm({"provider": "bailian", "model": "qwen-plus", "temperature": 0.5})
    """
    config = _parse_client_spec(spec, api_key=api_key, default_kind="llm")
    config.update(kwargs)

    from langchain_openai import ChatOpenAI

    timeout = config.get("timeout", config.get("request_timeout"))
    if timeout is None:
        timeout = float(os.environ.get("HE_LLM_TIMEOUT", DEFAULT_LLM_TIMEOUT_SECONDS))

    max_retries = config.get("max_retries")
    if max_retries is None:
        max_retries = int(os.environ.get("HE_LLM_MAX_RETRIES", DEFAULT_LLM_MAX_RETRIES))

    llm = ChatOpenAI(
        model=config["model"],
        api_key=config["api_key"] or os.environ.get("OPENAI_API_KEY", ""),
        base_url=config.get("base_url") or None,
        temperature=config.get("temperature", 0),
        timeout=timeout,
        max_retries=max_retries,
    )
    object.__setattr__(llm, "_provider", config.get("provider", ""))
    object.__setattr__(
        llm,
        "_structured_output_strategy",
        config.get("structured_output_strategy", ""),
    )
    return llm


def create_embedder(
    spec: str | dict,
    *,
    api_key: str = "",
    **kwargs: Any,
) -> Embeddings:
    """Create an Embedder client from a specification string or dict.

    Args:
        spec: String shorthand (e.g. "bailian:text-embedding-v4") or dict config.
        api_key: API key fallback.
        **kwargs: Extra args forwarded to the embedder class.

    Returns:
        Configured OpenAIEmbeddings or CompatibleEmbeddings instance.

    Examples:
        >>> emb = create_embedder("bailian", api_key="sk-xxx")
        >>> emb = create_embedder("vllm:bge-m3@localhost:8001/v1", api_key="dummy")
    """
    config = _parse_client_spec(spec, api_key=api_key, default_kind="embedder")

    base_url = config.get("base_url", "")
    uses_custom = bool(base_url and base_url.rstrip("/") != OPENAI_API_URL)

    if uses_custom:
        return CompatibleEmbeddings(
            model=config["model"],
            api_key=config["api_key"] or os.environ.get("OPENAI_API_KEY", ""),
            base_url=base_url,
            **kwargs,
        )
    else:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config["model"],
            api_key=config["api_key"] or os.environ.get("OPENAI_API_KEY", ""),
            **kwargs,
        )


def create_client(
    llm: str | dict | None = None,
    embedder: str | dict | None = None,
    *,
    provider: str = "",
    api_key: str = "",
    **kwargs: Any,
) -> Tuple[BaseChatModel, Embeddings]:
    """Create both LLM and Embedder clients in one call.

    Supports three patterns:

    **Pattern A: Single provider string (cloud API, simplest)**
    >>> llm, emb = create_client("bailian", api_key="sk-xxx")
    # Uses preset defaults: qwen3.6-plus + text-embedding-v4

    **Pattern B: Separate specs (vLLM, two independent services)**
    >>> llm, emb = create_client(
    ...     llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
    ...     embedder="vllm:bge-m3@http://localhost:8001/v1",
    ...     api_key="dummy",
    ... )

    **Pattern C: Mixed deployment**
    >>> llm = create_client(
    ...     llm="bailian:qwen-plus",
    ...     embedder="vllm:bge-m3@localhost:8001/v1",
    ...     api_key="sk-xxx",
    ... )

    Args:
        llm: LLM spec string/dict, or None to auto-infer from provider.
        embedder: Embedder spec string/dict, or None to auto-infer from provider.
        provider: Fallback provider when llm/embedder are bare strings without provider prefix.
        api_key: Shared API key for both services.
        **kwargs: Extra args forwarded to ChatOpenAI (e.g. temperature).

    Returns:
        (llm_client, embedder_client) tuple.
    """
    # Pattern A: Single provider shorthand
    if llm is None and embedder is None:
        if not provider:
            raise ValueError(
                "Must provide llm=, embedder=, or provider= argument.\n"
                "Examples:\n"
                '  create_client("bailian", api_key="...")\n'
                '  create_client(llm="bailian:qwen-plus", embedder="bailian", api_key="...")\n'
                '  create_client(llm="vllm:Qwen3.5-9B@localhost:8000", '
                'embedder="vllm:bge-m3@localhost:8001", api_key="dummy")'
            )
        # Use provider preset defaults for both
        llm = provider
        embedder = provider

    # Parse llm config
    llm_config = _parse_client_spec(
        llm or provider, api_key=api_key, default_kind="llm"
    )
    llm_config.update(kwargs)

    # Parse embedder config
    # For cloud providers, embedder defaults to llm's provider
    embedder_spec = embedder or llm_config.get("provider", "")
    emb_config = _parse_client_spec(
        embedder_spec, api_key=api_key, default_kind="embedder"
    )

    # Build clients
    llm_client = create_llm(llm_config, api_key=api_key)
    embedder_client = create_embedder(emb_config, api_key=api_key)

    return llm_client, embedder_client


def get_client(config_path: str | Path = None) -> Tuple[BaseChatModel, Embeddings]:
    """Get OpenAI LLM client and Embedder from config.

    Backward-compatible: reads ~/.he/config.toml.

    Args:
        config_path: Config file path, default ~/.he/config.toml

    Returns:
        (llm_client, embedder) tuple

    Examples:
        >>> from hyperextract.utils import get_client
        >>> llm, emb = get_client()
        >>> # Or with custom config path
        >>> llm, emb = get_client("/path/to/config.toml")
    """
    from hyperextract.cli.config import ConfigManager

    path = Path(config_path) if config_path else DEFAULT_CONFIG_FILE
    manager = ConfigManager(path)

    llm_config = manager.get_llm_config()
    emb_config = manager.get_embedder_config()

    # Build LLM client
    llm_client = create_llm(
        {
            "provider": llm_config.provider,
            "model": llm_config.model,
            "base_url": llm_config.base_url,
            "api_key": llm_config.api_key,
        }
    )

    # Build embedder client
    embedder_client = create_embedder(
        {
            "provider": emb_config.provider,
            "model": emb_config.model,
            "base_url": emb_config.base_url,
            "api_key": emb_config.api_key,
        }
    )

    return llm_client, embedder_client
