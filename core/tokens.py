
import re
from typing import List, Dict, Any, Optional

# %%NAME%%, %%NAME:ml%%, %%NAME:int%%, %%NAME:float%%, %%NAME:choice[a,b]%% (choice reserved for future)
TOKEN_RE = re.compile(r"%%([A-Za-z0-9_]+)(?::([A-Za-z0-9_]+)(?:\[[^%]*\])?)?%%")

def find_specs(graph: dict) -> List[Dict[str, Any]]:
    """Return ordered unique token specs: [{name, raw, kind}]"""
    seen = {}
    for node in graph.values():
        inputs = node.get("inputs", {})
        for v in inputs.values():
            if isinstance(v, str):
                for m in TOKEN_RE.finditer(v):
                    name = m.group(1)
                    kind = (m.group(2) or "str").lower()
                    if name not in seen:
                        seen[name] = {"name": name, "raw": m.group(0), "kind": kind}
    return [seen[k] for k in sorted(seen.keys())]

def _coerce(value: str, kind: str):
    s = value.strip()
    if kind == "int":
        try: return int(s)
        except: return s
    if kind == "float":
        try: return float(s)
        except: return s
    # default 'str' and 'ml' -> string
    return value

def apply_token_values(graph: dict, values: Dict[str, Any]) -> None:
    """
    Replace tokens in string inputs across the graph.
    Exact-match tokens get type coercion based on kind (if discovered).
    Embedded tokens always replaced as string.
    """
    # Build a map name->(raw token, kind). If multiple forms exist, prefer the first found.
    specs = { spec["name"]: spec for spec in find_specs(graph) }

    for node in graph.values():
        inputs = node.get("inputs", {})
        for k, v in list(inputs.items()):
            if not isinstance(v, str):
                continue

            # Exact match? e.g. input equals "%%SEED:int%%"
            m = TOKEN_RE.fullmatch(v)
            if m:
                name, kind = m.group(1), (m.group(2) or "str").lower()
                if name in values:
                    val = values[name]
                    # if user typed string, try coercion
                    if isinstance(val, str):
                        inputs[k] = _coerce(val, kind)
                    else:
                        inputs[k] = val
                continue

            # Otherwise, replace any tokens inside a larger string (always as str)
            def _repl(mx):
                n = mx.group(1)
                if n in values:
                    return str(values[n])
                return mx.group(0)  # leave unknowns untouched
            inputs[k] = TOKEN_RE.sub(_repl, v)
