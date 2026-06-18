## Language

- 当规则冲突时，以序号顺序为准（1 为最高优先级）。
1) 所有面向人类的自然语言段落使用简体中文，包括设计文档、规格说明、计划、任务清单、评审总结，以及 OpenSpec artifacts 的自然语言部分（例如 OpenSpec 格式的规范说明、YAML/JSON 规范文件和示例文档）。
2) 在文档中出现的代码标识符、命令、文件路径、API 名称、依赖包名、模型名等必须保持英文并保留其原始拼写与大小写，不翻译或本地化。中文正文中的这些英文项应使用单反引号 `likeThis` 标注，代码块按原样显示。
3) 对于工具或规范要求的机器可解析字段（例如 YAML/JSON keys、frontmatter、CI 配置字段、自动生成的元数据、自动化脚本中的键名），必须保持英文且不得更改格式。代码注释、提交信息、版本控制消息和自动生成的元数据应保留原文或保持英文键名；界面可本地化字符串需按用户另行说明。
- 遇到不明术语或专有格式时，先询问或在文档中注释定义该术语，并按用户确认处理。

## 项目概述

`Hyper-Extract`（PyPI 包名 `hyperextract`，CLI 命令 `he`）是一个基于大语言模型（LLM）的知识提取与演进框架，目标是把非结构化文本转换为持久化、强类型、可搜索的**知识摘要（Knowledge Abstract，简称 KA）**。

核心能力：

- **8 种 AutoType**：`AutoModel`、`AutoList`、`AutoSet`、`AutoGraph`、`AutoHypergraph`、`AutoTemporalGraph`、`AutoSpatialGraph`、`AutoSpatioTemporalGraph`。
- **10+ 提取引擎**：`Light_RAG`、`Hyper_RAG`、`HyperGraph_RAG`、`Cog_RAG`、`Graph_RAG`、`iText2KG`、`iText2KG_Star`、`KG_Gen`、`Atom` 等，统一注册在 `hyperextract.methods.registry`。
- **80+ YAML 模板**：位于 `hyperextract/templates/presets/`，覆盖 `general`、`finance`、`legal`、`medicine`、`tcm`、`industry` 等领域。
- **增量演进**：通过 `feed_text()` 持续合并新文档，自动去重并合并已有知识。
- **语义搜索与问答**：基于 `FAISS` 向量索引实现 `search()` 与 `chat()`。
- **可视化**：调用 `ontosight` 在浏览器中展示图谱。

项目采用**三层架构**：`AutoTypes`（数据结构层） → `Methods`（算法层） → `Templates`（零代码模板层）。

## 技术栈与关键配置

- **语言与构建**：Python `>=3.11`（`.python-version` 指定 `3.11`），构建后端为 `hatchling`，包管理器使用 `uv`（已提交 `uv.lock`）。
- **核心依赖**：`pydantic`、`langchain`、`langchain-openai`、`langchain-community`、`faiss-cpu`、`ontomem`、`ontosight`、`semhash`、`python-dotenv`、`structlog`。
- **可选依赖**：`hyperextract[anthropic]`（`langchain-anthropic`）、`hyperextract[google]`（`langchain-google-genai`）、`hyperextract[all]`。
- **CLI 依赖**：`typer`、`rich`、`tomli-w`。
- **文档依赖**：`mkdocs`、`mkdocs-material`、`mkdocs-static-i18n`、`mkdocstrings[python]`、`pymdown-extensions`、`mike`。
- **测试依赖**：`pytest`、`pytest-cov`。
- **入口配置**：`pyproject.toml` 中 `[project.scripts]` 定义 `he = "hyperextract.cli:app"`。
- **代码质量**：`pyproject.toml` 中 `[tool.ruff.lint]` 仅忽略 `E731`。

## 项目结构

