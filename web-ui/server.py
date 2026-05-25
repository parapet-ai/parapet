# Copyright (c) 2026 Andrzej Dobosz. All rights reserved.
# Priority Date: 2026-05-18
# License: MIT -- see LICENSE file
#!/usr/bin/env python3
"""
parapet Web UI — FastAPI server (container edition).
Serves the chat UI, manages sessions, streams agent events via SSE.
"""
import asyncio
import json
import os
import re
import secrets
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Config (container paths) ───────────────────────────────────────────
WORKSPACE = Path("/workspace")
INBOX = WORKSPACE / "inbox"
OUTBOX = WORKSPACE / "outbox"
LOG_PATH = Path("/var/log/agent/agent.jsonl")
SESSION_DIR = WORKSPACE / ".parapet" / "sessions"
AUTH_DIR = WORKSPACE / ".parapet"
AUTH_TOKEN_FILE = AUTH_DIR / "auth_token"
UI_DIR = Path("/app")

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434").rstrip("/v1").rstrip("/")
SESSION_MODEL = os.environ.get("MODEL", "qwen2.5:3b")  # locked at launch — frontend cannot override

MAX_MSG_CHARS = 5000
MAX_EXCHANGES = 30
MAX_FILE_KB = 320
MIN_EXCHANGES = 10

# ── Auth token management ──────────────────────────────────────────
# Generate or load the auth token on startup. This prevents unauthorized
# local access to the agent on shared machines (Security Audit fix #3).
def _init_auth_token():
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    if AUTH_TOKEN_FILE.exists():
        return AUTH_TOKEN_FILE.read_text().strip()
    token = secrets.token_hex(16)  # 32-char hex token
    AUTH_TOKEN_FILE.write_text(token)
    return token

parapet_AUTH_TOKEN = _init_auth_token()
auth_scheme = HTTPBearer(auto_error=False)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """Validates the Bearer token. Returns None if no token provided (for public endpoints)."""
    if credentials is None:
        return None
    if not secrets.compare_digest(credentials.credentials, parapet_AUTH_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid auth token")
    return credentials.credentials

def require_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """Requires a valid token — used for state-changing endpoints."""
    if credentials is None or not secrets.compare_digest(credentials.credentials, parapet_AUTH_TOKEN):
        raise HTTPException(status_code=403, detail="Valid auth token required")
    return credentials.credentials

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

def _validate_session_id(session_id: str) -> str:
    """Sanitize session ID to prevent path traversal."""
    if not session_id or not _SESSION_ID_RE.match(session_id):
        raise HTTPException(400, "Invalid session ID (alphanumeric, dashes, underscores only)")
    return session_id


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────
@asynccontextmanager
async def lifespan(app):
    for d in [INBOX, OUTBOX, WORKSPACE / "processed", SESSION_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    # Proactively generate encryption keys (pentest E1/E2 — no lazy init)
    try:
        from crypto_vault import generate_keys_if_missing
        generate_keys_if_missing()
    except ImportError:
        pass
    yield

app = FastAPI(title="parapet Web UI", lifespan=lifespan)

INDEX_HTML = (UI_DIR / "index.html").read_text()


# ── Helpers ──────────────────────────────────────────────────────────

def uid():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rand = os.urandom(4).hex()[:6]
    return f"{stamp}-{rand}"


def sid():
    stamp = datetime.now().strftime("%Y%m%d")
    rand = os.urandom(2).hex()[:4]
    return f"{stamp}-{rand}"


def load_session(session_id: str) -> list:
    path = SESSION_DIR / f"{session_id}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_session(session_id: str, messages: list):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSION_DIR / f"{session_id}.json"

    capped = []
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str) and len(content) > MAX_MSG_CHARS:
            m = dict(m)
            m["content"] = content[:MAX_MSG_CHARS] + f"\n[... truncated at {MAX_MSG_CHARS}]"
        capped.append(m)

    if len(capped) > MAX_EXCHANGES * 2:
        capped = capped[-(MAX_EXCHANGES * 2):]

    raw = json.dumps(capped, indent=2, ensure_ascii=False)
    max_bytes = MAX_FILE_KB * 1024
    if len(raw.encode("utf-8")) > max_bytes:
        while len(capped) > MIN_EXCHANGES * 2:
            capped = capped[2:]
            raw = json.dumps(capped, indent=2, ensure_ascii=False)
            if len(raw.encode("utf-8")) <= max_bytes:
                break

    path.write_text(raw)


def build_context_prompt(prompt: str, history: list, workdir: str = "") -> str:
    parts = []
    if workdir:
        parts.append(f"[Working directory: /workspace/{workdir}]")
    if history:
        recent = history[-(20 * 2):]
        for m in recent:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, str) and len(content) > 2000:
                content = content[:2000] + "..."
            parts.append(f"[{role}]: {content}")
    parts.append(prompt)
    return "\n".join(parts)


