from pathlib import Path
import os
from dotenv import load_dotenv
from hyperextract import create_client
from hyperextract.methods.rag import Hyper_RAG

project_root = Path(__file__).parent
load_dotenv(project_root / '.env')
api_key = os.environ.get('BAILIAN_API_KEY') or os.environ.get('OPENAI_API_KEY')
if not api_key:
    raise RuntimeError('Missing API key')
llm_model = os.environ.get('BAILIAN_LLM_MODEL', 'qwen3.6-plus')
embedding_model = os.environ.get('BAILIAN_EMBEDDING_MODEL', 'text-embedding-v4')
base_url = os.environ.get('OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
llm, embedder = create_client(
    llm=f'bailian:{llm_model}@{base_url}',
    embedder=f'bailian:{embedding_model}@{base_url}',
    api_key=api_key,
)
with open(project_root / 'examples' / 'zh' / 'sushi.md', encoding='utf-8') as f:
    text = f.read()
rag = Hyper_RAG(llm_client=llm, embedder=embedder, verbose=False)
chunks = rag.text_splitter.split_text(text)
first_chunk = chunks[0]
print('chunks', len(chunks))
print('first_chunk_len', len(first_chunk))
print('--- NODE EXTRACTION ---')
node_result = rag.node_extractor.invoke({'source_text': first_chunk})
print('node_result type', type(node_result).__name__)
nd = node_result.model_dump() if hasattr(node_result, 'model_dump') else None
print('node_dump keys', list(nd.keys()) if nd else None)
print('node_items_count', len(nd.get('items', [])) if nd else None)
for i, item in enumerate(nd.get('items', []) if nd else [], start=1):
    print('node_item', i, item)
    if i >= 20:
        break
node_items = node_result.items if hasattr(node_result, 'items') else []
print('node_items len', len(node_items))
node_keys = [rag.node_key_extractor(n) for n in node_items]
print('node_keys', node_keys)
known_nodes = 'No entities identified in this chunk.' if not node_keys else '\n- '.join(node_keys)
print('known_nodes preview:', known_nodes[:400])
print('--- EDGE EXTRACTION ---')
edge_result = rag.edge_extractor.invoke({'source_text': first_chunk, 'known_nodes': known_nodes})
print('edge_result type', type(edge_result).__name__)
ed = edge_result.model_dump() if hasattr(edge_result, 'model_dump') else None
print('edge_dump keys', list(ed.keys()) if ed else None)
print('edge_items_count', len(ed.get('items', [])) if ed else None)
for i, item in enumerate(ed.get('items', []) if ed else [], start=1):
    print('edge_item', i, item)
    if i >= 20:
        break
print('--- FULL TWO STAGE ---')
raw = rag._extract_data_by_two_stage(text)
print('raw_nodes', len(raw.nodes), 'raw_edges', len(raw.edges))
print('raw_node_names', [n.name for n in raw.nodes][:20])
print('raw_edge_participants', [e.participants for e in raw.edges][:20])
pruned = rag._prune_dangling_edges(raw)
print('pruned_nodes', len(pruned.nodes), 'pruned_edges', len(pruned.edges))
print('pruned_edge_participants', [e.participants for e in pruned.edges][:20])