```
.
├── hyperextract/              # 主包
│   ├── types/                 # AutoType 基类与 8 种具体类型
│   │   ├── base.py            # BaseAutoType：抽取、合并、索引、序列化生命周期
│   │   ├── model.py/list.py/set.py
│   │   ├── graph.py           # AutoGraph（节点+边）
│   │   ├── hypergraph.py      # AutoHypergraph（超边）
│   │   ├── temporal_graph.py  # AutoTemporalGraph（时序）
│   │   ├── spatial_graph.py   # AutoSpatialGraph（空间）
│   │   └── spatio_temporal_graph.py
│   ├── methods/               # 提取方法注册表与实现
│   │   ├── registry.py        # 统一方法注册中心
│   │   ├── rag/               # RAG 类方法
│   │   └── typical/           # 经典方法（iText2KG、KG_Gen、Atom 等）
│   ├── utils/                 # 工具模块
│   │   ├── client.py          # LLM/Embedder 客户端工厂
│   │   ├── logging.py         # structlog 日志配置
│   │   ├── structured_output.py # 多 Provider 结构化输出兼容层
│   │   └── template_engine/   # YAML 模板解析、Gallery、Factory
│   ├── templates/             # YAML 模板与设计指南
│   │   ├── presets/           # 按领域分类的 80+ 模板
│   │   ├── DESIGN_GUIDE.md    # 英文模板设计指南
│   │   └── DESIGN_GUIDE_zh.md # 中文模板设计指南
│   └── cli/                   # Typer 命令行入口
│       ├── cli.py             # `he` 主命令与核心子命令
│       ├── config.py          # `~/.he/config.toml` 配置管理
│       ├── utils.py           # CLI 公共工具
│       └── commands/          # `list`、`config` 子命令
├── tests/                     # 测试集合
│   ├── conftest.py            # pytest 配置、自动切换真实 API / Mock
│   ├── mocks.py               # MockChatModel、MockEmbeddings
│   ├── fixtures/              # 测试数据与 schema
│   ├── integration/           # 集成测试（需 OPENAI_API_KEY）
│   ├── types/                 # AutoType 单元测试
│   ├── template_engine/       # 模板引擎测试
│   ├── utils/                 # 工具模块测试
│   └── cli/                   # CLI 测试
├── examples/                  # 中英双语示例
│   ├── en/ / zh/              # autotypes、methods、templates 示例
│   └── providers/             # openai、bailian、vllm 接入示例
├── docs/                      # MkDocs 双语文档（en / zh）
├── openspec/                  # OpenSpec 工作流配置
├── .github/workflows/         # CI/CD
├── pyproject.toml
├── uv.lock
├── mkdocs.yml
├── docs_hooks.py
└── README.md / README_ZH.md
```

## 运行时架构

1. **模板解析**：`Template.create("general/graph", language="zh")` 通过 `Gallery` 加载 YAML，经 `TemplateFactory` 生成对应 AutoType 实例。
2. **客户端创建**：
   - CLI 从 `~/.he/config.toml` 读取配置，支持 `openai`、`bailian`、`vllm` 三种 Provider 预设。
   - Python API 可通过 `create_client("bailian:qwen-plus", api_key=...)` 或 `create_client(llm="vllm:Qwen3.5-9B@...", embedder="vllm:bge-m3@...")` 创建。
   - 自定义非 OpenAI 端点使用 `CompatibleEmbeddings` 避免 `tiktoken` 预分词问题。
3. **抽取流程**：`BaseAutoType._extract_data()` → 文本分块（`RecursiveCharacterTextSplitter`）→ 并发 LLM 结构化抽取 → `_filter_none_results()` → `merge_batch_data()`。
4. **结构化输出策略**：`structured_output.py` 自动选择 `langchain_structured`、`tool_calling` 或 `json_prompt_parser` 回退，兼容 `deepseek` 等 Provider。
5. **合并与去重**：图类使用 `ontomem` 的 `MergeStrategy`/`BaseMerger` 对节点和边做智能合并。
6. **索引与检索**：`build_index()` 使用 `FAISS` 构建向量索引；`search()` 语义检索；`chat()` 用检索结果作为上下文调用 LLM。
7. **序列化**：`dump(folder)` 生成 `data.json` + `metadata.json` + `index/`；`load(folder)` 恢复状态。

## 构建、安装与运行

推荐在仓库根目录使用 `uv`：

```bash
# 安装项目及所有可选/开发依赖（使用 uv.lock）
uv sync --all-extras --all-groups

# 以可编辑模式安装（等价于 CI 中的用法）
uv pip install -e ".[all]"
uv pip install pytest pytest-cov

# 运行 CLI
he --help
he parse examples/en/tesla.md -t general/biography_graph -o ./output/ -l en

# 本地文档预览
uv run mkdocs serve
```

首次使用 CLI 前需配置 LLM/Embedder：

```bash
he config init -k YOUR_OPENAI_API_KEY
# 或分别设置
he config llm --provider openai --model gpt-4o-mini --api-key YOUR_KEY
he config embedder --provider openai --model text-embedding-3-small --api-key YOUR_KEY
```

Python API 最小示例：

```python
from hyperextract import Template

ka = Template.create("general/biography_graph", language="en")
with open("examples/en/tesla.md") as f:
    ka.feed_text(f.read())
ka.build_index()
ka.dump("./output/")
ka.show()
```

## 测试说明

测试入口为 `pytest`。`tests/conftest.py` 会自动检测环境：