# ── UI ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return Response(
        content=INDEX_HTML.replace("__parapet_AUTH_TOKEN__", parapet_AUTH_TOKEN),
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/auth-token", dependencies=[Depends(require_token)])
async def get_auth_token(request: Request):
    """Returns the auth token. Requires valid Bearer token (CRITICAL #3 fix)."""
    return {"token": parapet_AUTH_TOKEN}


@app.get("/api/stats")
async def system_stats():
    """Live GPU VRAM% and token counts for the dashboard."""
    stats = {
        "model": "none",
        "vram_used_mb": 0,
        "vram_total_mb": 6144,
        "vram_pct": 0,
        "gpu_name": "NVIDIA GPU",
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0,
    }

    # 1. Query Ollama for loaded model + VRAM
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/ps")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                if models:
                    stats["model"] = models[0].get("name", "unknown")
                    total_vram = sum(m.get("size_vram", m.get("size", 0)) for m in models)
                    stats["vram_used_mb"] = round(total_vram / (1024 * 1024), 1)
                    if stats["vram_total_mb"] > 0:
                        stats["vram_pct"] = round(stats["vram_used_mb"] / stats["vram_total_mb"] * 100, 1)
    except Exception as e:
        print(f"[stats] Ollama query failed: {e}", file=sys.stderr, flush=True)

    # 2. GPU temp monitored by run.ps1 watchdog (nvidia-smi not in container)

    # 3. Token counts from agent logs
    try:
        if LOG_PATH.exists():
            tokens_in, tokens_out = 0, 0
            with open(LOG_PATH, "r") as f:
                for line in f.readlines()[-5000:]:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("event") in ("task_complete", "model_response"):
                        usage = entry.get("detail", {}).get("usage", entry.get("usage", {}))
                        tokens_in += usage.get("input_tokens", 0)
                        tokens_out += usage.get("output_tokens", 0)
            stats["tokens_in"] = tokens_in
            stats["tokens_out"] = tokens_out
            stats["tokens_total"] = tokens_in + tokens_out
    except Exception as e:
        print(f"[stats] Log parsing failed: {e}", file=sys.stderr, flush=True)

    return stats


@app.get("/api/browse")
async def browse_workspace(path: str = ""):
    """Returns subdirectories in the workspace for the folder picker."""
    target = WORKSPACE
    if path and path != "/":
        safe = os.path.normpath(path).lstrip("/")
        target = (WORKSPACE / safe).resolve()
        if not str(target).startswith(str(WORKSPACE.resolve())):
            raise HTTPException(403, "Path outside workspace")
    if not target.exists() or not target.is_dir():
        return {"dirs": [], "current": path or "/", "parent": "/"}
    dirs = []
    try:
        for entry in sorted(target.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append(entry.name)
    except OSError:
        pass
    rel = str(target.relative_to(WORKSPACE)) if target != WORKSPACE else ""
    # Compute parent safely — may be outside workspace for root
    parent = "/"
    if target != WORKSPACE:
        try:
            p = target.parent
            if str(p.resolve()).startswith(str(WORKSPACE.resolve())):
                parent = str(p.relative_to(WORKSPACE))
        except (ValueError, OSError):
            pass
    return {"dirs": dirs, "current": rel or "/", "parent": parent}


@app.post("/api/upload-image", dependencies=[Depends(require_token)])
async def upload_image(req: Request):
    """Accept a pasted/uploaded screenshot, save to workspace/inbox/screenshots."""
    import base64, uuid as _uuid
    # Reject payloads larger than 10MB before parsing
    content_length = req.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 10MB)")
    body = await req.json()
    image_data = body.get("image", "")
    if not image_data:
        raise HTTPException(400, "No image data")
    # Strip data:image/...;base64, prefix if present
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    # Reject base64 input that would decode to >10MB (~1.33x overhead)
    if len(image_data) > 14 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 10MB)")
    try:
        raw = base64.b64decode(image_data)
    except Exception:
        raise HTTPException(400, "Invalid base64")
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 10MB)")
    shot_dir = INBOX / "screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    fname = f"shot-{_uuid.uuid4().hex[:8]}.png"
    (shot_dir / fname).write_bytes(raw)
    # Return a markdown reference the agent can understand
    rel_path = f"inbox/screenshots/{fname}"
    return {"ok": True, "path": rel_path, "markdown": f"![screenshot]({rel_path})"}


