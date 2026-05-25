# parapet v3.0.0-MIT | 2026-05-18
"""
Claude Code Parity Module — 5 features for full AI assistant capability.
1. Codebase understanding (AST parsing + dependency graph)
2. Diagram generation (Mermaid.js rendering)
3. PR/code review (multi-agent: generate → review → suggest)
4. Git integration (commit, diff, branch, PR description)
5. Optional private web search (DuckDuckGo, opt-in, no tracking)
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

import requests

OLLAMA_BASE = os.environ.get("OLLAMA_BASE",
    "http://host.docker.internal:11434").rstrip("/")
WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))


# ====================================================================
# 1. CODEBASE UNDERSTANDING — AST Parsing + Dependency Graph
# ====================================================================

def parse_python_file(filepath):
    """Extract functions, classes, imports, and dependencies from a Python file."""
    try:
        import ast as _ast
        tree = _ast.parse(Path(filepath).read_text())
        result = {"functions": [], "classes": [], "imports": [], "file": str(filepath)}

        for node in _ast.walk(tree):
            if isinstance(node, _ast.FunctionDef):
                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "decorators": [d.id for d in node.decorator_list
                                  if isinstance(d, _ast.Name)],
                })
            elif isinstance(node, _ast.ClassDef):
                methods = [n.name for n in node.body
                          if isinstance(n, _ast.FunctionDef)]
                result["classes"].append({
                    "name": node.name, "line": node.lineno,
                    "methods": methods,
                })
            elif isinstance(node, _ast.Import):
                for alias in node.names:
                    result["imports"].append(alias.name)
            elif isinstance(node, _ast.ImportFrom):
                if node.module:
                    result["imports"].append(node.module)

        return result
    except Exception:
        return {"file": str(filepath), "error": "parse_failed"}


def parse_powershell_file(filepath):
    """Extract functions, parameters from a PowerShell file."""
    content = Path(filepath).read_text()
    funcs = re.findall(r'function\s+([\w-]+)\s*\{', content, re.IGNORECASE)
    params = re.findall(r'param\s*\(([^)]*)\)', content, re.IGNORECASE)
    return {"file": str(filepath), "functions": funcs,
            "param_blocks": len(params)}


def build_dependency_graph(workspace_path=None):
    """Build a dependency graph of the entire project."""
    if workspace_path is None:
        workspace_path = WORKSPACE
    ws = Path(workspace_path)

    graph = {"nodes": {}, "edges": [], "stats": {}}
    file_count = 0

    for ext, parser in {".py": parse_python_file, ".ps1": parse_powershell_file,
                        ".psm1": parse_powershell_file}.items():
        for f in ws.rglob(f"*{ext}"):
            if any(skip in str(f) for skip in ["__pycache__", ".git", "node_modules", "venv"]):
                continue
            try:
                parsed = parser(f)
                rel = str(f.relative_to(ws))
                graph["nodes"][rel] = parsed
                file_count += 1

                # Build edges from imports
                if "imports" in parsed:
                    for imp in parsed["imports"]:
                        for other_rel in graph["nodes"]:
                            if imp.replace(".", "/") in other_rel or imp in other_rel:
                                graph["edges"].append({"from": rel, "to": other_rel, "type": "import"})
            except Exception:
                pass
            if file_count > 100:
                break

    graph["stats"] = {
        "total_files": file_count,
        "total_functions": sum(len(n.get("functions", [])) for n in graph["nodes"].values()),
        "total_classes": sum(len(n.get("classes", [])) for n in graph["nodes"].values()),
        "total_imports": sum(len(n.get("imports", [])) for n in graph["nodes"].values()),
    }
    return graph


def generate_project_summary(workspace_path=None):
    """Generate a human-readable project summary for the agent's system prompt."""
    graph = build_dependency_graph(workspace_path)
    stats = graph["stats"]

    # Find entry points
    entries = [rel for rel, node in graph["nodes"].items()
              if "main" in rel.lower() or "run" in rel.lower()
              or "server" in rel.lower() or "app" in rel.lower()]

    return f"""Project: {stats['total_files']} files, {stats['total_functions']} functions, {stats['total_classes']} classes
Entry points: {', '.join(entries[:8])}
Key files: {', '.join(sorted(graph['nodes'].keys())[:15])}
Import graph: {len(graph['edges'])} edges""" if stats['total_files'] > 0 else "(empty project)"


