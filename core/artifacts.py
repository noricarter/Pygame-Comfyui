
from typing import List, Dict, Any

def split_artifacts(arts: List[Dict[str, Any]]):
    """Separate by kind for UI: returns (images, texts, audios, videos, others)."""
    imgs, txts, auds, vids, others = [], [], [], [], []
    for a in arts:
        kind = a.get("kind")
        if kind == "image": imgs.append(a)
        elif kind == "text": txts.append(a)
        elif kind == "audio": auds.append(a)
        elif kind == "video": vids.append(a)
        else: others.append(a)
    return imgs, txts, auds, vids, others
