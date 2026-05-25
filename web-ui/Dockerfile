# SECURITY: Pin base image to a SHA256 digest in production.
# Run: docker pull python:3.12-slim && docker image inspect python:3.12-slim --format '{{.RepoDigests}}'
# Then replace the line below with: FROM python:3.12-slim@sha256:<digest>
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates procps curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --create-home --shell /bin/bash agent

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY crypto_vault.py .
COPY ssdlc.py .
COPY index.html .

RUN chown -R agent:agent /app
USER agent:agent
EXPOSE 8080

ENTRYPOINT ["python3", "-u", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
