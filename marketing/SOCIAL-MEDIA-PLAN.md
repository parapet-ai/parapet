# Parapet AI — Social Media Execution Plan

## Platform Priority Matrix

| # | Platform | Priority | Why | Effort | Impact |
|---|----------|----------|-----|--------|--------|
| 1 | **Reddit** | HIGH | Core audience lives here (r/LocalLLaMA, r/privacy, r/selfhosted) | Medium | Very High |
| 2 | **Hacker News** | HIGH | "Show HN" — single best launch post for open-source dev tools | Low | Very High |
| 3 | **GitHub** | HIGH | Home of the project — stars, README, topics drive organic discovery | Ongoing | Very High |
| 4 | **Product Hunt** | HIGH | One-shot launch day event, drives 1-3k visitors if featured | Low (one day) | High |
| 5 | **X/Twitter** | MEDIUM | Infosec + AI communities, thread format works well for deep dives | Medium | Medium-High |
| 6 | **LinkedIn** | MEDIUM | Regulatory/pentest audience, compliance officers, CISOs | Low | Medium |
| 7 | **YouTube** | LOW | Long-lead content, high production cost, high trust payoff | High | High |
| 8 | **TikTok** | LOW | Gen Z privacy audience, fast growth but mismatched demo for enterprise | High | Low-Medium |

---

## Launch Week — Day-by-Day Content Calendar

Goal: 7 days of coordinated posts across platforms to establish presence, drive GitHub stars, and seed community.

### Day 0 (Pre-Launch — Sunday)

**Task:** Prepare all assets before going live.
- [ ] GitHub repo public: README polished, badges added, docs/ complete
- [ ] `parapetai.dev` HTTPS enforced, landing page live
- [ ] All 5 Reddit posts drafted (not posted yet)
- [ ] HN "Show HN" post drafted
- [ ] Product Hunt listing prepared (logo, tagline, description, screenshot, maker comment)
- [ ] Twitter thread drafted (12-tweet deep dive)
- [ ] LinkedIn article drafted

### Day 1 (Monday — Reddit Launch)

**Primary:** Reddit r/LocalLLaMA
**Secondary:** Reddit r/selfhosted

**r/LocalLLaMA post** (post ~14:00 UTC — peak EU+US overlap):

> **Title:** "Parapet — 5-layer hardened local AI agent that runs 33 models offline. MIT license, EU-built, pentest tools included."
>
> I built something I wanted to share with this community.
>
> Parapet is a Docker-based local AI stack that wraps Ollama in a 5-layer security model:
> - iptables egress filtering (only approved IPs, or full offline mode)
> - DNS sinkhole via CoreDNS
> - read-only rootfs, cap_drop ALL, no-new-privileges
> - seccomp syscall filter
> - API keys mounted as /run/secrets, never in env
>
> **Why I built it:**
> I wanted ChatGPT-level assistance without sending my data to a server I don't control. Also — I work in pentesting and couldn't use cloud AI on client engagements (NDAs, air-gapped networks, data sovereignty requirements).
>
> **What it does:**
> - Web UI + desktop GUI + Docker agent daemon
> - 33 models benchmarked (7 tasks each — code, translation, pentest, legal, general, stress, OCR)
> - Native EU models: Bielik (Polish), LeoLM (German), GEITje (Dutch), Teuken (24 EU languages), Salamandra (Catalan/Spanish), Occiglot (5 languages)
> - Pentest tools: recon, exploit scripting, CVE research, privesc advisor, payload crafting
> - SSDLC framework built in (6 phases, STRIDE threat modeling)
> - Runs on 6GB VRAM (RTX 3060), €17.50/year in electricity
>
> **Stack:** Python + FastAPI + Ollama + Docker
> **License:** MIT
> **Repo:** https://github.com/parapet-ai/parapet
> **Site:** https://parapetai.dev
>
> Happy to answer questions. Would love feedback from this community.

**r/selfhosted post** (post ~18:00 UTC):

> **Title:** "Parapet — self-hosted AI agent with 5-layer hardening. No cloud, no telemetry, no API keys needed."
>
> [Shorter version focusing on self-hosting angle, privacy comparison table, docker-compose one-liner]

### Day 2 (Tuesday — Hacker News + r/privacy)

**Primary:** Hacker News "Show HN"
**Secondary:** Reddit r/privacy

**Show HN post** (post ~14:00 UTC — peak HN traffic):

> **Title:** "Show HN: Parapet — Local AI agent with 5-layer container hardening (MIT)"
>
> [Same core content as Reddit, but HN-optimized: shorter, more technical, no emoji, focus on architecture decisions]
>
> Technical highlights to include:
> - Why iptables + DNS sinkhole vs. just --net=none
> - Seccomp profile design decisions
> - Why not just use Open WebUI + Ollama directly
> - The HuggingFace → Ollama import pipeline (technical moat)
>
> Link to repo. No landing page fluff — direct to README.

