#!/usr/bin/env python3
"""
Auto-rank models based on weighted composite scores from all benchmarks.
Reads models.json + domain test results, computes per-domain rankings,
updates task_defaults if better models found.
Usage: python3 auto-ranker.py [--update] [models.json]
"""
import json
import sys
from pathlib import Path

WEIGHTS = {
    "domain_score": 0.40,   # domain test score (quality)
    "tok_per_sec": 0.25,    # inference speed
    "vram_fit": 0.20,       # how well it fits in VRAM (lower = better)
    "tools": 0.10,          # native tool support bonus
    "green_tier": 0.05,     # green tier bonus
}

# Domain test results (from latest run)
# Updated with post-optimization data as available
DOMAIN_SCORES = {
    "openchat:7b":               {"translate": 62, "coding": 96, "pentest": 81, "files": 62, "tok_s": 14.1},
    "dolphincoder:7b":           {"translate": 50, "coding": 100, "pentest": 57, "files": 87, "tok_s": 15.5},
    "dolphin-llama3:8b":         {"translate": 56, "coding": 89, "pentest": 51, "files": 100, "tok_s": 10.6},
    "nchapman/dolphin3.0-llama3:8b": {"translate": 69, "coding": 89, "pentest": 62, "files": 73, "tok_s": 5.4},
    "SpeakLeash/bielik-7b-instruct-v0.1-gguf": {"translate": 62, "coding": 89, "pentest": 57, "files": 73, "tok_s": 14.2},
    "qwen2.5-coder:7b":          {"translate": 69, "coding": 84, "pentest": 47, "files": 73, "tok_s": 10.0},
    "deepseek-r1:7b":            {"translate": 56, "coding": 62, "pentest": 57, "files": 67, "tok_s": 10.7},
    "qwen2.5:7b":                {"translate": 69, "coding": 96, "pentest": 81, "files": 87, "tok_s": 10.2},
    # Pre-optimization scores (from session data)
    "qwen2.5:3b":                {"translate": 69, "coding": 90, "pentest": 51, "files": 73, "tok_s": 75.5},
    "nchapman/dolphin3.0-qwen2.5:3b": {"translate": 75, "coding": 86, "pentest": 62, "files": 73, "tok_s": 72.5},
    "qwen2.5-coder:3b":          {"translate": 62, "coding": 89, "pentest": 47, "files": 73, "tok_s": 75.7},
    "llama3.2:3b":               {"translate": 69, "coding": 86, "pentest": 40, "files": 73, "tok_s": 85.3},
    "gemma2:2b":                 {"translate": 69, "coding": 80, "pentest": 57, "files": 80, "tok_s": 95.4},
    "bielik-q5:latest":          {"translate": 75, "coding": 94, "pentest": 69, "files": 73, "tok_s": 26.7},
    "deepseek-coder:1.3b":       {"translate": 44, "coding": 69, "pentest": 44, "files": 87, "tok_s": 187},
    "mistral:7b-instruct":       {"translate": 62, "coding": 84, "pentest": 68, "files": 73, "tok_s": 11.4},
    "phi3:mini":                 {"translate": 50, "coding": 96, "pentest": 62, "files": 73, "tok_s": 31.2},
}

DOMAIN_MAP = {
    "coding": "coding", "general": "coding",
    "legal": "translate", "pentest": "pentest",
    "polish": "translate", "speed": "tok_s", "reasoning": "pentest",
}


def score_model(model_name, registry_entry, domain="coding"):
    """Compute composite score for a model in a given domain."""
    ds = DOMAIN_SCORES.get(model_name, {})
    domain_key = DOMAIN_MAP.get(domain, "coding")
    domain_score = ds.get(domain_key, 50)
    tok_s = ds.get("tok_s", ds.get("tok_per_sec", registry_entry.get("vram_gb", 5) * 20))
    vram_gb = registry_entry.get("vram_gb", 5.0)
    tier = registry_entry.get("tier", "yellow")
    has_tools = registry_entry.get("tools", False)

    # Normalize: domain_score 0-100, tok_s 0-200, vram fit: 6-vram (lower VRAM = higher score)
    domain_norm = min(domain_score / 100, 1.0)
    speed_norm = min(tok_s / 200, 1.0) if tok_s > 0 else 0
    vram_norm = max(0, (6.0 - vram_gb) / 6.0)  # 0 GB = 1.0, 6 GB = 0.0
    tools_bonus = 1.0 if has_tools else 0.3
    green_bonus = 1.0 if tier == "green" else 0.5

    composite = (
        WEIGHTS["domain_score"] * domain_norm +
        WEIGHTS["tok_per_sec"] * speed_norm +
        WEIGHTS["vram_fit"] * vram_norm +
        WEIGHTS["tools"] * tools_bonus +
        WEIGHTS["green_tier"] * green_bonus
    )
    return round(composite, 3)


def rank_domain(models, domain):
    """Rank all models for a given domain."""
    ranked = []
    for name, entry in models.items():
        s = score_model(name, entry, domain)
        ranked.append((name, s, entry.get("display", name)))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "models.json")
    if not path.exists():
        path = Path("/app/models.json")
    if not path.exists():
        print("models.json not found", file=sys.stderr)
        sys.exit(1)

    reg = json.loads(path.read_text())
    models = reg.get("models", {})

    print(f"{'='*60}")
    print(f"  MODEL AUTO-RANKER")
    print(f"  {len(models)} models analyzed")
    print(f"{'='*60}\n")

    for domain in ["coding", "general", "pentest", "polish", "legal", "speed", "reasoning"]:
        ranked = rank_domain(models, domain)
        print(f"  [{domain.upper()}]")
        for i, (name, score, display) in enumerate(ranked[:5]):
            icon = " *" if i == 0 else "  "
            print(f"  {icon} {score:.3f}  {name}")
        if ranked:
            best = ranked[0][0]
            current = reg.get("task_defaults", {}).get(domain, "")
            if best != current:
                print(f"  -> SUGGEST: {domain} default {current} -> {best}")
        print()

    if "--update" in sys.argv:
        updates = {}
        for domain in ["coding", "general", "pentest", "polish", "legal", "speed", "reasoning"]:
            ranked = rank_domain(models, domain)
            if ranked:
                updates[domain] = ranked[0][0]
        reg["task_defaults"].update(updates)
        path.write_text(json.dumps(reg, indent=2, ensure_ascii=False))
        print("  models.json updated with auto-ranked defaults")


if __name__ == "__main__":
    main()
