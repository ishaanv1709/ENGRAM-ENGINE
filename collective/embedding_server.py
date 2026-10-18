"""Real OpenAI-compatible local embeddings using ENGRAM's existing GGUF model.

Run with the original ENGRAM venv, which already contains llama-cpp-python.
"""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def serve(model_path, port=8091):
    from llama_cpp import Llama

    model = Llama(model_path=model_path, embedding=True, n_ctx=512, n_gpu_layers=0, verbose=False)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def send(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self.send(
                    200, {"status": "ready", "model": "mxbai-embed-large-v1", "engine": "llama.cpp", "device": "cpu"}
                )
            else:
                self.send(404, {"error": "Not found"})

        def do_POST(self):
            if self.path != "/v1/embeddings":
                return self.send(404, {"error": "Not found"})
            size = int(self.headers.get("Content-Length", 0))
            if size > 1_000_000:
                return self.send(413, {"error": "Input too large"})
            try:
                body = json.loads(self.rfile.read(size))
                texts = body["input"]
                if isinstance(texts, str):
                    texts = [texts]
                if (
                    not isinstance(texts, list)
                    or not texts
                    or len(texts) > 64
                    or any(not isinstance(t, str) for t in texts)
                ):
                    raise ValueError("Expected 1–64 text inputs")
                data, tokens = [], 0
                with lock:
                    for i, text in enumerate(texts):
                        count = len(model.tokenize(text.encode()))
                        if count > 500:
                            token_ids = model.tokenize(text.encode())
                            parts = [
                                model.embed(
                                    model.detokenize(token_ids[start : start + 480]).decode("utf-8", errors="replace")
                                )
                                for start in range(0, len(token_ids), 480)
                            ]
                            vector = [sum(values) / len(parts) for values in zip(*parts)]
                        else:
                            vector = model.embed(text)
                        norm = sum(x * x for x in vector) ** 0.5
                        vector = [x / norm for x in vector] if norm else vector
                        data.append({"object": "embedding", "index": i, "embedding": vector})
                        tokens += count
                self.send(
                    200,
                    {
                        "object": "list",
                        "model": "mxbai-embed-large-v1",
                        "data": data,
                        "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
                    },
                )
            except (ValueError, KeyError, TypeError) as exc:
                self.send(422, {"error": str(exc)})
            except Exception:
                self.send(500, {"error": "Local embedding inference failed; inspect embedding server logs"})

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    from .settings import settings

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=str(settings.embedding_model_path))
    parser.add_argument("--port", type=int, default=8091)
    args = parser.parse_args()
    serve(args.model, args.port)