@app.get("/api/models")
async def list_models():
    """Return all models pulled in Ollama with tools, tier, and use-case info."""
    # Load registry for rich model metadata
    registry_models = {}
    registry_path = Path("/app/models.json")
    if registry_path.exists():
        try:
            reg = json.loads(registry_path.read_text())
            registry_models = reg.get("models", {})
        except (json.JSONDecodeError, OSError):
            pass

    result = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("models", []):
                    name = m.get("name", "")
                    # Try exact match first, then strip :latest
                    reg_entry = registry_models.get(name) or registry_models.get(name.replace(":latest", ""))
                    if reg_entry:
                        result.append({
                            "name": name,
                            "tools": reg_entry.get("tools", False),
                            "tier": reg_entry.get("tier", "unknown"),
                            "vram_gb": reg_entry.get("vram_gb", 0),
                            "display": reg_entry.get("display", name),
                            "categories": reg_entry.get("categories", []),
                        })
                    else:
                        result.append({
                            "name": name,
                            "tools": True,  # assume yes for unknown models
                            "tier": "unknown",
                            "vram_gb": 0,
                            "display": name,
                            "categories": [],
                        })
    except Exception as e:
        print(f"[models] Failed to query Ollama: {e}", file=sys.stderr, flush=True)
    return {"models": result}

@app.post("/api/rotate-key", dependencies=[Depends(require_token)])
async def rotate_auth_key():
    """Rotate the auth token — invalidates all existing sessions."""
    global parapet_AUTH_TOKEN
    new_token = secrets.token_hex(16)
    AUTH_TOKEN_FILE.write_text(new_token)
    parapet_AUTH_TOKEN = new_token
    return {"ok": True, "message": "Auth token rotated. Refresh the page to continue."}

@app.get("/api/current-model")
async def get_current_model():
    """Returns the session-locked model. Frontend cannot change it."""
    return {"model": SESSION_MODEL, "locked": True}

@app.post("/api/switch-model", dependencies=[Depends(require_token)])
async def switch_model(req: Request):
    """Explicit model switch by user — updates SESSION_MODEL."""
    global SESSION_MODEL
    body = await req.json()
    new_model = body.get("model", "").strip()
    if not new_model:
        raise HTTPException(400, "model is required")
    old_model = SESSION_MODEL
    SESSION_MODEL = new_model
    return {"ok": True, "previous": old_model, "current": SESSION_MODEL,
            "message": f"Switched to {new_model}. Start a new session for clean context."}

@app.get("/health")
async def health():
    key_ok = False
    try:
        from crypto_vault import is_key_generated
        key_ok = is_key_generated()
    except ImportError:
        pass
    return {"status": "ok", "encryption_keys": key_ok}


# ── SSDLC API ───────────────────────────────────────────────────────

@app.get("/api/ssdlc/projects")
async def ssdlc_list_projects(token: str = Depends(verify_token)):
    """List all SSDLC projects in the workspace."""
    ssdlc_dir = WORKSPACE / ".parapet" / "ssdlc"
    projects = []
    if ssdlc_dir.exists():
        for f in sorted(ssdlc_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text())
                projects.append({
                    "name": data.get("project", f.stem),
                    "status": data.get("overall_status", "unknown"),
                    "current_phase": data.get("current_phase"),
                    "updated_at": data.get("updated_at", ""),
                })
            except (json.JSONDecodeError, OSError):
                pass
    return {"projects": projects}