# ====================================================================
# 2. DIAGRAM GENERATION — Mermaid.js
# ====================================================================

MERMAID_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true,theme:'dark'}});</script>
</head><body><div class="mermaid">
{diagram}
</div></body></html>"""


def generate_diagram(description, diagram_type="flowchart", model="qwen2.5:3b"):
    """Use a model to generate Mermaid.js diagram from natural language description."""
    prompt = f"""Generate a Mermaid.js {diagram_type} diagram for this description.
Return ONLY the Mermaid code, no explanation, no markdown fences.

Description: {description}

Mermaid {diagram_type} syntax:
- flowchart: graph TD; A[Start]-->B[Process]; B-->C[End]
- sequence: sequenceDiagram; Alice->>Bob: Hello
- class: classDiagram; class Animal {{ +name: string }}
- er: erDiagram; CUSTOMER ||--o{{ ORDER : places

Return ONLY valid Mermaid code starting with the diagram type:"""

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 400, "temperature": 0.2},
        }, timeout=60)
        if resp.status_code == 200:
            diagram = resp.json().get("message", {}).get("content", "")
            # Clean any markdown fences
            diagram = re.sub(r'^```\w*\n?', '', diagram.strip())
            diagram = re.sub(r'\n?```$', '', diagram)
            html = MERMAID_TEMPLATE.format(diagram=diagram)

            # Save to workspace
            out_path = WORKSPACE / f"diagram-{int(time.time())}.html"
            out_path.write_text(html)
            return {"ok": True, "path": str(out_path.relative_to(WORKSPACE)),
                    "diagram": diagram[:500], "type": diagram_type}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def render_mermaid_inline(diagram_code):
    """Render Mermaid code to HTML and return the path."""
    html = MERMAID_TEMPLATE.format(diagram=diagram_code.strip())
    out_path = WORKSPACE / f"diagram-{int(time.time())}.html"
    out_path.write_text(html)
    return str(out_path.relative_to(WORKSPACE))


# ====================================================================
# 3. PR / CODE REVIEW — Multi-Agent Review
# ====================================================================

def review_code(code, language="python", reviewer_model="phi4-mini:latest"):
    """Have a second model review code for bugs, style, and improvements."""
    prompt = f"""Review this {language} code. Check for:
1. Bugs or logic errors
2. Style violations
3. Performance issues
4. Security vulnerabilities
5. Suggested improvements

Be specific. Reference line numbers if possible. Keep it constructive.

Code:
```{language}
{code[:4000]}
```

Return a structured review with sections: BUGS, STYLE, PERFORMANCE, SECURITY, SUGGESTIONS."""

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/chat", json={
            "model": reviewer_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 500, "temperature": 0.2},
        }, timeout=60)
        if resp.status_code == 200:
            return {"review": resp.json().get("message", {}).get("content", ""),
                    "reviewer": reviewer_model, "language": language}
    except Exception as e:
        return {"error": str(e)}


def review_diff(diff_text, reviewer_model="phi4-mini:latest"):
    """Review a git diff for issues."""
    prompt = f"""Review this git diff. Focus on:
1. Logic changes — are they correct?
2. Potential regressions
3. Missing edge cases
4. Style consistency with surrounding code
5. One-line summary at the end

Diff:
{diff_text[:4000]}

Return structured review with SUMMARY at the end."""

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/chat", json={
            "model": reviewer_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 500, "temperature": 0.2},
        }, timeout=60)
        if resp.status_code == 200:
            return {"review": resp.json().get("message", {}).get("content", ""),
                    "reviewer": reviewer_model}
    except Exception as e:
        return {"error": str(e)}


def generate_pr_description(branch_summary, model="qwen2.5:3b"):
    """Generate a PR description from branch changes."""
    prompt = f"""Write a professional pull request description based on these changes.
Include: Summary (1-2 bullets), Test plan (checklist), and any breaking changes.

Changes:
{branch_summary[:3000]}

Return the PR description. Use markdown formatting."""

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 400, "temperature": 0.3},
        }, timeout=60)
        if resp.status_code == 200:
            return {"pr_description": resp.json().get("message", {}).get("content", "")}
    except Exception as e:
        return {"error": str(e)}


# ====================================================================
# 4. GIT INTEGRATION
# ====================================================================

def git_status(workspace_path=None):
    """Get git status — branch, changed files, untracked."""
    if workspace_path is None:
        workspace_path = WORKSPACE
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=str(workspace_path),
            timeout=5, text=True).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=str(workspace_path),
            timeout=5, text=True).strip()
        return {"branch": branch, "status": status,
                "changed": len(status.split("\n")) if status else 0}
    except Exception as e:
        return {"error": str(e)}


def git_diff(workspace_path=None, staged=False):
    """Get git diff (unstaged or staged)."""
    if workspace_path is None:
        workspace_path = WORKSPACE
    args = ["git", "diff"]
    if staged:
        args.append("--staged")
    try:
        diff = subprocess.check_output(
            args, cwd=str(workspace_path), timeout=10, text=True)
        return {"diff": diff[:5000], "lines": len(diff.split("\n")) if diff else 0}
    except Exception as e:
        return {"error": str(e)}


def git_log(workspace_path=None, n=10):
    """Get recent git log."""
    if workspace_path is None:
        workspace_path = WORKSPACE
    try:
        log = subprocess.check_output(
            ["git", "log", f"-{n}", "--oneline", "--decorate"],
            cwd=str(workspace_path), timeout=5, text=True).strip()
        return {"log": log}
    except Exception as e:
        return {"error": str(e)}


def git_commit(message, files=None, workspace_path=None):
    """Stage and commit files."""
    if workspace_path is None:
        workspace_path = WORKSPACE
    try:
        if files:
            for f in files:
                subprocess.run(["git", "add", f], cwd=str(workspace_path),
                              timeout=10, capture_output=True)
        else:
            subprocess.run(["git", "add", "-A"], cwd=str(workspace_path),
                          timeout=10, capture_output=True)

        result = subprocess.run(["git", "commit", "-m", message],
            cwd=str(workspace_path), timeout=10,
            capture_output=True, text=True)
        return {"ok": result.returncode == 0,
                "output": result.stdout.strip() + result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}


def git_branch_summary(workspace_path=None, base_branch="main"):
    """Get summary of changes on current branch vs base."""
    if workspace_path is None:
        workspace_path = WORKSPACE
    try:
        diff_stat = subprocess.check_output(
            ["git", "diff", "--stat", f"{base_branch}..HEAD"],
            cwd=str(workspace_path), timeout=10, text=True).strip()
        log_commits = subprocess.check_output(
            ["git", "log", f"{base_branch}..HEAD", "--oneline"],
            cwd=str(workspace_path), timeout=5, text=True).strip()
        return {"diff_stat": diff_stat, "commits": log_commits,
                "commit_count": len(log_commits.split("\n")) if log_commits else 0}
    except Exception as e:
        return {"error": str(e)}


def generate_pr_full(workspace_path=None, base_branch="main"):
    """Full PR generation: get changes, review, write description."""
    summary = git_branch_summary(workspace_path, base_branch)
    if "error" in summary:
        return summary

    diff = git_diff(workspace_path)
    review = review_diff(diff.get("diff", "")) if diff.get("diff") else {"review": "(no changes)"}
    description = generate_pr_description(summary.get("diff_stat", ""))

    return {
        "summary": summary,
        "diff": diff,
        "review": review,
        "pr_description": description.get("pr_description", ""),
    }


# ====================================================================
# 5. PRIVATE WEB SEARCH (Opt-In, DuckDuckGo, No Tracking)
# ====================================================================

def web_search(query, max_results=5, use_tor=False):
    """Privacy-preserving web search. Supports DuckDuckGo, DuckDuckGo .onion via Tor,
    and SearXNG self-hosted instances."""
    import urllib.parse
    import urllib.request

    # Search backends in order of privacy preference
    backends = []

    # Option 1: Tor .onion (requires Tor proxy on 127.0.0.1:9050)
    if use_tor:
        backends.append({
            "name": "DuckDuckGo .onion (Tor)",
            "url": f"https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/html/?q={urllib.parse.quote(query)}",
            "proxy": "socks5h://127.0.0.1:9050",
        })

    # Option 2: DuckDuckGo clearnet (no tracking, but not anonymous)
    backends.append({
        "name": "DuckDuckGo (private, clearnet)",
        "url": f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}",
        "proxy": None,
    })

    for backend in backends:
        try:
            opener = urllib.request.build_opener()
            if backend["proxy"]:
                import socks
                import socket
                # Use PySocks for SOCKS5 proxy to Tor
                try:
                    import sockshandler
                    opener = urllib.request.build_opener(
                        sockshandler.SocksiPyHandler(
                            socks.SOCKS5, "127.0.0.1", 9050))
                except ImportError:
                    pass  # Fall through to clearnet

            req = urllib.request.Request(backend["url"], headers={
                "User-Agent": "parapet/3.0 (local AI; privacy-first; no tracking)"})
            html = opener.open(req, timeout=15).read().decode("utf-8")

            # Extract results
            results = []
            for match in re.finditer(
                r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>.*?'
                r'<a class="result__snippet"[^>]*>([^<]+)</a>',
                html, re.DOTALL):
                results.append({
                    "title": match.group(2).strip(),
                    "url": match.group(1).strip(),
                    "snippet": match.group(3).strip(),
                })
                if len(results) >= max_results:
                    break

            if results:
                return {"query": query, "results": results,
                        "source": backend["name"]}

        except Exception:
            continue  # Try next backend

    # All backends failed
    return {"query": query, "results": [],
            "error": "All search backends unavailable",
            "note": "Web search requires internet. Install Tor for .onion search: apt install tor"}


def web_search_searx(query, searx_instance=None, max_results=5):
    """Search via self-hosted SearXNG instance (maximum privacy).
    searx_instance: URL of your SearXNG server (e.g., http://localhost:8888)."""
    if searx_instance is None:
        searx_instance = os.environ.get("SEARX_INSTANCE", "")

    if not searx_instance:
        return {"query": query, "results": [], "source": "SearXNG",
                "error": "No SearXNG instance configured. Set SEARX_INSTANCE env var."}

    try:
        resp = requests.get(f"{searx_instance}/search", params={
            "q": query, "format": "json", "categories": "general",
        }, timeout=10)
        if resp.status_code != 200:
            return {"error": f"SearXNG returned {resp.status_code}"}

        data = resp.json()
        results = []
        for r in data.get("results", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", r.get("snippet", ""))[:300],
            })

        return {"query": query, "results": results,
                "source": f"SearXNG (self-hosted, {searx_instance})"}
    except Exception as e:
        return {"query": query, "results": [], "source": "SearXNG",
                "error": str(e)[:200]}


def web_search_for_agent(query):
    """Search the web and format results for agent context injection."""
    results = web_search(query)
    if not results.get("results"):
        return ""

    context = "Web search results:\n"
    for i, r in enumerate(results["results"], 1):
        context += f"{i}. {r['title']}\n   {r['snippet'][:200]}\n   {r['url']}\n\n"
    return context


# ====================================================================
# INTEGRATION HELPERS — Callable from server.py or ollama_agent.py
# ====================================================================

def ingest_document(filepath, chunk_size=500):
    """Split a document into overlap chunks for RAG indexing.
    Each chunk ~500 chars with 50-char overlap. Returns list of chunks."""
    path = Path(filepath)
    if not path.exists():
        return []
    text = path.read_text()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Don't split mid-word
        if end < len(text):
            while end > start and text[end] not in (' ', '\n', '.', ',', ';'):
                end -= 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"text": chunk, "file": str(path),
                          "position": start, "size": len(chunk)})
        start = end - 50  # 50-char overlap
        if start <= 0 or start >= len(text):
            break
        if start <= 0:
            start = 0
            break
    return chunks


