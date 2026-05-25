# Copyright (c) 2026 Andrzej Dobosz. All rights reserved.
# Priority Date: 2026-05-18
# License: MIT -- see LICENSE file
# parapet v3.0.0 | 2026-05-18 | MIT/Apache 2.0
"""
Workspace RAG index ? embeds files with nomic-embed-text, provides semantic search.
Lightweight: cosine similarity on cached embeddings, re-index on file change.
"""
import json
import os
import time
from pathlib import Path

import requests

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://host.docker.internal:11434").rstrip("/")
EMBED_MODEL = "nomic-embed-text:latest"
WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
INDEX_FILE = WORKSPACE / ".parapet" / "rag_index.json"
_mem_index = None  # in-memory cache with embeddings (disk version strips them)
INDEXABLE_EXTS = {".py", ".ps1", ".sh", ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml",
                  ".html", ".css", ".js", ".ts", ".rs", ".go", ".java", ".c", ".h", ".cpp",
                  ".xml", ".toml", ".cfg", ".ini", ".env", ".dockerfile", ".psm1", ".psd1"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".claude", "processed",
             "screenshots", "benchmarks", "tests", "exports", "logs", "claude-backups",
             "session-history", ".parapet"}
MAX_FILE_KB = 5000
MAX_FILES = 200
CHUNK_TOKENS = 2000
CHUNK_OVERLAP = 200
CHARS_PER_TOKEN = 4  # rough estimate: ~4 chars per token for English text


def get_embedding(text: str) -> list:
    """Get embedding vector from nomic-embed-text."""
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/embed", json={
            "model": EMBED_MODEL, "input": text[:8000]
        }, timeout=30)
        if r.status_code == 200:
            return r.json().get("embeddings", [[]])[0]
    except Exception:
        pass
    return []


def cosine_sim(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_text(text: str, chunk_chars: int = None, overlap_chars: int = None) -> list:
    """Split text into overlapping chunks for embedding.
    Each chunk is ~CHUNK_TOKENS tokens, with CHUNK_OVERLAP token overlap."""
    if chunk_chars is None:
        chunk_chars = CHUNK_TOKENS * CHARS_PER_TOKEN
    if overlap_chars is None:
        overlap_chars = CHUNK_OVERLAP * CHARS_PER_TOKEN

    if len(text) <= chunk_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap_chars
    return chunks


def scan_workspace():
    """Scan workspace for indexable files. Returns {relpath: mtime, ...}"""
    files = {}
    for root, dirs, filenames in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in INDEXABLE_EXTS:
                continue
            fpath = Path(root) / fname
            try:
                size_kb = fpath.stat().st_size / 1024
                if size_kb > MAX_FILE_KB:
                    continue
                rel = str(fpath.relative_to(WORKSPACE))
                files[rel] = fpath.stat().st_mtime
            except OSError:
                continue
        if len(files) >= MAX_FILES:
            break
    return files


def build_index(force=False):
    """Build or update the embedding index. Returns index dict."""
    global _mem_index
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing
    existing = {}
    if INDEX_FILE.exists() and not force:
        try:
            existing = json.loads(INDEX_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    current_files = scan_workspace()
    index = {}
    new_count = 0

    for relpath, mtime in current_files.items():
        if relpath in existing and existing[relpath].get("mtime") == mtime:
            # Unchanged — reuse cached embedding
            index[relpath] = existing[relpath]
        else:
            # New or changed — re-embed
            fpath = WORKSPACE / relpath
            try:
                raw = fpath.read_text()
            except Exception:
                raw = fpath.read_bytes().decode("utf-8", errors="replace")

            # Chunk large files for embedding (fixes I-04)
            if len(raw) > 4000:
                chunks = chunk_text(raw)
            else:
                chunks = [raw]

            chunk_embeddings = []
            for chunk in chunks:
                emb = get_embedding(chunk)
                if emb:
                    chunk_embeddings.append({
                        "embedding": emb,
                        "preview": chunk[:200],
                        "size": len(chunk),
                    })

            if chunk_embeddings:
                index[relpath] = {
                    "mtime": mtime,
                    "size": len(raw),
                    "chunks": chunk_embeddings,
                    "preview": raw[:200],
                }
                new_count += 1

    # Save — strip embeddings (regenerated on change anyway)
    _mem_index = index  # keep embeddings in memory
    save_data = {}
    for relpath, entry in index.items():
        save_entry = {
            "mtime": entry["mtime"],
            "size": entry.get("size", 0),
            "preview": entry.get("preview", ""),
        }
        # Preserve chunk metadata (count, sizes) without embedding vectors
        if "chunks" in entry:
            save_entry["chunk_count"] = len(entry["chunks"])
            save_entry["chunk_sizes"] = [c["size"] for c in entry["chunks"]]
            save_entry["chunk_previews"] = [c["preview"] for c in entry["chunks"]]
        index[relpath] = entry  # keep in-memory with embeddings for search
        save_data[relpath] = save_entry
    INDEX_FILE.write_text(json.dumps(save_data, indent=2, default=str))
    search._last_build_ts = time.time()

    return {"indexed": len(index), "new": new_count, "total_files": len(current_files)}


def search(query: str, top_k: int = 5):
    """Semantic search over workspace files. Returns ranked list."""
    global _mem_index
    query_emb = get_embedding(query)
    if not query_emb:
        return []

    # Use in-memory index with embeddings if available and not stale
    index = {}
    if _mem_index is not None:
        # Check if disk index was updated by index_document (claude_parity)
        if INDEX_FILE.exists():
            try:
                disk_mtime = INDEX_FILE.stat().st_mtime
                if disk_mtime > getattr(search, "_last_build_ts", 0):
                    # Disk changed — reload and merge
                    disk = json.loads(INDEX_FILE.read_text())
                    for k, v in disk.items():
                        if k not in _mem_index or disk_mtime > v.get("mtime", 0):
                            _mem_index[k] = v
                    search._last_build_ts = disk_mtime
            except (json.JSONDecodeError, OSError):
                pass
        index = _mem_index
    elif INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    else:
        build_index()
        index = _mem_index if _mem_index is not None else {}

    results = []
    for relpath, entry in index.items():
        # Check chunk-level embeddings first (I-04: chunked reading)
        chunks = entry.get("chunks")
        if chunks:
            for ci, chunk in enumerate(chunks):
                emb = chunk.get("embedding")
                if not emb:
                    continue
                score = cosine_sim(query_emb, emb)
                if score > 0.3:
                    results.append({
                        "path": relpath,
                        "chunk": ci,
                        "chunk_count": len(chunks),
                        "score": round(score, 3),
                        "preview": chunk.get("preview", "")[:200],
                        "size": chunk.get("size", 0),
                    })
        else:
            # Legacy: single embedding per file
            emb = entry.get("embedding")
            if not emb:
                continue
            score = cosine_sim(query_emb, emb)
            if score > 0.3:
                results.append({
                    "path": relpath,
                    "score": round(score, 3),
                    "preview": entry.get("preview", "")[:200],
                    "size": entry.get("size", 0),
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        result = build_index(force=True)
        print(json.dumps(result, indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "search":
        results = search(sys.argv[2])
        print(json.dumps(results, indent=2))
    else:
        # Auto: build if needed, then show stats
        result = build_index()
        print(json.dumps(result, indent=2))