@app.get("/api/ssdlc/status")
async def ssdlc_status(project: str = Query("default"), token: str = Depends(verify_token)):
    """Get SSDLC progress summary for a project."""
    try:
        from ssdlc import get_progress
        return get_progress(project)
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/ssdlc/init", dependencies=[Depends(require_token)])
async def ssdlc_init(req: Request):
    """Initialize a new SSDLC project."""
    body = await req.json()
    project = body.get("project", "").strip()
    if not project:
        raise HTTPException(400, "project is required")
    try:
        from ssdlc import load_state, PHASES
        state = load_state(project)
        # Set metadata from request
        if body.get("owner"):
            state["metadata"]["owner"] = body["owner"]
        if body.get("compliance_frameworks"):
            state["metadata"]["compliance_frameworks"] = body["compliance_frameworks"]
        from ssdlc import save_state
        save_state(project, state)
        return {"ok": True, "project": project, "phases": list(PHASES.keys())}
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.post("/api/ssdlc/phase/start", dependencies=[Depends(require_token)])
async def ssdlc_phase_start(req: Request):
    """Start an SSDLC phase for a project."""
    body = await req.json()
    project = body.get("project", "").strip()
    phase = body.get("phase", "").strip()
    if not project or not phase:
        raise HTTPException(400, "project and phase are required")
    try:
        from ssdlc import start_phase
        return start_phase(project, phase)
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.post("/api/ssdlc/phase/complete", dependencies=[Depends(require_token)])
async def ssdlc_phase_complete(req: Request):
    """Complete an SSDLC phase for a project."""
    body = await req.json()
    project = body.get("project", "").strip()
    phase = body.get("phase", "").strip()
    if not project or not phase:
        raise HTTPException(400, "project and phase are required")
    try:
        from ssdlc import complete_phase
        return complete_phase(project, phase)
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.post("/api/ssdlc/check", dependencies=[Depends(require_token)])
async def ssdlc_check_item(req: Request):
    """Toggle a checklist item."""
    body = await req.json()
    project = body.get("project", "").strip()
    phase = body.get("phase", "").strip()
    item_id = body.get("item_id", "").strip()
    checked = body.get("checked", True)
    notes = body.get("notes", "")
    if not project or not phase or not item_id:
        raise HTTPException(400, "project, phase, and item_id are required")
    try:
        from ssdlc import check_item
        return check_item(project, phase, item_id, checked, notes)
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.post("/api/ssdlc/risk", dependencies=[Depends(require_token)])
async def ssdlc_add_risk(req: Request):
    """Add a risk finding to an SSDLC phase."""
    body = await req.json()
    project = body.get("project", "").strip()
    phase = body.get("phase", "").strip()
    title = body.get("title", "").strip()
    description = body.get("description", "").strip()
    likelihood = body.get("likelihood", 1)
    impact = body.get("impact", 1)
    stride_category = body.get("stride_category", "")
    mitigation = body.get("mitigation", "")
    if not project or not phase or not title:
        raise HTTPException(400, "project, phase, and title are required")
    try:
        from ssdlc import add_risk
        return add_risk(project, phase, title, description,
                        likelihood, impact, stride_category, mitigation)
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.post("/api/ssdlc/artifact", dependencies=[Depends(require_token)])
async def ssdlc_add_artifact(req: Request):
    """Record an artifact for an SSDLC phase."""
    body = await req.json()
    project = body.get("project", "").strip()
    phase = body.get("phase", "").strip()
    artifact_name = body.get("artifact_name", "").strip()
    file_path = body.get("file_path", "")
    file_hash = body.get("file_hash", "")
    if not project or not phase or not artifact_name:
        raise HTTPException(400, "project, phase, and artifact_name are required")
    try:
        from ssdlc import record_artifact
        return record_artifact(project, phase, artifact_name, file_path, file_hash)
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.get("/api/ssdlc/report")
async def ssdlc_report(project: str = Query("default"), token: str = Depends(verify_token)):
    """Generate full SSDLC report for a project."""
    try:
        from ssdlc import generate_report
        return generate_report(project)
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.get("/api/ssdlc/report/markdown")
async def ssdlc_report_markdown(project: str = Query("default"), token: str = Depends(verify_token)):
    """Generate SSDLC report as markdown."""
    try:
        from ssdlc import export_report_markdown
        md = export_report_markdown(project)
        return Response(content=md, media_type="text/markdown")
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


@app.get("/api/ssdlc/phases")
async def ssdlc_phase_definitions(token: str = Depends(verify_token)):
    """Get phase definitions with all checklist items."""
    try:
        from ssdlc import PHASES
        return {"phases": PHASES}
    except ImportError:
        raise HTTPException(500, "SSDLC module not available")


# ── Session API ─────────────────────────────────────────────────────

