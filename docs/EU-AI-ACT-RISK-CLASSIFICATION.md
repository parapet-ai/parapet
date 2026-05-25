# Airlock v3.0.0 — EU AI Act Risk Classification Guide
## v1.0.0 | Priority Date: 2026-05-22 | For Airlock Deployers

---

**Purpose:** This guide helps Airlock deployers determine their obligations under the **EU AI Act** (Regulation (EU) 2024/1689), applicable from **2 August 2026**. It is a practical decision tree, not legal advice. For binding determinations, consult your DPO or legal counsel.

---

## Decision Tree

### Step 1 — What Is the AI Being Used For?

Answer the question below by finding the use case that best matches your deployment. Follow the arrow to your risk classification.

```
YOUR USE CASE                                          → RISK CLASSIFICATION
====================================================    ==================================

Employee performance evaluation, workplace monitoring   → HIGH RISK (Annex III, point 4)
  "The AI analyses employee emails for productivity"
  "The AI scores call centre interactions"

Creditworthiness assessment, credit scoring             → HIGH RISK (Annex III, point 5b)
  "The AI evaluates loan applications"
  "The AI assesses customer credit risk"

Critical infrastructure management                      → HIGH RISK (Annex III, point 2)
  "The AI monitors energy grid load"
  "The AI controls water treatment parameters"

Law enforcement, migration, justice                     → PROHIBITED or HIGH RISK
  "The AI profiles suspects"                            (Art. 5 prohibition likely applies)
  "The AI assists in visa eligibility decisions"        (Annex III, point 6)

Biometric categorisation, emotion recognition           → HIGH RISK or PROHIBITED
  "The AI analyses facial expressions of employees"     (Art. 5 prohibition for workplace)
  "The AI identifies individuals in CCTV footage"       (Annex III, point 1)

Internal document search, code assistance               → MINIMAL RISK
  "The AI searches internal policies for relevant text"
  "The AI helps write Python functions"

Translation, summarisation                              → MINIMAL RISK
  "The AI translates contracts from Polish to English"
  "The AI summarises meeting notes"

Customer-facing chatbot                                 → LIMITED RISK
  "The AI answers product questions on our website"     (Art. 50 transparency obligation)

Internal data extraction, form processing               → MINIMAL to LIMITED RISK
  "The AI extracts dates from invoices"                 (depends on downstream use)
```

### Key Principle: Data Sovereignty Reduces Risk

Because Airlock runs **entirely on local hardware** with **zero data transmission**, many obligations that apply to cloud AI services are either simplified or not applicable:

- **No cross-border data transfer** — data never leaves the device → no transfer impact assessment needed
- **No third-party processor** — no DPA with an AI provider → simplified DPIA
- **Full logging control** — you control what is logged and for how long
- **Human oversight inherent** — local deployment means a human is always in the loop

---

### Step 2 — If HIGH RISK, What Additional Obligations Apply?

If your use case falls into HIGH RISK (Annex III), the following obligations apply. Airlock's compliance posture for each is noted.

| Article | Obligation | Airlock Compliance Posture |
|---------|-----------|---------------------------|
| **Art. 9** | Risk management system | Deployer must document risks. Airlock's local architecture eliminates cloud-related risks (data breach, vendor lock-in, third-party access). The seccomp profile, capability dropping, and read-only filesystem provide documented mitigations (see security/). |
| **Art. 10** | Data governance | Airlock uses pre-trained models. If you fine-tune models, you must govern that training data. Airlock's local architecture means training data stays on your device. Document your data sources. |
| **Art. 11** | Technical documentation | This document + docs/SCALING-LIMITATIONS.md + docs/OLLAMA-SUPPLY-CHAIN.md + benchmarks/METHODOLOGY.md form the technical documentation package. |
| **Art. 12** | Record-keeping (logs) | Airlock logs all agent activity to JSONL (`workspace/logs/agent.jsonl`). Logs are stored locally. Configure retention per your policy. |
| **Art. 13** | Transparency and information | Deployers must inform users they are interacting with an AI system. Airlock's web UI displays the model name prominently. |
| **Art. 14** | Human oversight | Local deployment = human always in loop. Confirmation required for dangerous tools (shell execution, file writes). Auto-approve mode disables this — document why if used. |
| **Art. 15** | Accuracy, robustness, cybersecurity | Airlock's benchmark suite measures model accuracy (benchmarks/quality_eval.py). The security architecture (seccomp, capabilities, read-only FS) addresses cybersecurity. See security/ directory. |
| **Art. 6 + Annex III** | Conformity assessment | Self-assessment for most high-risk categories. Airlock's documentation package supports this. |
| **Art. 49** | EU database registration | High-risk AI systems must be registered in the EU database. This is the deployer's obligation, not Airlock's. |
| **Art. 50** | Transparency (all risk levels) | Users must be informed they are interacting with AI. The Airlock web UI displays model info. For customer-facing chatbots, add a visible "AI-powered" notice. |