def index_document(filepath):
    """Ingest and embed a document into the RAG index."""
    from rag_index import get_embedding, INDEX_FILE
    chunks = ingest_document(filepath)
    if not chunks:
        return {"ok": False, "error": "Could not read file"}

    # Get embeddings for all chunks
    indexed = 0
    import json as _json
    index = {}
    if INDEX_FILE.exists():
        try:
            index = _json.loads(INDEX_FILE.read_text())
        except (_json.JSONDecodeError, OSError):
            pass

    doc_path = str(Path(filepath).relative_to(WORKSPACE))
    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk["text"][:8000])
        if emb:
            chunk_id = f"{doc_path}#chunk{i}"
            index[chunk_id] = {
                "mtime": Path(filepath).stat().st_mtime,
                "size": chunk["size"],
                "embedding": emb,
                "preview": chunk["text"][:200],
            }
            indexed += 1

    INDEX_FILE.write_text(_json.dumps(index, indent=2, default=str))
    return {"ok": True, "indexed": indexed, "file": doc_path,
            "chunks": len(chunks)}


def search_document(query, top_k=5):
    """Search ingested documents by semantic similarity."""
    return search(query, top_k)  # reuse existing rag_index search


def summarize_document(query, filepath=None):
    """Search indexed documents and summarize relevant findings."""
    results = search_document(query, top_k=5)
    if not results:
        return {"answer": "No relevant content found in indexed documents.",
                "sources": []}
    return {"answer": f"Found {len(results)} relevant sections.",
            "sources": results}


