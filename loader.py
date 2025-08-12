# loader.py
import json

def load_workflow_graph(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def set_param(graph: dict, node_id: str, field: str, value):
    node = graph.get(node_id)
    if not node:
        raise KeyError(f"Node {node_id} not found")
    node.setdefault("inputs", {})[field] = value