**r/privacy post** (post ~18:00 UTC):

> **Title:** "I built an AI that physically cannot spy on you — 5-layer hardening, no internet required"
>
> [Privacy-focused angle, data collection comparison table, GDPR/attorney-client privilege angles]

### Day 3 (Wednesday — Product Hunt)

**Primary:** Product Hunt launch
**Secondary:** r/netsec

**Product Hunt listing:**
- **Tagline:** "Local-first AI agent with 5-layer hardening. No cloud, no telemetry, no API keys."
- **Description:** Short paragraph on what it does, who it's for
- **Maker comment:** Personal story — why you built it, what problem it solves
- **Screenshots:** Web UI chat, desktop GUI, terminal benchmark output, model registry
- **Topics:** AI, Developer Tools, Privacy, Open Source, Security

**r/netsec post** (if mod-allowed — check rules first):

> Focus: pentest angle. "Local AI for pentesters that doesn't leak target data to cloud providers."

### Day 4 (Thursday — X/Twitter Thread)

**Primary:** X/Twitter deep-dive thread
**Secondary:** Reddit r/degoogle

**Twitter thread** (12 tweets, post ~15:00 UTC):

> Tweet 1/12:
> "I built a local AI agent that runs 33 models offline with 5-layer container hardening.
>
> It costs €17.50/year in electricity. Never phones home. Works on 6GB VRAM.
>
> Here's how I built it, and why cloud AI is a privacy disaster: 🧵"
>
> Tweet 2: The problem — what cloud AI actually collects about you
> Tweet 3: Privacy comparison table (ChatGPT vs Claude vs Gemini vs Parapet)
> Tweet 4: The architecture diagram — 5 security layers explained
> Tweet 5: Layer 1 — iptables egress (only approved IPs)
> Tweet 6: Layer 2 — DNS sinkhole (CoreDNS, only api.deepseek.com resolves)
> Tweet 7: Layer 3 — Container hardening (read-only rootfs, cap_drop ALL)
> Tweet 8: Layer 4 — Seccomp (curated syscall whitelist)
> Tweet 9: Layer 5 — Secret isolation (/run/secrets, never in env)
> Tweet 10: Benchmark results — 33 models, 7 tasks, real numbers
> Tweet 11: EU angle — Bielik, native language models, translation tax explained
> Tweet 12: "Try it: parapetai.dev | GitHub: github.com/parapet-ai/parapet | MIT license | Stars appreciated"

### Day 5 (Friday — LinkedIn + CM)

**Primary:** LinkedIn article
**Secondary:** Cross-post best Reddit comment replies

**LinkedIn article** (long-form, regulatory angle):

> **Title:** "Your ChatGPT API Key Is a DORA Article 28 Liability — Here's the Fix"
>
> [Regulatory/compliance angle — CISOs and DPOs are the target]
>
> - EU AI Act Article 17: provider audit obligations you can't fulfill with cloud AI
> - DORA Article 28: your cloud AI provider IS a critical ICT third-party
> - NIS2 Article 21: board liability for supply chain failures
> - The fix: local inference as architectural compliance
> - Estimated savings: €26,000-69,000/year for a mid-size regulated entity

### Day 6 (Saturday — Community Engagement)

- Reply to every Reddit comment and HN comment
- Star and respond to GitHub issues
- Cross-post top-performing content to secondary subreddits
- DM relevant Discord servers (LocalLLaMA, Ollama, self-hosted communities)

### Day 7 (Sunday — Retro + Next Week)

- Review metrics: GitHub stars, Reddit upvotes, HN points, Product Hunt rank, site traffic
- Identify top-performing message/angle
- Plan Week 2 content based on what resonated
- Queue next round of posts

---

## Post Templates — Reusable Per Pillar

### Pillar 1: Regulatory Shield (LinkedIn, r/compliance, EU tech press)

```
HEADLINE: "Your cloud AI provider is a compliance liability. Here's how to remove it."

BODY:
The EU AI Act, DORA, and NIS2 create specific obligations for any organization
using AI. Most companies don't realize that their ChatGPT/Claude/Gemini usage
creates compliance gaps that can't be fixed with policy — only with architecture:

• AI Act Art. 17: You must verify your AI provider's QMS. OpenAI won't let you audit theirs.
• DORA Art. 28: Your AI API key belongs on your critical ICT third-party register.
• NIS2 Art. 21: Board liability extends to AI supply chain failures.

Parapet eliminates the provider entirely. You run the model locally. You ARE the provider.

No provider = no Article 28 registration. No API = no supply chain risk. No cloud = no data transfer.

[Link to DORA compliance doc]
[Link to repo]
```

