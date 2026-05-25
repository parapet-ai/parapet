# DORA Alignment / Zgodnosc z DORA

## Overview / Przeglad

The EU Digital Operational Resilience Act (DORA, Regulation 2022/2554) applies to financial entities in the EU. Parapet AI's architecture supports DORA compliance objectives through its 5-layer hardening model.

Rozporzadzenie DORA (2022/2554) dotyczy podmiotow finansowych w UE. Architektura Parapet AI wspiera cele zgodnosci z DORA poprzez 5-warstwowy model zabezpieczen.

## Article Mapping / Mapowanie artykulow

| DORA Article | Requirement / Wymog | Parapet Mechanism / Mechanizm |
|---|---|---|
| Art. 9 | ICT risk management framework | 5-layer security model with documented controls |
| Art. 10 | ICT systems security | Read-only rootfs, cap_drop ALL, no-new-privileges |
| Art. 11 | Detection and response | JSONL audit trail, healthcheck monitoring |
| Art. 12 | Business continuity | Immutable container images, reproducible builds |
| Art. 13 | Testing of ICT systems | Seccomp profiles, pentest-automated pipeline |
| Art. 15 | ICT third-party risk | Local-only execution — no cloud dependencies, no API keys |
| Art. 16 | ICT incident management | Structured logging, container restart policies |

## Key Principle / Kluczowa zasada

**EN:** Parapet AI eliminates third-party ICT risk entirely — the stack runs 100% locally with no external API dependencies. This aligns with DORA's emphasis on managing and minimizing ICT supply chain risk.

**PL:** Parapet AI calkowicie eliminuje ryzyko ICT stron trzecich — stos dziala w 100% lokalnie, bez zaleznosci od zewnetrznych API. Jest to zgodne z naciskiem DORA na zarzadzanie i minimalizacje ryzyka lancucha dostaw ICT.

## Disclaimer / Zastrzezenie

These materials describe architectural alignment. Parapet AI is a tool, not a compliance service. Consult your compliance officer for formal DORA assessment.

Niniejsze materialy opisuja zgodnosc architektoniczna. Parapet AI jest narzedziem, nie usluga zgodnosci. Skonsultuj sie z oficerem ds. zgodnosci w celu formalnej oceny DORA.