- 若存在有效 `OPENAI_API_KEY`，则使用真实 `ChatOpenAI` / `OpenAIEmbeddings`。
- 若不存在，则回退到 `tests/mocks.py` 中的 `MockChatModel` / `MockEmbeddings`。

常用命令：

```bash
# 完整测试（当前环境无 API key 时会自动使用 Mock）
uv run pytest

# 强制使用 Mock（CI 采用此方式）
OPENAI_API_KEY="" uv run pytest

# 仅运行集成测试（需要真实 API key）
uv run pytest -m integration -v

# 带覆盖率
uv run pytest --cov=hyperextract --cov-report=xml --cov-report=term -v
```

注意：

- 集成测试文件 `tests/integration/test_real_extraction.py` 标记了 `@pytest.mark.integration`。
- 如果本地 `.env` 中配置了 `OPENAI_API_KEY` 但对应的账号没有目标模型访问权限，部分测试会失败。此时可取消该环境变量以强制走 Mock 路径。

## 代码风格与开发约定

- **格式化与静态检查**：使用 `ruff`。`pyproject.toml` 中仅忽略 `E731`。
  ```bash
  ruff check hyperextract
  ruff format --check hyperextract
  ```
- **文档字符串**：采用 Google 风格，以便 `mkdocstrings[python]` 生成 API 文档。
- **日志**：统一通过 `hyperextract.utils.logging.get_logger(__name__)` 获取 `structlog` logger；日志级别由环境变量 `HYPER_EXTRACT_LOG_LEVEL` 控制（默认 `WARNING`），`HYPER_EXTRACT_LOG_FILE` 可指定输出文件。
- **类型提示**：广泛使用 `pydantic.BaseModel` 定义 schema，AutoType 使用泛型 `Generic[NodeSchema, EdgeSchema]`。
- **模板 YAML 约定**（详见 `hyperextract/templates/DESIGN_GUIDE_zh.md`）：
  - 模板名使用 `CamelCase`，字段名使用 `snake_case`。
  - 关系类型字段固定名为 `type`，时间字段固定名为 `time`。
  - `description`、`guideline` 等人类可读字段提供 `zh`/`en` 双语。
- **代码中的英文标识符**：文件路径、API、命令、包名、模型名等保持英文，不在中文正文中翻译。

## 安全与隐私

- **API Key 管理**：优先写入 `~/.he/config.toml`（CLI 管理），或设置环境变量 `OPENAI_API_KEY` / `OPENAI_BASE_URL`。`.env.example` 仅作示例，真实 `.env` 已加入 `.gitignore`，切勿提交密钥。
- **本地部署**：`vllm` Provider 支持 `api_key="dummy"`，所有数据留在本地。
- **分发包安全**：`pyproject.toml` 中 `tool.hatch.build.exclude` 已排除 `.env`、`.env.example`、测试、文档等敏感/非必要文件。
- **兼容端点保护**：`CompatibleEmbeddings` 对非 OpenAI 端点使用字符串输入而非预分词 token，避免泄露或兼容性问题。
- **超时与重试**：LLM 默认超时 180 秒、最大重试 2 次，可通过 `HE_LLM_TIMEOUT` / `HE_LLM_MAX_RETRIES` 覆盖。

## CI/CD 与发布

`.github/workflows/` 包含四个工作流：

- **`test.yml`**：在 `ubuntu-latest` / `macos-latest` 上针对 Python 3.11/3.12 运行 `pytest` 并上传覆盖率到 Codecov。运行时会设置 `OPENAI_API_KEY=""` 强制使用 Mock。
- **`lint.yml`**：对 `hyperextract/` 运行 `ruff check` 与 `ruff format --check`。
- **`integration.yml`**：每日 UTC 02:00 触发，使用仓库密文 `OPENAI_API_KEY` 运行集成测试。
- **`docs.yml`**：当 `docs/`、`mkdocs.yml`、`pyproject.toml` 等变更时，使用 `mike` 部署 MkDocs 到 GitHub Pages。
- **`publish.yml`**：在 Release 发布或手动触发时，使用 `hatchling`/`build` 构建并发布到 PyPI（或 Test PyPI）。

## 常用入口速查

| 用途 | 入口 |
|------|------|
| Python 包导入 | `from hyperextract import Template, create_client, AutoGraph` |
| CLI 入口 | `he`（由 `hyperextract.cli:app` 提供）|
| 模板列表 | `he list template` / `Template.list()` |
| 方法列表 | `he list method` |
| 全局配置 | `~/.he/config.toml` |
| 文档构建 | `mkdocs serve` / `mike deploy latest` |
| 默认 chunk 大小 | `2048` 字符，overlap `256` |
