
import secrets

def random_u32() -> int:
    return secrets.randbits(32)

def set_seed_on_all_nodes(graph: dict, seed: int) -> int:
    count = 0
    for node in graph.values():
        inputs = node.get("inputs", {})
        for key in ("seed", "noise_seed"):
            if key in inputs:
                inputs[key] = int(seed)
                count += 1
    return count

def apply_seed_policy(graph: dict, tokens_in_graph: set[str], provided_seed: str | int | None) -> int | None:
    """
    If graph has a SEED token and user didn't provide it, generate one and set exact-match tokens.
    If graph has no SEED token, broadcast to all seed/noise_seed fields.
    Returns the chosen seed (or None).
    """
    seed = None
    # User provided?
    if isinstance(provided_seed, (int, float)) or (isinstance(provided_seed, str) and provided_seed.strip() != ""):
        try:
            seed = int(float(provided_seed))  # accept "123", "123.0"
        except:
            seed = random_u32()
    else:
        seed = random_u32()

    if "SEED" in tokens_in_graph:
        # Exact-match replacement will be handled by tokens.apply_token_values
        return seed
    else:
        set_seed_on_all_nodes(graph, seed)
        return seed
