# Copyright (c) 2026 Andrzej Dobosz. All rights reserved.
# Priority Date: 2026-05-24
# License: MIT -- see LICENSE file
"""
parapet SSDLC Engine -- Security System Development Life Cycle framework.

Six phases: Planning -> Analysis -> Design -> Implementation -> Maintenance -> Retirement.
State tracked in /workspace/.parapet/ssdlc/<project>.json.
Integrates with crypto_vault for artifact encryption and adaptive_engine for threat modeling.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
SSDLC_DIR = WORKSPACE / ".parapet" / "ssdlc"

# ── Phase definitions ──────────────────────────────────────────────────

PHASES = {
    "planning": {
        "order": 1,
        "label": "Planning",
        "description": "Identify security needs, evaluate risks, define scope, budget, policies, and roles.",
        "checklist": [
            {"id": "P1", "item": "Define security policy statement", "required": True},
            {"id": "P2", "item": "Establish risk appetite and tolerance levels", "required": True},
            {"id": "P3", "item": "Define project scope and budget", "required": True},
            {"id": "P4", "item": "Identify applicable compliance frameworks (GDPR, HIPAA, PCI-DSS, ISO 27001)", "required": True},
            {"id": "P5", "item": "Assign security roles and responsibilities", "required": True},
            {"id": "P6", "item": "Identify key stakeholders and sign-off authorities", "required": False},
            {"id": "P7", "item": "Define security metrics and KPIs", "required": False},
            {"id": "P8", "item": "Create project timeline with security gates", "required": True},
        ],
        "artifacts": [
            "security_policy.md",
            "risk_appetite_statement.md",
            "compliance_matrix.md",
            "roles_and_responsibilities.md",
        ],
    },
    "analysis": {
        "order": 2,
        "label": "Analysis",
        "description": "Detailed threat, risk, and control evaluation. Define security requirements, classify data, establish system criticality.",
        "checklist": [
            {"id": "A1", "item": "Perform threat assessment (identify threat actors, attack vectors)", "required": True},
            {"id": "A2", "item": "Conduct vulnerability identification (existing weaknesses, CVEs)", "required": True},
            {"id": "A3", "item": "Classify data by sensitivity (public, internal, confidential, restricted)", "required": True},
            {"id": "A4", "item": "Rate system criticality (low, medium, high, critical)", "required": True},
            {"id": "A5", "item": "Define security requirements (functional and non-functional)", "required": True},
            {"id": "A6", "item": "Perform control gap analysis (existing vs required controls)", "required": True},
            {"id": "A7", "item": "Calculate risk scores (likelihood x impact)", "required": True},
            {"id": "A8", "item": "Document privacy impact assessment (PIA)", "required": False},
        ],
        "artifacts": [
            "threat_assessment.md",
            "data_classification.md",
            "system_criticality.md",
            "risk_matrix.md",
            "security_requirements.md",
        ],
    },
    "design": {
        "order": 3,
        "label": "Design",
        "description": "Architect security blueprints, select hardware/software, conduct threat modeling (STRIDE), design access controls.",
        "checklist": [
            {"id": "D1", "item": "Create security architecture blueprint", "required": True},
            {"id": "D2", "item": "Conduct STRIDE threat modeling per component", "required": True},
            {"id": "D3", "item": "Design network segmentation and trust boundaries", "required": True},
            {"id": "D4", "item": "Define access control model (RBAC, ABAC, PBAC)", "required": True},
            {"id": "D5", "item": "Select encryption standards and key management strategy", "required": True},
            {"id": "D6", "item": "Design audit logging and monitoring architecture", "required": True},
            {"id": "D7", "item": "Plan secure API design (auth, rate limiting, input validation)", "required": True},
            {"id": "D8", "item": "Design disaster recovery and business continuity", "required": False},
            {"id": "D9", "item": "Select security tools (firewall, IDS/IPS, WAF, SIEM)", "required": True},
        ],
        "artifacts": [
            "security_architecture.md",
            "threat_model.md",
            "access_control_model.md",
            "encryption_strategy.md",
        ],
    },
    "implementation": {
        "order": 4,
        "label": "Implementation",
        "description": "Develop, configure, and activate security technologies. Secure coding, testing, and deployment.",
        "checklist": [
            {"id": "I1", "item": "Apply secure coding standards (OWASP Top 10, CWE Top 25)", "required": True},
            {"id": "I2", "item": "Configure firewalls and network security groups", "required": True},
            {"id": "I3", "item": "Deploy intrusion detection/prevention systems (IDS/IPS)", "required": True},
            {"id": "I4", "item": "Implement encryption at rest and in transit", "required": True},
            {"id": "I5", "item": "Set up identity and access management (IAM)", "required": True},
            {"id": "I6", "item": "Run SAST (static analysis) and SCA (dependency scanning)", "required": True},
            {"id": "I7", "item": "Run DAST (dynamic analysis) and penetration testing", "required": True},
            {"id": "I8", "item": "Harden containers, OS, and runtime environments", "required": True},
            {"id": "I9", "item": "Conduct security code review", "required": True},
            {"id": "I10", "item": "Validate all security controls before production deployment", "required": True},
        ],
        "artifacts": [
            "sast_report.md",
            "dast_report.md",
            "pentest_report.md",
            "hardening_checklist.md",
            "security_test_results.md",
        ],
    },
    "maintenance": {
        "order": 5,
        "label": "Maintenance",
        "description": "Monitor, patch, update, and continuously assess the system against emerging threats.",
        "checklist": [
            {"id": "M1", "item": "Establish patch management schedule (OS, dependencies, firmware)", "required": True},
            {"id": "M2", "item": "Configure security monitoring and alerting (SIEM)", "required": True},
            {"id": "M3", "item": "Implement user onboarding/offboarding procedures", "required": True},
            {"id": "M4", "item": "Enforce least-privilege access reviews (quarterly)", "required": True},
            {"id": "M5", "item": "Schedule routine vulnerability scans (weekly/monthly)", "required": True},
            {"id": "M6", "item": "Create incident response plan and run tabletop exercises", "required": True},
            {"id": "M7", "item": "Monitor CVE feeds for relevant vulnerabilities", "required": True},
            {"id": "M8", "item": "Review and rotate secrets, keys, and certificates", "required": True},
            {"id": "M9", "item": "Conduct periodic compliance audits", "required": False},
        ],
        "artifacts": [
            "patch_schedule.md",
            "incident_response_plan.md",
            "access_review_log.md",
            "vulnerability_scan_schedule.md",
        ],
    },
    "retirement": {
        "order": 6,
        "label": "Retirement",
        "description": "Securely decommission, sanitize data, dispose of hardware, and capture lessons learned.",
        "checklist": [
            {"id": "R1", "item": "Inventory all assets to be decommissioned", "required": True},
            {"id": "R2", "item": "Securely wipe/sanitize all data (NIST 800-88 standard)", "required": True},
            {"id": "R3", "item": "Revoke all certificates, keys, and credentials", "required": True},
            {"id": "R4", "item": "Remove from network and security groups", "required": True},
            {"id": "R5", "item": "Dispose of hardware per environmental regulations", "required": False},
            {"id": "R6", "item": "Notify affected users and stakeholders", "required": True},
            {"id": "R7", "item": "Archive logs and audit trails per retention policy", "required": True},
            {"id": "R8", "item": "Document lessons learned and gap analysis for replacement", "required": True},
        ],
        "artifacts": [
            "decommission_inventory.md",
            "data_sanitization_log.md",
            "revocation_certificate.md",
            "lessons_learned.md",
        ],
    },
}

# Risk scoring matrix: likelihood x impact
RISK_MATRIX = {
    "critical": {"min_score": 20, "color": "#f85149"},
    "high":     {"min_score": 15, "color": "#d2991d"},
    "medium":   {"min_score": 10, "color": "#bc8cff"},
    "low":      {"min_score": 5,  "color": "#3fb950"},
    "info":     {"min_score": 0,  "color": "#8b949e"},
}

# STRIDE categories for threat modeling
STRIDE = {
    "spoofing": "Attacker pretends to be someone/something else",
    "tampering": "Attacker modifies data or code",
    "repudiation": "Attacker denies performing an action",
    "information_disclosure": "Attacker accesses data they should not see",
    "denial_of_service": "Attacker prevents legitimate use",
    "elevation_of_privilege": "Attacker gains unauthorized permissions",
}


# ── State management ──────────────────────────────────────────────────

def _ensure_dir():
    SSDLC_DIR.mkdir(parents=True, exist_ok=True)


def load_state(project: str) -> dict:
    """Load SSDLC state for a project. Returns initialized state if none exists."""
    _ensure_dir()
    path = SSDLC_DIR / f"{project}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return _init_state(project)


def save_state(project: str, state: dict):
    _ensure_dir()
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = SSDLC_DIR / f"{project}.json"
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _init_state(project: str) -> dict:
    """Initialize a fresh SSDLC state for a project."""
    now = datetime.now(timezone.utc).isoformat()
    phases_state = {}
    for key, phase in PHASES.items():
        phases_state[key] = {
            "status": "pending",  # pending | in_progress | completed | skipped
            "started_at": None,
            "completed_at": None,
            "checklist": {c["id"]: {"checked": False, "notes": "", "checked_at": None}
                          for c in phase["checklist"]},
            "artifacts": {a: {"created": False, "path": "", "hash": ""}
                          for a in phase["artifacts"]},
            "risks": [],
            "notes": "",
        }
    state = {
        "project": project,
        "version": "1.0",
        "created_at": now,
        "updated_at": now,
        "current_phase": None,
        "overall_status": "not_started",
        "phases": phases_state,
        "metadata": {
            "owner": "",
            "team": [],
            "compliance_frameworks": [],
            "data_classification": "unclassified",
            "system_criticality": "unrated",
        },
    }
    return state


# ── Phase operations ──────────────────────────────────────────────────

def start_phase(project: str, phase_key: str) -> dict:
    """Begin a phase. Sets it to in_progress."""
    state = load_state(project)
    if phase_key not in PHASES:
        return {"ok": False, "error": f"Unknown phase: {phase_key}"}

    # Validate phase order — previous phases must be completed
    target_order = PHASES[phase_key]["order"]
    for key, ph in PHASES.items():
        if ph["order"] < target_order:
            if state["phases"][key]["status"] != "completed":
                return {"ok": False, "error": f"Cannot start {phase_key}: {key} is not yet completed",
                        "blocked_by": key}

    now = datetime.now(timezone.utc).isoformat()
    state["phases"][phase_key]["status"] = "in_progress"
    state["phases"][phase_key]["started_at"] = now
    state["current_phase"] = phase_key
    state["overall_status"] = "in_progress"
    save_state(project, state)
    return {"ok": True, "phase": phase_key, "started_at": now}


def complete_phase(project: str, phase_key: str) -> dict:
    """Complete a phase. Validates all required checklist items are checked."""
    state = load_state(project)
    if phase_key not in PHASES:
        return {"ok": False, "error": f"Unknown phase: {phase_key}"}

    ps = state["phases"][phase_key]
    if ps["status"] != "in_progress":
        return {"ok": False, "error": f"Phase {phase_key} is not in progress (status: {ps['status']})"}

    # Check all required items
    missing = []
    for c in PHASES[phase_key]["checklist"]:
        if c["required"] and not ps["checklist"][c["id"]]["checked"]:
            missing.append(c["id"])

    if missing:
        return {"ok": False, "error": "Required checklist items not completed",
                "missing_items": missing}

    now = datetime.now(timezone.utc).isoformat()
    ps["status"] = "completed"
    ps["completed_at"] = now

    # Auto-advance to next phase if there is one
    next_phase = None
    current_order = PHASES[phase_key]["order"]
    for key, ph in PHASES.items():
        if ph["order"] == current_order + 1:
            next_phase = key
            break

    if next_phase:
        state["current_phase"] = next_phase
    else:
        state["overall_status"] = "completed"

    save_state(project, state)
    return {"ok": True, "phase": phase_key, "completed_at": now, "next_phase": next_phase}


def check_item(project: str, phase_key: str, item_id: str, checked: bool = True, notes: str = "") -> dict:
    """Mark a checklist item as checked/unchecked."""
    state = load_state(project)
    if phase_key not in PHASES:
        return {"ok": False, "error": f"Unknown phase: {phase_key}"}

    ps = state["phases"][phase_key]
    if item_id not in ps["checklist"]:
        return {"ok": False, "error": f"Unknown checklist item: {item_id}"}

    now = datetime.now(timezone.utc).isoformat() if checked else None
    ps["checklist"][item_id] = {
        "checked": checked,
        "notes": notes,
        "checked_at": now,
    }
    save_state(project, state)
    return {"ok": True, "phase": phase_key, "item": item_id, "checked": checked}


def add_risk(project: str, phase_key: str, title: str, description: str,
             likelihood: int, impact: int, stride_category: str = "",
             mitigation: str = "") -> dict:
    """Add a risk finding to a phase. likelihood/impact scored 1-5."""
    state = load_state(project)
    if phase_key not in PHASES:
        return {"ok": False, "error": f"Unknown phase: {phase_key}"}

    likelihood = max(1, min(5, likelihood))
    impact = max(1, min(5, impact))
    score = likelihood * impact

    # Determine risk level
    level = "info"
    for lvl, meta in sorted(RISK_MATRIX.items(),
                            key=lambda x: x[1]["min_score"], reverse=True):
        if score >= meta["min_score"]:
            level = lvl
            break

    risk = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "description": description,
        "likelihood": likelihood,
        "impact": impact,
        "score": score,
        "level": level,
        "stride_category": stride_category,
        "mitigation": mitigation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
    }
    state["phases"][phase_key]["risks"].append(risk)
    save_state(project, state)
    return {"ok": True, "risk": risk}


def record_artifact(project: str, phase_key: str, artifact_name: str,
                    file_path: str, file_hash: str = "") -> dict:
    """Record that an artifact has been created."""
    state = load_state(project)
    if phase_key not in PHASES:
        return {"ok": False, "error": f"Unknown phase: {phase_key}"}

    ps = state["phases"][phase_key]
    if artifact_name not in ps["artifacts"]:
        return {"ok": False, "error": f"Unknown artifact: {artifact_name}"}

    ps["artifacts"][artifact_name] = {
        "created": True,
        "path": file_path,
        "hash": file_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(project, state)
    return {"ok": True, "artifact": artifact_name}


# ── Reporting ─────────────────────────────────────────────────────────

def get_progress(project: str) -> dict:
    """Return overall SSDLC progress summary."""
    state = load_state(project)
    phases_summary = {}
    total_items = 0
    checked_items = 0

    for key, phase in PHASES.items():
        ps = state["phases"][key]
        items = len(ps["checklist"])
        checked = sum(1 for c in ps["checklist"].values() if c["checked"])
        total_items += items
        checked_items += checked

        phases_summary[key] = {
            "label": phase["label"],
            "order": phase["order"],
            "status": ps["status"],
            "checklist_pct": round(checked / items * 100, 1) if items > 0 else 0,
            "items_checked": checked,
            "items_total": items,
            "risks_count": len(ps["risks"]),
            "risks_open": sum(1 for r in ps["risks"] if r.get("status") == "open"),
            "artifacts_created": sum(1 for a in ps["artifacts"].values() if a["created"]),
            "artifacts_total": len(ps["artifacts"]),
            "started_at": ps["started_at"],
            "completed_at": ps["completed_at"],
        }

    return {
        "project": project,
        "overall_status": state["overall_status"],
        "current_phase": state["current_phase"],
        "overall_pct": round(checked_items / total_items * 100, 1) if total_items > 0 else 0,
        "total_items": total_items,
        "checked_items": checked_items,
        "phases": phases_summary,
        "metadata": state["metadata"],
        "updated_at": state["updated_at"],
    }


def generate_report(project: str) -> dict:
    """Generate a full SSDLC report with all risks, findings, and status."""
    progress = get_progress(project)
    state = load_state(project)

    all_risks = []
    for key, phase in PHASES.items():
        for risk in state["phases"][key].get("risks", []):
            risk["phase"] = key
            risk["phase_label"] = phase["label"]
            all_risks.append(risk)

    risks_by_level = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
    for r in all_risks:
        risks_by_level[r["level"]].append(r)

    return {
        "project": project,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "progress": progress,
        "risks_summary": {
            "total": len(all_risks),
            "open": sum(1 for r in all_risks if r["status"] == "open"),
            "by_level": {k: len(v) for k, v in risks_by_level.items()},
        },
        "risks": risks_by_level,
        "framework_compliance": _compliance_checklist(state),
    }


def _compliance_checklist(state: dict) -> list:
    """Generate a compliance checklist based on selected frameworks."""
    frameworks = state.get("metadata", {}).get("compliance_frameworks", [])
    checks = []

    for fw in frameworks:
        fw_upper = fw.upper()
        if "GDPR" in fw_upper:
            checks.append({"framework": "GDPR", "control": "Data Protection by Design (Art. 25)",
                           "covered_by": ["analysis.A3", "design.D5"]})
            checks.append({"framework": "GDPR", "control": "Right to Erasure (Art. 17)",
                           "covered_by": ["retirement.R2"]})
            checks.append({"framework": "GDPR", "control": "Data Breach Notification (Art. 33-34)",
                           "covered_by": ["maintenance.M6"]})
        if "ISO" in fw_upper and "27001" in fw_upper:
            checks.append({"framework": "ISO 27001", "control": "A.8 Asset Management",
                           "covered_by": ["analysis.A3", "analysis.A4"]})
            checks.append({"framework": "ISO 27001", "control": "A.12 Operations Security",
                           "covered_by": ["implementation.I8", "maintenance.M2"]})
            checks.append({"framework": "ISO 27001", "control": "A.14 System Acquisition & Development",
                           "covered_by": ["implementation.I1", "implementation.I9"]})
        if "PCI" in fw_upper:
            checks.append({"framework": "PCI-DSS", "control": "Requirement 3: Protect Stored Cardholder Data",
                           "covered_by": ["implementation.I4"]})
            checks.append({"framework": "PCI-DSS", "control": "Requirement 6: Develop and Maintain Secure Systems",
                           "covered_by": ["implementation.I6", "maintenance.M1"]})
            checks.append({"framework": "PCI-DSS", "control": "Requirement 11: Regularly Test Security Systems",
                           "covered_by": ["implementation.I7", "maintenance.M5"]})

    return checks


def set_metadata(project: str, key: str, value) -> dict:
    """Update project metadata (owner, team, compliance_frameworks, etc)."""
    state = load_state(project)
    if key in state["metadata"]:
        state["metadata"][key] = value
        save_state(project, state)
        return {"ok": True, "key": key, "value": value}
    return {"ok": False, "error": f"Unknown metadata key: {key}"}


# ── Artifact export ───────────────────────────────────────────────────

def export_report_markdown(project: str) -> str:
    """Generate a markdown report suitable for sharing or archiving."""
    report = generate_report(project)
    p = report["progress"]

    lines = [
        f"# SSDLC Report — {project}",
        f"**Generated:** {report['generated_at']}",
        f"**Overall Status:** {p['overall_status'].replace('_', ' ').title()}",
        f"**Completion:** {p['overall_pct']}% ({p['checked_items']}/{p['total_items']} checklist items)",
        f"**Current Phase:** {p['current_phase'] or 'N/A'}",
        "",
        "## Phase Progress",
        "",
        "| Phase | Status | Checklist | Risks (Open) | Artifacts |",
        "|-------|--------|-----------|--------------|-----------|",
    ]
    for key, ps in p["phases"].items():
        status_icon = {"completed": "✅", "in_progress": "🔄", "pending": "⬜", "skipped": "⏭️"}.get(ps["status"], "❓")
        lines.append(
            f"| {status_icon} {ps['label']} | {ps['status']} | "
            f"{ps['checklist_pct']}% ({ps['items_checked']}/{ps['items_total']}) | "
            f"{ps['risks_count']} ({ps['risks_open']} open) | "
            f"{ps['artifacts_created']}/{ps['artifacts_total']} |"
        )
    lines.append("")

    lines.append("## Risk Summary")
    lines.append(f"- **Total risks:** {report['risks_summary']['total']}")
    lines.append(f"- **Open risks:** {report['risks_summary']['open']}")
    for level, count in report["risks_summary"]["by_level"].items():
        lines.append(f"- **{level.title()}:** {count}")
    lines.append("")

    for level, risks in report["risks"].items():
        if not risks:
            continue
        lines.append(f"### {level.title()} Risks")
        for r in risks:
            lines.append(f"- **{r['title']}** (Score: {r['score']}, {r['phase_label']})")
            lines.append(f"  - {r['description']}")
            if r.get("mitigation"):
                lines.append(f"  - Mitigation: {r['mitigation']}")
        lines.append("")

    if report.get("framework_compliance"):
        lines.append("## Compliance Mapping")
        for c in report["framework_compliance"]:
            lines.append(f"- **{c['framework']}** — {c['control']}: {', '.join(c['covered_by'])}")

    return "\n".join(lines)
