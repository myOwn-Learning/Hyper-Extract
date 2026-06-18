#!/usr/bin/env python3
"""
Real LLM diagnostic for Hyper-RAG two-stage extraction.
Captures raw node/edge extraction results for first chunk of sushi.md.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    import os
    
    # Load environment
    load_dotenv(project_root / '.env')
    api_key = os.environ.get('BAILIAN_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('Missing API key: BAILIAN_API_KEY or OPENAI_API_KEY')
    
    from hyperextract import create_client
    from hyperextract.methods.rag import Hyper_RAG
    
    # Setup output file
    output_file = project_root / 'debug_real_extraction_output.txt'
    log_lines = []
    
    def log_msg(msg):
        """Log message to both stdout and file."""
        print(msg)
        log_lines.append(msg)
    
    log_msg(f"=== Hyper-RAG Real LLM Diagnostic ===")
    log_msg(f"Start time: {datetime.now().isoformat()}")
    log_msg(f"Output file: {output_file}")
    log_msg("")
    
    # Create LLM clients with real API
    llm_model = os.environ.get('BAILIAN_LLM_MODEL', 'qwen3.6-plus')
    embedding_model = os.environ.get('BAILIAN_EMBEDDING_MODEL', 'text-embedding-v4')
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    
    log_msg(f"LLM Model: {llm_model}")
    log_msg(f"Embedding Model: {embedding_model}")
    log_msg(f"Base URL: {base_url}")
    log_msg("")
    
    log_msg("Creating LLM and embedding clients...")
    llm, embedder = create_client(
        llm=f'bailian:{llm_model}@{base_url}',
        embedder=f'bailian:{embedding_model}@{base_url}',
        api_key=api_key,
    )
    log_msg("✓ Clients created")
    log_msg("")
    
    # Load example text
    sushi_file = project_root / 'examples' / 'zh' / 'sushi.md'
    log_msg(f"Loading: {sushi_file}")
    with open(sushi_file, encoding='utf-8') as f:
        text = f.read()
    log_msg(f"✓ Text loaded ({len(text)} chars)")
    log_msg("")
    
    # Initialize Hyper_RAG
    log_msg("Initializing Hyper_RAG...")
    rag = Hyper_RAG(
        llm_client=llm,
        embedder=embedder,
        chunk_size=2048,
        chunk_overlap=256,
        verbose=False,
    )
    log_msg("✓ Hyper_RAG initialized")
    log_msg("")
    
    # Get first chunk manually (simple split for testing)
    chunk_size = 2048
    first_chunk = text[:chunk_size]
    log_msg(f"First chunk size: {len(first_chunk)} chars")
    log_msg(f"First chunk preview: {first_chunk[:200]}...")
    log_msg("")
    
    # Test node extraction
    log_msg("=== NODE EXTRACTION ===")
    try:
        node_result = rag.node_extractor.invoke({'source_text': first_chunk})
        log_msg(f"✓ Node extraction succeeded")
        log_msg(f"  Type: {type(node_result).__name__}")
        log_msg(f"  Items count: {len(node_result.items) if hasattr(node_result, 'items') else 'N/A'}")
        if hasattr(node_result, 'items'):
            for i, node in enumerate(node_result.items[:5]):
                log_msg(f"    [{i}] {node.name} ({node.type})")
            if len(node_result.items) > 5:
                log_msg(f"    ... and {len(node_result.items) - 5} more")
        log_msg("")
        
        # Save raw nodes for inspection
        node_json = {
            'type': type(node_result).__name__,
            'count': len(node_result.items) if hasattr(node_result, 'items') else 0,
            'items': [
                {'name': n.name, 'type': n.type, 'description': n.description[:100] + '...' if len(n.description) > 100 else n.description}
                for n in (node_result.items if hasattr(node_result, 'items') else [])
            ][:10]
        }
        log_msg(f"Raw node output (first 10):")
        log_msg(json.dumps(node_json, indent=2, ensure_ascii=False))
        log_msg("")
        
    except Exception as e:
        log_msg(f"✗ Node extraction failed: {type(e).__name__}")
        log_msg(f"  Error: {str(e)[:500]}")
        log_msg("")
    
    # Test edge extraction
    log_msg("=== EDGE EXTRACTION ===")
    try:
        # Build known_nodes for edge extraction
        if hasattr(node_result, 'items'):
            node_names = [n.name for n in node_result.items]
            known_nodes_text = "\n- ".join(node_names)
        else:
            known_nodes_text = ""
        
        edge_result = rag.edge_extractor.invoke({
            'source_text': first_chunk,
            'known_nodes': known_nodes_text,
        })
        log_msg(f"✓ Edge extraction succeeded")
        log_msg(f"  Type: {type(edge_result).__name__}")
        log_msg(f"  Items count: {len(edge_result.items) if hasattr(edge_result, 'items') else 'N/A'}")
        if hasattr(edge_result, 'items'):
            for i, edge in enumerate(edge_result.items[:5]):
                log_msg(f"    [{i}] {edge.participants}")
            if len(edge_result.items) > 5:
                log_msg(f"    ... and {len(edge_result.items) - 5} more")
        log_msg("")
        
        # Save raw edges for inspection
        edge_json = {
            'type': type(edge_result).__name__,
            'count': len(edge_result.items) if hasattr(edge_result, 'items') else 0,
            'items': [
                {'participants': e.participants, 'description': e.description[:100] + '...' if len(e.description) > 100 else e.description}
                for e in (edge_result.items if hasattr(edge_result, 'items') else [])
            ][:10]
        }
        log_msg(f"Raw edge output (first 10):")
        log_msg(json.dumps(edge_json, indent=2, ensure_ascii=False))
        log_msg("")
        
    except Exception as e:
        log_msg(f"✗ Edge extraction failed: {type(e).__name__}")
        log_msg(f"  Error: {str(e)[:500]}")
        log_msg("")
    
    # Test full two-stage extraction
    log_msg("=== FULL TWO-STAGE EXTRACTION ===")
    try:
        result = rag._extract_data_by_two_stage(first_chunk)
        log_msg(f"✓ Two-stage extraction succeeded")
        log_msg(f"  Raw nodes: {len(result.nodes) if hasattr(result, 'nodes') else 'N/A'}")
        log_msg(f"  Raw edges: {len(result.edges) if hasattr(result, 'edges') else 'N/A'}")
        
        if hasattr(result, 'nodes'):
            log_msg(f"  Node keys: {[n.name for n in result.nodes[:5]]}")
        if hasattr(result, 'edges'):
            log_msg(f"  Edge participants (first 3): {[e.participants for e in result.edges[:3]]}")
        log_msg("")
        
    except Exception as e:
        log_msg(f"✗ Two-stage extraction failed: {type(e).__name__}")
        log_msg(f"  Error: {str(e)[:500]}")
        log_msg("")
    
    log_msg(f"End time: {datetime.now().isoformat()}")
    log_msg("=== END ===")
    
    # Write all logs to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    
    print(f"\n✓ Output saved to: {output_file}")
    
except Exception as e:
    print(f"Fatal error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
