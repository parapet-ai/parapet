# Parapet AI

A hardened local AI stack with five-layer egress security. Runs Ollama models inside Docker containers behind iptables, DNS sinkholes, seccomp profiles, and read-only filesystems.

**No cloud. No API keys. No telemetry.**

## Architecture

```
┌─────────────────────────────────────────┐
│ Layer 1: VM Isolation (NAT mode)        │
│ Layer 2: iptables (AIRLOCK-EGRESS)      │
│ Layer 3: DNS Sinkhole (CoreDNS)         │
│ Layer 4: Container Hardening            │
│   ├── read-only rootfs                  │
│   ├── cap_drop ALL                      │
│   ├── no-new-privileges                 │
│   └── seccomp profile                   │
│ Layer 5: Secret Isolation               │
└─────────────────────────────────────────┘
```

## Quick Start

```bash
# Build containers
docker compose build

# Start the stack
docker compose up -d

# View logs
docker logs -f parapet-agent

# Stop
docker compose down
```

Web UI at `http://localhost:8080`

## Requirements

- Docker + Docker Compose
- [Ollama](https://ollama.com) running on the host
- 6GB+ VRAM recommended

## Project Structure

```
├── agent/               # AI agent container
│   ├── parapet_agent.py # Main daemon
│   ├── ssdlc.py         # Security lifecycle
│   ├── crypto_vault.py  # Encryption
│   └── Dockerfile
├── web-ui/              # FastAPI web interface
│   ├── server.py
│   ├── index.html
│   └── Dockerfile
├── security/            # Hardening configs
├── tests/               # Test suite
├── config/              # Models + runtime config
├── scripts/             # Launchers + utilities
└── prompts/             # Domain-specific prompts
```

## License

MIT — see [LICENSE](LICENSE)

---

**parapetai.dev**
