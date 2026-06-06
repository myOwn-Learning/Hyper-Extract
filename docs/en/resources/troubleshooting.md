# Troubleshooting

Solutions to common issues.

---

## Installation Issues

### pip install fails

**Problem**: Installation fails with errors

**Solutions**:

1. Upgrade pip: `pip install --upgrade pip`
2. Use Python 3.11+: `python --version`
3. Install in virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install hyperextract
   ```

### ImportError: No module named 'hyperextract'

**Problem**: Can't import after installation

**Solutions**:

1. Check Python version: `python --version` (need 3.11+)
2. Verify installation: `pip list | grep hyper`
3. Check virtual environment is activated
4. Reinstall: `pip install --force-reinstall hyperextract`

---

## Configuration Issues

### API Key Not Found

**Error**: `No API key configured`

**Solutions**:

1. **CLI Configuration** (recommended):
   ```bash
   he config init -k YOUR_API_KEY
   ```

2. **Environment Variable**:
   ```bash
   export OPENAI_API_KEY=your-api-key
   ```

3. **Verify Configuration**:
   ```bash
   he config show
   ```

### Invalid API Key

**Error**: `Authentication failed`

**Solutions**:

1. Verify key is correct
2. Check for extra spaces
3. Try regenerating key in OpenAI dashboard
4. Check if key has available credits

---

## Runtime Issues

### Template Not Found

**Error**: `Template 'xxx' not found`

**Solutions**:

1. **List available templates**:
   ```bash
   he list template
   ```

2. **Check spelling**:
   ```bash
   # Correct
   he parse doc.md -t general/biography_graph
   
   # Incorrect
   he parse doc.md -t general/biography
   ```

3. **Use Python to search**:
   ```python
   from hyperextract import Template
   templates = Template.list(filter_by_query="bio")
   ```

### Language Required

**Error**: `--lang is required`

**Solution**:

```bash
# Add language flag
he parse doc.md -t general/biography_graph -o ./out/ -l en
```

Note: Method templates don't require language.

### Output Directory Exists

**Error**: `Output directory already exists`

**Solutions**:

1. **Force overwrite**:
   ```bash
   he parse doc.md -t general/graph -o ./out/ -l en -f
   ```

2. **Use different directory**:
   ```bash
   he parse doc.md -t general/graph -o ./out2/ -l en
   ```

3. **Remove existing**:
   ```bash
   rm -rf ./out/
   he parse doc.md -t general/graph -o ./out/ -l en
   ```

---

## Index and Search Issues

### Index Not Found

**Error**: `Search index not built`

**Solution**:

```bash
he build-index ./output/
```

### Search Returns Empty

**Problem**: `he search` finds no results

**Solutions**:

1. **Verify index exists**:
   ```bash
   he info ./output/
   # Should show: Index: Built
   ```

2. **Try different query**:
   ```bash
   he search ./output/ "different keywords"
   ```

3. **Increase top_k**:
   ```bash
   he search ./output/ "query" -n 10
   ```

4. **Check data exists**:
   ```bash
   he info ./output/
   # Should show Nodes > 0
   ```

### Chat Fails

**Error**: `Chat failed: index not found`

**Solution**:

```bash
he build-index ./output/
he talk ./output/ -q "your question"
```

---

## Performance Issues

### Extraction is Very Slow

**Problem**: Taking too long to process

**Solutions**:

1. **Skip index during batch**:
   ```bash
   he parse doc.md -t general/graph -o ./out/ -l en --no-index
   ```

2. **Reduce chunk size** (Python):
   ```python
   ka = Template.create("general/graph", "en")
   ka.chunk_size = 1024  # Default: 2048
   ```

3. **Reduce workers** (if hitting rate limits):
   ```python
   ka = Template.create("general/graph", "en")
   ka.max_workers = 5  # Default: 10
   ```

4. **Tune LLM request timeout** (when provider responses are slow):
   ```bash
   HE_LLM_TIMEOUT=120 he parse doc.md -t general/graph -o ./out/ -l en
   ```

   The default LLM timeout is 60 seconds. Set `HE_LLM_MAX_RETRIES=0` while debugging provider latency to avoid retries extending the wait.

### Out of Memory

**Problem**: Process killed or memory error

**Solutions**:

1. **Process smaller chunks**:
   ```python
   for chunk in split_document(text, chunk_size=1000):
       result.feed_text(chunk)
   ```

2. **Save intermediate results**:
   ```python
   for i, doc in enumerate(documents):
       result.feed_text(doc)
       if i % 5 == 0:
           result.dump(f"./checkpoint_{i}/")
   ```

3. **Don't build index for intermediate steps**:
   ```python
   # Build only at the end
   result.build_index()
   ```

---

## Data Issues

### No Entities Extracted

**Problem**: Empty result

**Solutions**:

1. **Check input text**:
   ```bash
   wc -l document.md  # Check not empty
   ```

2. **Try different template**:
   ```bash
   he parse doc.md -t general/model -l en
   ```

3. **Check language**:
   ```bash
   # Wrong language
   he parse chinese_doc.md -t general/graph -l en
   
   # Correct
   he parse chinese_doc.md -t general/graph -l zh
   ```

### Corrupted Knowledge Abstract

**Problem**: Can't load or errors reading

**Solutions**:

1. **Check file structure**:
   ```bash
   ls ./ka/
   # Should have: data.json, metadata.json
   ```

2. **Validate JSON**:
   ```bash
   python -c "import json; json.load(open('./ka/data.json'))"
   ```

3. **Re-extract**:
   ```bash
   rm -rf ./ka/
   he parse doc.md -t general/graph -o ./ka/ -l en
   ```

---

## Provider Structured Output Compatibility

### Bailian returns messages must contain the word json

**Problem**: Bailian returns an error like:

```text
'messages' must contain the word 'json'
```

**Cause**: The provider requires prompts to explicitly mention JSON when JSON response format is used.

**Solution**: Hyper-Extract injects this instruction in the unified structured extraction adapter. YAML templates do not need provider-specific wording. If this error still appears, verify that you are running a version that includes this fix.

### DeepSeek rejects response_format

**Problem**: DeepSeek rejects response-format structured output.

**Solution**: Hyper-Extract first tries tool/function calling. It falls back to JSON prompt + Pydantic validation only when the provider clearly does not support the structured-output strategy.

Authentication failures, network errors, rate limits, and insufficient balance do not trigger fallback and should be treated as provider/API configuration issues.

---

## Still Having Issues?

1. **Check logs** — Look for detailed error messages
2. **Update to latest** — `pip install --upgrade hyperextract`
3. **Check GitHub Issues** — [github.com/yifanfeng97/hyper-extract/issues](https://github.com/yifanfeng97/hyper-extract/issues)
4. **Create new issue** — Include error messages and reproduction steps

---

## Debug Mode

Enable verbose output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from hyperextract import Template
ka = Template.create("general/graph", "en")
```

Or in CLI config:
```toml
[defaults]
verbose = true
```
