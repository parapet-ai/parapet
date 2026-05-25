# Airlock v3.0.0-APACHE — NIS2 Compliance Mapping
## v1.0.0 | Priority Date: 2026-05-18 | Evidence for Patent #7

---

## NIS2 Overview

**Directive (EU) 2022/2555** — measures for a high common level of cybersecurity across the Union.

**Who it applies to:**
- **Essential entities:** Energy, transport, banking, financial market infrastructure, health, drinking water, digital infrastructure, ICT service management, public administration, space
- **Important entities:** Postal/courier, waste management, chemicals, food, manufacturing, digital providers, research

**Key obligations:** Article 21 (cybersecurity risk-management measures), Article 23 (incident reporting), Article 20 (management body accountability)

---

## Article-by-Article Mapping

### Article 20 — Management Body Accountability

| Requirement | Airlock Implementation | Evidence |
|-------------|----------------------|----------|
| Management must approve cybersecurity measures | Deployment checklist + audit trail | `security/CAPABILITIES.md` — all 40 capabilities documented |
| Management must follow training | Operator documentation | `PATENT_POLAND/01-FILING-GUIDE-PL-EN.md` |
| Management liable for non-compliance | Zero third-party AI dependency = simplified liability | This document |

**Airlock advantage:** No cloud AI provider to audit. Management approves one system (Airlock), not a chain of subcontractors.

### Article 21(2) — Cybersecurity Risk-Management Measures

| NIS2 Art. 21(2) requirement | Airlock Mechanism | Compliance |
|------------------------------|-------------------|------------|
| **(a) Policies on risk analysis and information system security** | `security/CAPABILITIES.md` — full capability audit + `security/seccomp-airlock.json` — syscall whitelist | Yes |
| **(b) Incident handling** | Graceful container restart via Docker restart policy; session auto-save | Yes |
| **(c) Business continuity** | Offline operation (no cloud dependency); backup via workspace bind mount | Yes |
| **(d) Supply chain security** | **Zero external AI provider** — no AI supply chain to attack. Models are local GGUF files with verified sha256. | **Yes — key advantage** |
| **(e) Security in acquisition, development and maintenance** | All code in MIT/APACHE dual license; reproducible Docker builds; dependency pinning in Dockerfiles | Yes |
| **(f) Policies to assess effectiveness of cybersecurity measures** | Pentest suite (`pentest-airlock.ps1` — 22/22 PASS); automated test suite (`test-mit-automated.ps1` — 57/57 PASS target) | Yes |
| **(g) Cryptography and encryption** | AES-256-GCM session encryption; DPAPI token storage; `security/KEY-LIFECYCLE.md` — full lifecycle | Yes |
| **(h) Human resources security, access control** | Bearer token authentication (timing-safe comparison); RBAC via container user (1000:1000); `tests/test_auth_negative.py` — 14 auth tests | Yes |
| **(i) Multi-factor authentication** | Not applicable (local-only, 127.0.0.1 binding). Optional: Web UI can be placed behind reverse proxy with MFA | Partial |
| **(j) Secure communications** | All container communication via Docker bridge network (localhost); no external connections for AI layer | Yes |

### Article 21(2)(d) — Supply Chain Security — Deep Dive

This is Airlock's strongest NIS2 advantage.

| Supply chain element | Cloud AI (ChatGPT/Claude/Gemini) | Airlock |
|---------------------|----------------------------------|---------|
| **AI model provider** | OpenAI / Anthropic / Google — critical ICT supplier | Ollama + local GGUF files — **no supplier** |
| **Inference provider** | Cloud API endpoint — critical ICT supplier | Local GPU — **no supplier** |
| **Model weights source** | Proprietary, opaque, unverifiable | Open-weight GGUF files with published sha256 hashes |
| **Training data provenance** | Unknown; not disclosed | Documented per model (e.g., Bielik trained on Polish legal corpus) |
| **Vendor lock-in** | High — switching providers requires retesting all prompts | None — 38 models tested, switching is instant |
| **Supplier audit rights** | Limited or non-existent | Full — model files are auditable artifacts |
| **Supplier security posture** | Must be assessed and documented | **No assessment needed** — no external supplier |
| **Concentration risk** | Provider failure = AI unavailable | Hardware failure = AI unavailable (self-contained, no cascade) |

**Regulatory impact:** A NIS2 essential entity using cloud AI must document and risk-assess every AI provider in their ICT supply chain register. With Airlock, the AI supply chain entry is **zero providers**.

### Article 23 — Incident Reporting

| Requirement | Airlock Implementation |
|-------------|----------------------|
| Early warning (24 hours) | Container health status via `/health` endpoint; Docker HEALTHCHECK |
| Incident notification (72 hours) | Logged to `agent.jsonl` structured JSON; audit trail preserved |
| Final report (1 month) | `BENCHMARK-RESULTS.md` provides baseline for root cause analysis |

**Airlock advantage:** Incident scope is self-contained — no third-party provider to coordinate with. Report writing uses the same data already being collected.

### Article 32 — Penalties

| Entity type | Maximum penalty |
|-------------|----------------|
| Essential entities | Up to €10,000,000 or 2% of global annual turnover |
| Important entities | Up to €7,000,000 or 1.4% of global annual turnover |

**Airlock relevance:** Using cloud AI exposes the entity to penalties if the cloud provider's security fails and the entity didn't properly audit them. Local AI eliminates this exposure for the AI layer.

---

## NIS2 Compliance Matrix — Airlock vs Cloud AI

| NIS2 Obligation | Cloud AI Burden | Airlock Burden | Savings |
|-----------------|----------------|----------------|---------|
| Supply chain risk assessment (Art. 21) | 3+ providers to assess | **0 providers** | ~€15,000/year |
| ICT register maintenance | 3+ entries, annual review | **0 entries** | ~€5,000/year |
| Incident notification coordination | Must coordinate with provider timeline | Self-contained | Faster response |
| Management training | Provider-specific training per vendor | One system | ~€2,000/year |
| Audit trail | Provider logs + internal logs = fragmented | Single JSONL log file | Audit ready |
| **Total annual compliance delta** | | | **~€22,000/year saved** |

---

## Cross-Reference: NIS2 + DORA Overlap

Both regulations cover ICT supply chain risk. Airlock's compliance-by-architecture approach satisfies both simultaneously:

| Requirement | NIS2 | DORA | Airlock |
|-------------|------|------|---------|
| ICT third-party risk register | Art. 21(2)(d) | Art. 28 | Zero AI providers — no entries |
| Supply chain security | Art. 21(2)(d) | Art. 28(5) | No AI supply chain |
| Incident reporting | Art. 23 | Art. 11 | Self-contained |
| Testing | Art. 21(2)(f) | Art. 24 | Pentest suite + automated tests |
| Management accountability | Art. 20 | Art. 5 | Single system, simplified |

---

*Document v1.0.0 | 2026-05-21 | Andrzej Dobosz*
*Evidence for Patent #7: Compliance-by-Architecture — NIS2 Directive*
