FROM python:3.11-slim
COPY infra/wheels /wheels
COPY infra/sandbox-requirements.txt /requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /requirements.txt && \
    mkdir -p /workspace && chown 65534:65534 /workspace
USER 65534:65534
WORKDIR /workspace
CMD ["sleep", "infinity"]
