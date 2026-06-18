"""
Hyper RAG 示例：苏轼传记超图抽取

使用 Hyper RAG 从苏轼传记中提取超图知识。

Usage:
    python examples/zh/methods/hyper_rag_demo.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from hyperextract import create_client
from hyperextract.methods.rag import Hyper_RAG

project_root = Path(__file__).resolve().parent.parent.parent.parent

load_dotenv(project_root / ".env")

INPUT_FILE = project_root / "examples" / "zh" / "sushi.md"
QUESTION_FILE = project_root / "examples" / "zh" / "sushi_question.md"
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
PLACEHOLDER_API_KEYS = {
    "",
    "sk-your-api-key-here",
    "your-key",
    "your_api_key",
    "your-bailian-api-key-here",
    "YOUR_BAILIAN_API_KEY",
}


def create_bailian_client_from_env():
    api_key = (
        os.environ.get("BAILIAN_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    ).strip()
    if api_key in PLACEHOLDER_API_KEYS:
        raise RuntimeError(
            "请先在 .env 中设置有效的百炼 API Key，例如："
            "BAILIAN_API_KEY=sk-...。当前值为空或仍是示例占位值。"
        )

    llm_model = os.environ.get("BAILIAN_LLM_MODEL", "qwen3.6-plus")
    embedding_model = os.environ.get("BAILIAN_EMBEDDING_MODEL", "text-embedding-v4")
    base_url = os.environ.get("OPENAI_BASE_URL", BAILIAN_BASE_URL)

    return create_client(
        llm=f"bailian:{llm_model}@{base_url}",
        embedder=f"bailian:{embedding_model}@{base_url}",
        api_key=api_key,
    )

if __name__ == "__main__":
    with open(INPUT_FILE, encoding="utf-8") as f:
        text = f.read()
    with open(QUESTION_FILE, encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]

    llm, embedder = create_bailian_client_from_env()

    print("=" * 60)
    print("Hyper RAG 示例")
    print("=" * 60)

    rag = Hyper_RAG(llm_client=llm, embedder=embedder)
    rag.feed_text(text)

    print("从苏轼传记中提取超图...")
    print(f"\n✓ 提取了 {len(rag.nodes)} 个实体，{len(rag.edges)} 个超边\n")

    print("-" * 60)
    print("问答")
    print("-" * 60)
    for q in questions:
        print(f"\n问: {q}")
        try:
            result = rag.chat(q)
            print(f"答: {result.content}")
        except Exception as e:
            print(f"错误: {e}")

    rag.show()
