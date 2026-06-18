# 常见问题

关于 Hyper-Extract 的常见问题解答。

---

## 通用问题

### Hyper-Extract 是什么？

Hyper-Extract 是一个基于大语言模型的知识提取框架，可以将非结构化文本转换为结构化的知识图谱、列表、模型等。

### 它可以用来做什么？

- 研究论文分析
- 知识库构建
- 文档处理
- 信息提取
- 问答系统

### 它是免费的吗？

本软件是开源的（Apache-2.0 协议）。您需要提供自己的 OpenAI API 密钥来进行大语言模型调用。

---

## 安装问题

### 系统要求是什么？

- Python 3.11+
- OpenAI API 密钥

### 如何安装？

```bash
pip install hyperextract
```

### 安装失败，提示 "No module named 'hyperextract'"

尝试：
```bash
pip install --upgrade hyperextract
```

或使用虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install hyperextract
```

---

## 配置问题

### 在哪里设置 API 密钥？

**选项 1**：命令行
```bash
he config init -k YOUR_API_KEY
```

**选项 2**：环境变量
```bash
export OPENAI_API_KEY=your-api-key
```

**选项 3**：.env 文件
```
OPENAI_API_KEY=your-api-key
```

### 可以使用其他大语言模型提供商吗？

可以，设置 base URL：
```bash
he config set llm.base_url https://your-provider.com/v1
```

### 支持哪些模型？

- OpenAI 模型（gpt-4o、gpt-4o-mini 等）
- 任何兼容 OpenAI API 的接口

---

## 使用问题

### 应该使用哪个模板？

参见[如何选择](../templates/how-to-choose.md)指南或使用：
```bash
he list template
```

### 如何处理 PDF 文件？

先转换为文本：
```bash
pdftotext document.pdf document.txt
he parse document.txt -t general/graph -l zh
```

### 可以处理多个文档吗？

**选项 1**：增量添加
```bash
he parse doc1.md -t general/graph -o ./ka/ -l zh
he feed ./ka/ doc2.md
he feed ./ka/ doc3.md
```

**选项 2**：处理目录
```bash
he parse ./docs/ -t general/graph -o ./ka/ -l zh
```

### 如何提取中文内容？

```bash
he parse doc.md -t general/biography_graph -l zh
```

---

## 性能问题

### 为什么提取速度很慢？

- 长文档会被分块并行处理
- 每个分块都需要调用大语言模型
- 建议在批量处理时使用 `--no-index`

### 如何加快速度？

1. 使用更小的分块大小
2. 如果达到速率限制，减少 `max_workers`
3. 并行处理文档（手动）

### 大文档导致内存不足？

分批处理：
```python
for batch in chunks(documents, 5):
    for doc in batch:
        ka.feed_text(doc)
    ka.dump("./checkpoint/")
```

---

## 结果问题

### 数据存储在哪里？

```
./output/
├── data.json      # 提取的知识
├── metadata.json  # 提取信息
└── index/         # 搜索索引
```

### 如何可视化结果？

```bash
he show ./output/
```

或在 Python 中：
```python
# 构建索引以支持可视化中的交互式搜索/对话
result.build_index()

result.show()
```

![交互式可视化](../../assets/zh_show.jpg)

### 可以导出为其他格式吗？

```python
import json

# 导出为 JSON
json_data = result.data.model_dump_json()

# 导出为字典
data_dict = result.data.model_dump()
```

---

## 故障排除

### "API key not found"

运行：
```bash
he config init -k YOUR_API_KEY
```

### "Template not found"

列出可用模板：
```bash
he list template
```

### "Index not found" 错误

构建索引：
```bash
he build-index ./output/
```

### 搜索没有返回结果

尝试：
- 使用不同的搜索词
- 增加 `top_k`：`he search ./ka/ "查询" -n 10`
- 检查索引是否已构建：`he info ./ka/`

---

## 高级功能

### 可以创建自定义模板吗？

可以！参见[自定义模板](../python/guides/custom-templates.md)。

### 可以使用自己的提取方法吗？

可以，实现并注册：
```python
from hyperextract.methods import register_method

class MyMethod:
    def extract(self, text):
        # 您的逻辑
        pass

register_method("my_method", MyMethod, "graph", "Description")
```

### 如何集成到我的应用程序中？

```python
from hyperextract import Template

class MyApp:
    def __init__(self):
        self.ka = Template.create("general/graph", "zh")
    
    def process_document(self, text):
        return self.ka.parse(text)
```

---

## 获取更多帮助

- [GitHub Issues](https://github.com/myOwn-Learning/Hyper-Extract/issues)
- [故障排除指南](troubleshooting.md)
- [CLI 文档](../cli/index.md)
- [Python SDK](../python/index.md)
