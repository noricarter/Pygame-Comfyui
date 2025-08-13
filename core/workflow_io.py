
import os, json
from typing import List

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def scan_workflows(root_dir: str, exts={".json"}) -> List[str]:
    out = []
    root = os.path.abspath(root_dir)
    for base, _, files in os.walk(root):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in exts:
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, root)
                out.append(rel)
    out.sort(key=str.lower)
    return out

def load_workflow_graph(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