def ocr_image(image_path, language="eng"):
    """Extract text from an image using Tesseract OCR. Fully local, no network.
    Supports: eng, spa, pol, fra, deu, ita, por, rus, chi_sim, jpn."""
    import subprocess as sp
    img = Path(image_path)
    if not img.exists():
        img = WORKSPACE / image_path
    if not img.exists():
        return {"ok": False, "error": f"Image not found: {image_path}"}

    try:
        result = sp.run(["tesseract", str(img), "stdout", "-l", language],
                       capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            text = result.stdout.strip()
            return {"ok": True, "text": text, "language": language,
                    "length": len(text), "path": str(img)}
        return {"ok": False, "error": result.stderr.strip()[:200]}
    except FileNotFoundError:
        return {"ok": False, "error": "Tesseract OCR not installed in container"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ocr_screenshot(image_path, language="eng"):
    """OCR a screenshot/image and return structured text."""
    result = ocr_image(image_path, language)
    if result.get("ok"):
        text = result["text"]
        # Detect if it's code or natural language
        is_code = any(kw in text for kw in ["def ", "function", "class ", "import ",
                      "param(", "#!/", "```", "const ", "let ", "var "])
        return {"ok": True, "text": text, "type": "code" if is_code else "text",
                "language": language, "path": result["path"]}
    return result


def enhance_agent_context(prompt, workspace_path=None):
    """Build enriched context for the agent: project summary + git status + search.
    Returns a string to prepend to the system prompt."""
    parts = []

    # Project understanding
    summary = generate_project_summary(workspace_path)
    if summary:
        parts.append(f"[Project Context]\n{summary}")

    # Git status
    git = git_status(workspace_path)
    if git and "error" not in git:
        parts.append(f"[Git: {git['branch']}, {git.get('changed', 0)} changed files]")

    return "\n".join(parts)


def get_claude_parity_capabilities():
    """Return a capabilities manifest for the UI/agent."""
    return {
        "codebase_understanding": True,
        "diagram_generation": True,
        "pr_review": True,
        "git_integration": True,
        "web_search": True,
        "web_search_provider": "DuckDuckGo (private, no tracking)",
        "models_used": {
            "code_reviewer": "phi4-mini:latest",
            "diagram_generator": "qwen2.5:3b",
            "pr_writer": "qwen2.5:3b",
        },
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: claude_parity.py [analyze|diagram|review|git|search|pr] [args...]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "analyze":
        graph = build_dependency_graph()
        print(json.dumps(graph["stats"], indent=2))
        print("\n=== Files ===")
        for f in sorted(graph["nodes"].keys())[:20]:
            print(f"  {f}")

    elif cmd == "diagram" and len(sys.argv) > 2:
        desc = " ".join(sys.argv[2:])
        result = generate_diagram(desc)
        print(json.dumps(result, indent=2))

    elif cmd == "review" and len(sys.argv) > 2:
        filepath = sys.argv[2]
        code = Path(filepath).read_text()
        review = review_code(code, "python")
        print(review["review"])

    elif cmd == "git":
        status = git_status()
        print(json.dumps(status, indent=2))

    elif cmd == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = web_search(query)
        for i, r in enumerate(results.get("results", []), 1):
            print(f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}\n")

    elif cmd == "pr":
        pr = generate_pr_full()
        print(json.dumps(pr, indent=2))