@app.get("/api/sessions")
async def list_sessions():
    sessions = []
    if SESSION_DIR.exists():
        for f in sorted(SESSION_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            sid_val = f.stem
            msgs = load_session(sid_val)
            sessions.append({
                "id": sid_val,
                "exchanges": len(msgs) // 2,
                "created": datetime.fromtimestamp(f.stat().st_ctime, tz=timezone.utc).isoformat(),
            })
    return {"sessions": sessions}


@app.post("/api/sessions", dependencies=[Depends(require_token)])
async def create_session(req: Request):
    body = await req.json() if await req.body() else {}
    session_id = body.get("id", sid())
    _validate_session_id(session_id)
    if not (SESSION_DIR / f"{session_id}.json").exists():
        save_session(session_id, [])
    return {"id": session_id}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    _validate_session_id(session_id)
    messages = load_session(session_id)
    return {"id": session_id, "messages": messages}


# ── Task API ────────────────────────────────────────────────────────

@app.post("/api/send", dependencies=[Depends(require_token)])
async def send_task(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")

    session_id = body.get("session_id", "")
    if session_id:
        _validate_session_id(session_id)
    workdir = body.get("workdir", "")

    history = load_session(session_id) if session_id else []
    full_prompt = build_context_prompt(prompt, history, workdir)

    task_id = uid()
    task = {"id": task_id, "prompt": full_prompt, "model": SESSION_MODEL}
    if session_id:
        task["session_id"] = session_id
    if workdir:
        task["workdir"] = workdir

    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / f"{task_id}.json").write_text(json.dumps(task))
    return {"task_id": task_id, "session_id": session_id}


@app.post("/api/approve", dependencies=[Depends(require_token)])
async def approve_tool(req: Request):
    body = await req.json()
    task_id = body.get("task_id", "")
    approved = body.get("approved", False)
    if not task_id:
        raise HTTPException(400, "task_id is required")
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / f"{task_id}.approved.json").write_text(json.dumps({"approved": approved}))
    return {"ok": True}


@app.get("/api/history")
async def history(limit: int = Query(50, le=200)):
    tasks = []
    outbox_files = sorted(OUTBOX.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in outbox_files:
        if f.name.endswith(".confirm.json"):
            continue
        try:
            data = json.loads(f.read_text())
            tasks.append({
                "task_id": data.get("task_id", f.stem),
                "status": data.get("status", "unknown"),
                "model": data.get("model", ""),
                "response": data.get("response", "")[:200],
                "usage": data.get("usage", {}),
            })
        except (json.JSONDecodeError, OSError):
            continue
        if len(tasks) >= limit:
            break
    return {"tasks": tasks}


@app.post("/api/save-exchange", dependencies=[Depends(require_token)])
async def save_exchange(req: Request):
    body = await req.json()
    session_id = body.get("session_id", "")
    user_msg = body.get("user", "")
    assistant_msg = body.get("assistant", "")
    task_id = body.get("task_id", "")
    if not session_id:
        raise HTTPException(400, "session_id is required")
    _validate_session_id(session_id)
    messages = load_session(session_id)
    if user_msg:
        messages.append({"role": "user", "content": user_msg})
    if assistant_msg:
        meta = f" [model: {body.get('model', '')}]" if body.get("model") else ""
        meta += f" [task: {task_id}]" if task_id else ""
        messages.append({"role": "assistant", "content": assistant_msg + meta})
    save_session(session_id, messages)
    return {"ok": True, "exchanges": len(messages) // 2}


# ── SSE Streaming ───────────────────────────────────────────────────

@app.get("/api/stream/{task_id}")
async def stream_task(task_id: str, req: Request):
    async def event_stream():
        waited = 0
        while not LOG_PATH.exists() and waited < 30:
            await asyncio.sleep(0.5)
            waited += 0.5

        if not LOG_PATH.exists():
            yield f"event: error\ndata: {json.dumps({'error': 'Log file not found — is the agent running?'})}\n\n"
            return

        try:
            st = LOG_PATH.stat()
            last_pos = st.st_size
            last_ino = st.st_ino
        except OSError:
            last_pos = 0
            last_ino = 0

        deadline = time.time() + 600
        result_sent = False

        while time.time() < deadline:
            if await req.is_disconnected():
                break

            try:
                st = LOG_PATH.stat()
                current_size = st.st_size
                if st.st_ino != last_ino or current_size < last_pos:
                    last_pos = 0
                    last_ino = st.st_ino

                if current_size > last_pos:
                    with open(LOG_PATH, "r") as f:
                        f.seek(last_pos)
                        new_data = f.read()
                        last_pos = f.tell()

                    for line in new_data.strip().split("\n"):
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        if entry.get("task_id") == task_id:
                            yield f"event: log\ndata: {json.dumps(entry, default=str)}\n\n"

                # Check for confirmation
                confirm_path = OUTBOX / f"{task_id}.confirm.json"
                if confirm_path.exists():
                    try:
                        confirm_data = json.loads(confirm_path.read_text())
                        yield f"event: confirm\ndata: {json.dumps(confirm_data)}\n\n"
                    except (json.JSONDecodeError, OSError):
                        pass

                # Check for result
                result_path = OUTBOX / f"{task_id}.json"
                if result_path.exists() and not result_sent:
                    try:
                        result = json.loads(result_path.read_text())
                    except (json.JSONDecodeError, OSError):
                        result = {"status": "error", "error": "Failed to read result"}
                    yield f"event: result\ndata: {json.dumps(result, default=str)}\n\n"
                    result_sent = True
                    return

            except OSError:
                pass

            await asyncio.sleep(0.3)

        if not result_sent:
            yield f"event: timeout\ndata: {json.dumps({'error': 'Task timed out after 10 minutes'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Passthrough — OpenAI-compatible /v1/chat/completions ─────────────
# Proxies directly to Ollama, bypassing the agent task queue.
# Matches raw Ollama throughput (50-287 tok/s vs 0.3-71 tok/s via agent).

@app.post("/v1/chat/completions")
@app.options("/v1/chat/completions")
async def chat_completions_passthrough(req: Request):
    if req.method == "OPTIONS":
        return Response(status_code=204)

    body = await req.json()
    stream = body.get("stream", False)

    if stream:
        async def _stream():
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_BASE}/v1/chat/completions",
                    json=body, timeout=300
                ) as upstream:
                    async for chunk in upstream.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            _stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    async with httpx.AsyncClient(timeout=300) as client:
        upstream = await client.post(
            f"{OLLAMA_BASE}/v1/chat/completions",
            json=body, timeout=300
        )
    return Response(content=upstream.content, status_code=upstream.status_code,
                    media_type=upstream.headers.get("content-type", "application/json"))