### Pillar 2: Cost Annihilation (HN, r/LocalLLaMA, r/programming)

```
HEADLINE: "€17.50/year. That's your AI bill. Not €17,500."

BODY:
4 hours/day of AI use on Claude Opus 4: ~€2,400/year
Same workload on Parapet (RTX 3060, local): ~€17.50/year (electricity only)

The math:
• RTX 3060 draws ~150W under load → 0.15 kWh
• EU average electricity: €0.28/kWh
• 4h × 365 days × 0.15 kW × €0.28 = €6.13/year... let's round up to €17.50 for the whole rig

Break-even on hardware: ~200 hours of use pays for the GPU vs cloud.
No per-token pricing. No rate limits at 2 AM. No "you've exceeded your quota."

[Cost comparison table]
[Link to benchmark data]
```

### Pillar 3: Pentest Autopilot (r/netsec, r/cybersecurity, Twitter/X)

```
HEADLINE: "AI-assisted pentesting that doesn't leak your target list to a cloud provider."

BODY:
If you're using cloud AI on a pentest engagement:
- Your target list is logged on someone else's server
- Your exploit paths are potentially reviewable by employees
- You're violating client confidentiality (check your NDA)

Parapet runs entirely offline. Same models, same capabilities, zero external logging.

Domain-tested on pentest tasks:
• openchat:7b — 88% pentest accuracy
• dolphin-mistral:7b — 100% coding, 100% file analysis
• qwen2.5:7b — 88% pentest, 100% file analysis

Built-in tools: recon, exploit scripting, CVE research, privesc advisor, payload crafting.

No cloud. No logs. No liability.
```

### Pillar 4: Privacy (r/privacy, r/degoogle, TikTok, Instagram)

```
HEADLINE: "ChatGPT knows more about you than your therapist. Parapet knows nothing."

BODY:
Cloud AI collects: your prompts, IP, device fingerprint, conversation history,
location data, usage patterns. Employees can review your conversations.
Your data is used for training (unless you find the buried opt-out).

Parapet collects: nothing.

Everything runs on your machine. The model is a file. The conversation history
is a local file you own. Delete it whenever you want. Air-gap it. Encrypt it.

[Privacy comparison infographic — "What They Collect" table]
```

### Pillar 5: Data Sovereignty (LinkedIn, legal tech, healthcare IT)

```
HEADLINE: "Attorney-client privilege doesn't survive a cloud AI prompt."

BODY:
When you paste a client document into ChatGPT:
- That data lives on OpenAI's servers
- It can be subpoenaed (third-party doctrine)
- You may have waived privilege (check your bar association guidance)

Parapet eliminates the third party. The model runs locally.
The document never leaves your device. No server to subpoena.

Same for:
• Healthcare — GDPR Art. 9 special category data
• Government — classified/sensitive-but-unclassified
• Defense — ITAR/EAR controlled technical data

If "send it to the AI" is currently blocked by your policy,
Parapet is the answer.
```

---

## Hashtag Strategy

### Primary Hashtags (use 3-5 per post)
| Hashtag | Platform | Volume | Relevance |
|---------|----------|--------|-----------|
| #LocalAI | All | Medium | Core category |
| #Privacy | All | Very High | Broad reach |
| #OpenSource | All | Very High | Broad reach |
| #GDPR | LinkedIn, X | Medium | Regulatory audience |
| #CyberSecurity | X, LinkedIn | High | Pentest audience |
| #SelfHosted | Reddit, X | Medium | r/selfhosted crossover |
| #Ollama | Reddit, X | Low-Medium | Niche but targeted |
| #EUTech | LinkedIn, X | Low-Medium | EU sovereignty angle |

### Secondary Hashtags (rotate in)
| Hashtag | When to use |
|---------|------------|
| #AIAct | Regulatory posts |
| #DORA | Financial sector posts |
| #Pentesting | Pentest posts |
| #AIPrivacy | Privacy comparison posts |
| #BuildInPublic | Development updates |
| #DataSovereignty | EU/government posts |
| #Docker | Technical posts |
| #LLM | Model benchmark posts |
| #Offline | Offline capability posts |

---

## Posting Schedule

### Weekly Cadence (after Launch Week)

