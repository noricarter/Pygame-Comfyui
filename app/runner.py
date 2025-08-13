
import threading, queue, tempfile, os
from typing import List, Dict, Any
from core.comfy_client import ComfyClient

class Runner:
    def __init__(self):
        self.q: "queue.Queue[list[dict]]" = queue.Queue()
        self.client = ComfyClient()

    def run_async(self, graph: dict, poll_interval=0.5, max_wait=600):
        threading.Thread(target=self._worker, args=(graph, poll_interval, max_wait), daemon=True).start()

    def _worker(self, graph: dict, poll_interval, max_wait):
        try:
            job = self.client.run_workflow(graph, poll_interval=poll_interval, max_wait=max_wait)
            self.q.put(job["artifacts"])
        except Exception as e:
            print("Workflow failed:", e)
            self.q.put([])