# ── WebSocket ───────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query("")):
    # Port is bound to 127.0.0.1 -- no external access possible. Skip auth.
    await ws.accept()
    subscriptions: set = set()
    log_pos = 0
    log_ino = 0

    try:
        if LOG_PATH.exists():
            st = LOG_PATH.stat()
            log_pos = st.st_size
            log_ino = st.st_ino

        while True:
            try:
                data = await asyncio.wait_for(ws.receive_json(), timeout=0.1)
                msg_type = data.get("type", "")

                if msg_type == "subscribe":
                    tid = data.get("task_id", "")
                    if tid:
                        subscriptions.add(tid)
                        await ws.send_json({"type": "subscribed", "task_id": tid})
                elif msg_type == "unsubscribe":
                    subscriptions.discard(data.get("task_id", ""))
                elif msg_type == "unsubscribe_all":
                    subscriptions.clear()

            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            try:
                st = LOG_PATH.stat()
                current_size = st.st_size
                if st.st_ino != log_ino or current_size < log_pos:
                    log_pos = 0
                    log_ino = st.st_ino
                if current_size > log_pos:
                    with open(LOG_PATH, "r") as f:
                        f.seek(log_pos)
                        new_data = f.read()
                        log_pos = f.tell()
                        log_ino = st.st_ino
                    for line in new_data.strip().split("\n"):
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        tid = entry.get("task_id", "")
                        if tid in subscriptions:
                            await ws.send_json({"type": "log", "entry": entry})
                            if entry.get("event") in ("task_complete", "task_error"):
                                rp = OUTBOX / f"{tid}.json"
                                if rp.exists():
                                    try:
                                        result = json.loads(rp.read_text())
                                    except (json.JSONDecodeError, OSError):
                                        result = {"status": "error", "error": "Failed to read result"}
                                    await ws.send_json({"type": "result", "task_id": tid, "result": result})

                for tid in list(subscriptions):
                    cp = OUTBOX / f"{tid}.confirm.json"
                    if cp.exists():
                        try:
                            cd = json.loads(cp.read_text())
                            await ws.send_json({"type": "confirm", "task_id": tid, "data": cd})
                        except (json.JSONDecodeError, OSError):
                            pass

            except OSError:
                pass

            await asyncio.sleep(2.0 if not subscriptions else 0.3)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
