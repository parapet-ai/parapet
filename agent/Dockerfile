# SECURITY: Pin base image to a SHA256 digest in production.
# Run: docker pull python:3.12-slim && docker image inspect python:3.12-slim --format '{{.RepoDigests}}'
# Then replace the line below with: FROM python:3.12-slim@sha256:<digest>
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates procps \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --create-home --shell /bin/bash agent

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ollama_agent.py .
COPY ssdlc.py .

RUN mkdir -p /var/log/agent /workspace /tmp && \
    chown -R agent:agent /app /var/log/agent /workspace /tmp

USER agent:agent
ENTRYPOINT ["python3", "-u", "/app/ollama_agent.py"]
