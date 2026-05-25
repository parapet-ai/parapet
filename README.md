# Parapet AI

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Patent Pending](https://img.shields.io/badge/Patent-Pending-blue.svg)](IP-NOTICE.md)
[![Trademark Pending](https://img.shields.io/badge/Trademark-Pending-blue.svg)](IP-NOTICE.md)
[![EU AI Act](https://img.shields.io/badge/EU_AI_Act-Minimal_Risk-success.svg)](docs/EU-AI-ACT-RISK-CLASSIFICATION.md)

**EN:** A hardened local AI stack with five-layer egress security. Runs Ollama models inside Docker containers behind iptables, DNS sinkholes, seccomp profiles, and read-only filesystems. No cloud. No API keys. No telemetry.

**PL:** Zahartowany lokalny stos AI z pieciowarstwowym zabezpieczeniem ruchu wychodzacego. Uruchamia modele Ollama w kontenerach Docker za iptables, DNS sinkhole, seccomp i read-only rootfs. Bez chmury. Bez kluczy API. Bez telemetrii.

## Supported Models / Wspierane modele

Parapet AI works with any Ollama-compatible model. Benchmarked highlights from 38-model evaluation:

| Model | Strength | Throughput |
|-------|----------|------------|
| **Bielik** (SpeakLeash) | Polish language — legal, general | 68 tok/s |
| **DeepSeek Coder 1.3B** | Code generation | 233 tok/s |
| **Phi-4 Mini** | General reasoning | 93 tok/s |
| **Qwen 2.5 3B** | Best all-rounder for 6GB VRAM | 85 tok/s |
| **Llama 3.1 8B** | Document processing, translation | ~30 tok/s |

See `config/models.json` for full model registry.

## Architecture / Architektura

```
┌─────────────────────────────────────────┐
│ Layer 1: VM Isolation (NAT mode)        │
│ Layer 2: iptables (PARAPET-EGRESS)      │
│ Layer 3: DNS Sinkhole (CoreDNS)         │
│ Layer 4: Container Hardening            │
│   ├── read-only rootfs                  │
│   ├── cap_drop ALL                      │
│   ├── no-new-privileges                 │
│   └── seccomp profile                   │
│ Layer 5: Secret Isolation               │
└─────────────────────────────────────────┘
```

## Quick Start / Szybki start

```bash
docker compose build
docker compose up -d
docker logs -f parapet-agent
```

Web UI at `http://localhost:8080`

## Requirements / Wymagania

- Docker + Docker Compose
- [Ollama](https://ollama.com) running on the host
- 6GB+ VRAM recommended

## Regulatory Alignment / Zgodnosc regulacyjna

Parapet AI's architecture supports compliance with key EU regulations:

| Regulation | How Parapet Helps / W jaki sposob pomaga |
|---|---|
| **EU AI Act** | Local-only execution meets data minimization and privacy-by-design requirements. Classified as minimal risk. [Analysis / Analiza →](docs/EU-AI-ACT-RISK-CLASSIFICATION.md) |
| **NIS2** | 5-layer hardening and container isolation support Article 21 risk management. [Mapping / Mapowanie →](docs/NIS2-COMPLIANCE-MAPPING.md) |
| **DORA** | Read-only rootfs, cap dropping, and immutable infrastructure align with Articles 9-16. [Alignment / Zgodnosc →](docs/DORA-COMPLIANCE.md) |

*Architectural alignment, not legal certification. / Zgodnosc architektoniczna, nie certyfikacja prawna.*

## Project Structure / Struktura projektu

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
├── docs/                # Regulatory + architecture docs
├── scripts/             # Launchers + utilities
└── prompts/             # Domain-specific prompts
```

## Legal / Informacje prawne

| | ID | Jurisdiction | Status |
|---|---|---|---|
| Patent | P.455821 | Poland (UPRP) | Pending / W trakcie |
| Trademark / Znak towarowy | Z.603439 | Poland (UPRP) | Pending / W trakcie |

Patent priority date / Data pierwszenstwa: 2026-05-18  
Trademark priority date / Data pierwszenstwa znaku: 2026-05-25  

See [IP-NOTICE.md](IP-NOTICE.md) for full details.

## License / Licencja

MIT — see [LICENSE](LICENSE)

---

**[parapetai.dev](https://parapetai.dev)**
