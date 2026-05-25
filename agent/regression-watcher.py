#!/usr/bin/env python3
"""
Watch source files for changes, auto-trigger benchmark-smoke on change.
Runs as a daemon. Catches regressions in real-time.
Usage: python3 regression-watcher.py [--interval 30] [--dir /path/to/project]
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

WATCH_EXTENSIONS = {".py", ".ps1", ".sh", ".psm1"}
WATCH_DIRS = ["agent-container", "web-ui"]
SKIP_FILES = {"rag_index.py", "import-claude-profile.py", "auto-ranker.py",
              "benchmark-smoke.py", "regression-watcher.py"}
INTERVAL = int(os.environ.get("WATCH_INTERVAL", "30"))
PROJECT_DIR = Path(os.environ.get("PROJECT_DIR", Path(__file__).resolve().parent))


def get_file_hashes():
    """Build a dict of {relpath: mtime} for watched files."""
    hashes = {}
    for watch_dir in WATCH_DIRS:
        d = PROJECT_DIR / watch_dir
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.suffix not in WATCH_EXTENSIONS:
                continue
            if f.name in SKIP_FILES:
                continue
            try:
                hashes[str(f.relative_to(PROJECT_DIR))] = f.stat().st_mtime
            except OSError:
                pass
    return hashes


def run_smoke_test():
    """Run benchmark-smoke.py. Returns True if passed."""
    smoke_script = PROJECT_DIR / "benchmark-smoke.py"
    if not smoke_script.exists():
        print("[watcher] benchmark-smoke.py not found — skipping", file=sys.stderr)
        return True
    try:
        result = subprocess.run(
            [sys.executable, str(smoke_script), "--ci"],
            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_DIR))
        passed = result.returncode == 0
        if passed:
            print(f"[watcher] Smoke test PASSED", file=sys.stderr)
        else:
            print(f"[watcher] Smoke test FAILED:\n{result.stderr[-500:]}", file=sys.stderr)
        return passed
    except subprocess.TimeoutExpired:
        print("[watcher] Smoke test TIMEOUT", file=sys.stderr)
        return False


def main():
    print(f"[watcher] Watching {WATCH_DIRS} for changes (interval={INTERVAL}s)", file=sys.stderr)
    last_hashes = get_file_hashes()
    last_test = time.time()

    while True:
        time.sleep(INTERVAL)
        current = get_file_hashes()

        # Detect new, modified, or deleted files
        changed = []
        for path, mtime in current.items():
            if path not in last_hashes or last_hashes[path] != mtime:
                changed.append(path)
        for path in last_hashes:
            if path not in current:
                changed.append(path + " (deleted)")

        if changed:
            print(f"[watcher] {len(changed)} files changed: {changed[:5]}", file=sys.stderr)
            last_hashes = current
            # Debounce — only test if at least 10s since last test
            if time.time() - last_test > 10:
                run_smoke_test()
                last_test = time.time()


if __name__ == "__main__":
    main()