| Day | Platform | Content | Pillar |
|-----|----------|---------|--------|
| **Mon** | Reddit (r/LocalLLaMA) | Technical update or benchmark result | Cost / Tech |
| **Tue** | Hacker News | Only if major update (don't over-post HN) | — |
| **Wed** | Twitter/X | Midweek thread or quick-tip | Rotate |
| **Thu** | LinkedIn | Long-form article or compliance angle | Regulatory / Sovereignty |
| **Fri** | Reddit (rotating sub) | r/privacy, r/netsec, r/selfhosted | Privacy / Pentest |
| **Sat** | GitHub | Commit, respond to issues, merge PRs | — |
| **Sun** | Planning | Review metrics, plan next week | — |

### Posting Times (UTC)
- **Reddit:** 14:00-16:00 UTC (EU afternoon + US morning overlap)
- **HN:** 13:00-15:00 UTC (catch both coasts)
- **Twitter/X:** 15:00-17:00 UTC
- **LinkedIn:** 08:00-10:00 UTC (EU business hours) or 15:00 UTC (US business hours)
- **Product Hunt:** 00:01 PST (08:01 UTC) — launch at midnight Pacific

---

## Engagement Tactics

### Reddit
- **Reply to EVERY comment** on launch posts for the first 48 hours
- Cross-link between related subreddits in comments (not posts)
- Comment on other people's posts in r/LocalLLaMA — build presence before your own posts
- Never post just a link — always a text post with the link inline
- Upvote ratio matters — if a post goes negative, delete and rethink the angle

### Hacker News
- Stay in the thread for the first 2 hours after posting
- Reply to technical questions with depth — HN rewards substance
- Don't argue. If someone says "this is just a wrapper," explain the architecture calmly
- The "Show HN" tag is important — it signals you built it and want feedback
- Don't ask for upvotes — HN detects and penalizes this

### Twitter/X
- Pin the launch thread to your profile
- Reply to relevant accounts in the space (@ollama, @huggingface, infosec accounts)
- Quote-tweet with insight, not just "this"
- Use 1-2 images per tweet (benchmark charts, architecture diagram, privacy comparison)
- Threads with data outperform opinion threads 3:1

### LinkedIn
- Tag relevant companies/people sparingly (only if genuinely relevant)
- The first 2 hours of engagement determine reach — post when your network is active
- Articles (long-form) outperform short posts for B2B/regulatory content
- Use the "Document" post type (upload a PDF one-pager) — LinkedIn boosts these

### GitHub
- Respond to issues within 24 hours
- Star and engage with similar projects (shows up in contributors' feeds)
- Add topics/tags: `local-ai`, `ollama`, `docker`, `privacy`, `security`, `offline`, `self-hosted`, `ai-agent`, `mit-license`, `container-hardening`
- Pin the best issue/discussion to the repo
- Add a "Sponsor" button (even if no tiers yet — it signals seriousness)

### Product Hunt
- Launch on a Tuesday or Wednesday (highest traffic days)
- First 4 hours of votes are weighted most heavily
- Have 5-10 friends/early users ready to upvote and comment
- Maker comment must be personal and story-driven — "why I built this" not "what it does"
- Reply to every comment within the first day
- Include a video/GIF of the product working (screen recording of the web UI)

---

## Metrics to Track

### Weekly
| Metric | Source | Target (Month 1) |
|--------|--------|-----------------|
| GitHub stars | GitHub Insights | 200+ |
| GitHub clones | GitHub Traffic | 500+ |
| Website visitors | Cloudflare/GA | 1,000+ |
| Reddit post karma | Reddit | 100+ per post |
| HN points | HN | 50+ |
| Twitter impressions | X Analytics | 10k+ per thread |
| LinkedIn article views | LinkedIn | 1,000+ |
| Product Hunt upvotes | PH | 100+ |

### Monthly (end of Month 1)
- GitHub: 500+ stars, 50+ clones/week sustained
- Website: 5,000+ visitors, >60% from organic/search
- Community: 10+ GitHub issues, 5+ contributors
- Press: 1-2 inbound media/ blog mentions
- Subscribers: 100+ on whatever list you build (newsletter, Discord, etc.)

---

## First Month Content Pipeline

### Week 2: Technical Deep Dives
- Mon Reddit: "How Parapet's seccomp profile blocks 200+ syscalls — design decisions"
- Thu LinkedIn: "The architectural compliance pattern — why regulated entities need local AI"
- Fri Reddit: Cross-post seccomp post to r/docker or r/cybersecurity

### Week 3: Model Benchmarks
- Mon Reddit: "We benchmarked 7 EU-native models — here's which one to use for what"
- Wed Twitter: Infographic thread — model comparison chart
- Thu LinkedIn: "Why native-language models beat translation-first AI for EU legal text"

### Week 4: Use Cases
- Mon Reddit: "How a pentester uses Parapet on air-gapped client networks"
- Thu LinkedIn: "GDPR Article 9 and AI — healthcare use case"
- Fri: End-of-month metrics review. Post a "Month 1: Building in Public" retrospective.

---

*Social media plan v1.0 — 2026-05-25*
*https://parapetai.dev | https://github.com/parapet-ai/parapet*