---

### Step 3 — Airlock's Compliance Advantages

Airlock's architecture provides **inherent compliance advantages** that cloud AI services cannot match without significant additional engineering:

#### 1. Data Never Leaves the Device

| Requirement | Cloud AI | Airlock |
|------------|----------|---------|
| DPIA (Data Protection Impact Assessment) | Full DPIA required — cross-border transfer, third-party processor, security of transmission | Simplified DPIA — no transfer, no processor, no transmission |
| DPA with AI provider | Required (Art. 28 GDPR) | NOT required — no provider |
| Cross-border transfer mechanism | Required (SCCs, adequacy decision) | NOT required — data stays local |
| Data breach notification to provider | Required within 72h (Art. 33 GDPR) | NOT applicable — no provider to notify |

#### 2. Full Logging Control

| Requirement | Cloud AI | Airlock |
|------------|----------|---------|
| Access logs | Provider controls — may be limited or cost extra | Full control — JSONL logs on your storage |
| Retention | Provider's policy (may be short, may be immutable) | Your policy — configure retention as needed |
| Audit trail integrity | Trust provider's logging | Local logs — you control integrity |

#### 3. Human Oversight Built In

| Requirement | Cloud AI | Airlock |
|------------|----------|---------|
| Human review of outputs | Must implement manually (API → display → human review) | Local deployment = human sees every output |
| Dangerous operation approval | Must implement API-level gating | Built-in confirmation for shell execution and file writes |

---

### Remaining Deployer Obligations (You Must Do These)

Even with Airlock, the deployer (you) must:

1. **Document your risk management system** (Art. 9) — template provided in this document's structure
2. **Establish human oversight procedures** (Art. 14) — define who reviews AI outputs, how often, and what triggers escalation
3. **Set up incident reporting** (Art. 62) — how will you detect and report AI incidents? Document the procedure
4. **Register high-risk systems** in the EU database (Art. 49) — if your use case is high-risk
5. **Conduct fundamental rights impact assessment** (Art. 27) — if your use case involves processing personal data in a high-risk context
6. **Maintain technical documentation** (Art. 11) — keep it current, review annually

---

## Quick Reference: Risk Classification by Sector

| Sector | Common Use Case | Typical Classification |
|--------|----------------|----------------------|
| Financial services | Internal policy search, contract summarisation | MINIMAL |
| Financial services | Credit scoring, loan decisions | HIGH RISK (Annex III, 5b) |
| Legal | Document review, case law search | MINIMAL |
| Legal | Client advice generation without human review | LIMITED (transparency) |
| Healthcare | Medical record summarisation (assistive) | HIGH RISK (safety component) |
| Healthcare | Appointment scheduling chatbot | LIMITED |
| HR | CV screening, candidate ranking | HIGH RISK (Annex III, 4) |
| HR | Employee handbook Q&A chatbot | MINIMAL |
| IT/Security | Code review assistance | MINIMAL |
| IT/Security | Automated vulnerability triage without human review | LIMITED (document) |
| Government | Internal document processing | MINIMAL to LIMITED |
| Government | Citizen-facing benefit eligibility decisions | HIGH RISK (Annex III, 5a) |

---

*Document v1.0.0 | 2026-05-22 | Andrzej Dobosz*
*This is guidance, not legal advice. Consult your DPO or legal counsel for binding determinations.*
