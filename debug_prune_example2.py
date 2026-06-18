from tests.mocks import MockChatModel, MockEmbeddings
from hyperextract.methods.rag.hyper_rag import Hyper_RAG, NodeSchema, EdgeSchema

llm = MockChatModel()
embedder = MockEmbeddings(dim=8)
rag = Hyper_RAG(llm_client=llm, embedder=embedder, verbose=False)

# Create nodes: A and B
nodes = [NodeSchema(name='A', type='person', description='Entity A'),
         NodeSchema(name='B', type='person', description='Entity B')]

# Create edges: one valid (A,B), one dangling (A,C), one empty participants
edges = [
    EdgeSchema(participants=['A','B'], description='A-B relation', keywords=['rel'], strength=5),
    EdgeSchema(participants=['A','C'], description='A-C relation dangling', keywords=['rel'], strength=4),
    EdgeSchema(participants=[], description='no participants', keywords=[], strength=1),
]

raw_graph = rag.graph_schema(nodes=nodes, edges=edges)
print('raw_nodes', [n.name for n in raw_graph.nodes])
print('raw_edges participants', [e.participants for e in raw_graph.edges])
pruned = rag._prune_dangling_edges(raw_graph)
print('pruned_nodes', [n.name for n in pruned.nodes])
print('pruned_edges participants', [e.participants for e in pruned.edges])
