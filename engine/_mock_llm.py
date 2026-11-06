"""Tiny OpenAI-compatible mock server for offline tests. Always answers with the seed program in a code fence.
Usage: python engine/_mock_llm.py [port]  (then LLM_BASE_URL=http://127.0.0.1:PORT/v1)"""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SEED = (Path(__file__).parent / "initial_program.py").read_text()
COUNT = [0]


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        COUNT[0] += 1
        prog = SEED.replace("range(k, k + 4)", f"range(k, k + {2 + COUNT[0] % 3})")  # change inside the EVOLVE-BLOCK
        text = "```python\n" + prog + "\n```"
        body = json.dumps({"id": "m", "object": "chat.completion", "created": 0, "model": "mock",
                           "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
                           "usage": {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
