FROM python:3.11-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/engram/.venv PATH=/opt/engram/.venv/bin:$PATH \
    SANDBOX_RUNTIME=docker SANDBOX_IMAGE=engram-sandbox:local \
    EMBEDDING_MODEL_PATH=/opt/engram/data/models/mxbai-embed-large-v1_fp32.gguf \
    EMBEDDING_URL=http://127.0.0.1:8091/v1 EMBEDDING_DIMENSION=1024 \
    ARTIFACT_BACKEND=r2 ARTIFACT_ROOT=/opt/engram/data/collective/artifacts \
    COOKIE_SECURE=true AGENT_PROVIDER=groq AGENT_MODEL=openai/gpt-oss-120b \
    DECISION_PROVIDER=safeguard MAX_PARALLEL_AGENTS=3
RUN apt-get update && apt-get install -y --no-install-recommends \
      docker.io build-essential cmake pkg-config libopenblas-dev ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.11.13
WORKDIR /opt/engram
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --python /usr/local/bin/python
COPY collective/embedding-requirements.txt /tmp/embedding-requirements.txt
RUN CMAKE_ARGS='-DGGML_NATIVE=OFF -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS' \
    uv pip install --python .venv/bin/python --index-strategy unsafe-best-match \
      -r /tmp/embedding-requirements.txt
COPY collective/ ./collective/
COPY runtime/supervisor.py ./runtime-supervisor.py
COPY data/models/mxbai-embed-large-v1_fp32.gguf ./data/models/mxbai-embed-large-v1_fp32.gguf
COPY sandbox-image.tar /opt/engram/sandbox-image.tar
RUN mkdir -p data/collective/artifacts data/collective/tmp && chmod 700 data/collective
EXPOSE 8088
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/engram/.venv/bin/python", "/opt/engram/runtime-supervisor.py"]
