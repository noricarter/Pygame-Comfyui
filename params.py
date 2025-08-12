# params.py

import secrets

def replace_token(graph: dict, token: str, value: str):
    for node in graph.values():
        inputs = node.get("inputs", {})
        for k, v in inputs.items():
            if isinstance(v, str) and token in v:
                inputs[k] = v.replace(token, value)

def set_overrides(graph: dict, overrides: dict[str, object]):
    for key, value in overrides.items():
        try:
            node_id, field = key.split(".", 1)
        except ValueError:
            raise ValueError(f"Override key must be 'node.field', got: {key}")
        node = graph.get(node_id)
        if not node:
            raise KeyError(f"Node {node_id} not found in graph.")
        node.setdefault("inputs", {})[field] = value

def apply_placeholders(graph: dict, values: dict[str, str]):
    tokens = {f"{{{{{k}}}}}": str(v) for k, v in values.items()}
    for node in graph.values():
        inputs = node.get("inputs", {})
        for k, v in inputs.items():
            if isinstance(v, str):
                for t, repl in tokens.items():
                    if t in v:
                        inputs[k] = v.replace(t, repl)

# --- NEW: numeric seed tools ---

def replace_numeric_token(graph: dict, token: str, value: int) -> int:
    """
    If any input equals the string token (e.g., '%%SEED%%'), replace it with the integer value.
    Returns count of replacements.
    """
    count = 0
    for node in graph.values():
        inputs = node.get("inputs", {})
        for k, v in list(inputs.items()):
            if isinstance(v, str) and v == token:
                inputs[k] = int(value)
                count += 1
    return count

def set_seed_on_all_nodes(graph: dict, seed: int) -> int:
    """
    Force a seed into all inputs named 'seed' or 'noise_seed' (if present).
    Returns count of fields updated.
    """
    count = 0
    for node in graph.values():
        inputs = node.get("inputs", {})
        for key in ("seed", "noise_seed"):
            if key in inputs:
                inputs[key] = int(seed)
                count += 1
    return count

def random_u32() -> int:
    """Cryptographically strong 32-bit seed."""
    return secrets.randbits(32)
