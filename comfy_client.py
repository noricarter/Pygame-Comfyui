# comfy_client.py
import os
import time
import uuid
import requests
from typing import Any

_EXT_KIND = {
    ".png": ("image", "image/png"),
    ".jpg": ("image", "image/jpeg"),
    ".jpeg": ("image", "image/jpeg"),
    ".webp": ("image", "image/webp"),
    ".gif": ("image", "image/gif"),
    ".wav": ("audio", "audio/wav"),
    ".ogg": ("audio", "audio/ogg"),
    ".mp3": ("audio", "audio/mpeg"),
    ".flac": ("audio", "audio/flac"),
    ".mp4": ("video", "video/mp4"),
    ".mov": ("video", "video/quicktime"),
    ".webm": ("video", "video/webm"),
    ".json": ("text", "application/json"),
    ".txt": ("text", "text/plain"),
    ".csv": ("text", "text/csv"),
}

def _guess_kind_mime(filename: str):
    name = filename.lower()
    for ext, pair in _EXT_KIND.items():
        if name.endswith(ext):
            return pair
    return ("binary", "application/octet-stream")

class ComfyClient:
    def __init__(self, base_url: str | None = None, auth: tuple[str, str] | None = None, timeout=60):
        self.base_url = (base_url or os.getenv("COMFY_BASE_URL") or "http://127.0.0.1:8188").rstrip("/")
        self.session = requests.Session()
        if auth:
            self.session.auth = auth
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def run_workflow(self, workflow_graph: dict, poll_interval=0.5, max_wait: float | None = None) -> dict[str, Any]:
        client_id = str(uuid.uuid4())
        r = self.session.post(
            self._url("/prompt"),
            json={"prompt": workflow_graph, "client_id": client_id},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"No prompt_id in response: {data}")

        start = time.time()
        while True:
            h = self.session.get(self._url(f"/history/{prompt_id}"), timeout=self.timeout)
            if h.status_code == 200:
                entry = h.json().get(prompt_id)
                if entry and "outputs" in entry:
                    outputs = entry["outputs"]
                    artifacts = self._collect_artifacts(outputs)
                    return {"prompt_id": prompt_id, "outputs": outputs, "artifacts": artifacts}

            if max_wait is not None and (time.time() - start) > max_wait:
                raise TimeoutError(f"ComfyUI job {prompt_id} timed out.")
            time.sleep(poll_interval)

    def _download_file(self, filename: str, subfolder: str, ftype: str) -> bytes:
        resp = self.session.get(
            self._url("/view"),
            params={"filename": filename, "subfolder": subfolder or "", "type": ftype or "output"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.content

    def _collect_artifacts(self, outputs: dict) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for node_id, node_out in outputs.items():
            if not isinstance(node_out, dict):
                continue
            for key, value in node_out.items():
                if isinstance(value, list) and value and isinstance(value[0], dict) and "filename" in value[0]:
                    for item in value:
                        filename = item.get("filename")
                        subfolder = item.get("subfolder", "")
                        ftype = item.get("type", "output")
                        if not filename:
                            continue
                        raw = self._download_file(filename, subfolder, ftype)
                        kind, mime = _guess_kind_mime(filename)
                        artifacts.append({
                            "node_id": node_id,
                            "key": key,
                            "filename": filename,
                            "subfolder": subfolder,
                            "type": ftype,
                            "kind": kind,
                            "mimetype": mime,
                            "bytes": raw,
                        })
        return artifacts
