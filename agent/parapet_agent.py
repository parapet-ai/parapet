# Copyright (c) 2026 Andrzej Dobosz. All rights reserved.
# Priority Date: 2026-05-18
# License: MIT -- see LICENSE file
#!/usr/bin/env python3
"""
parapet Ollama Agent Daemon.
Reads tasks from /workspace/inbox/, processes them with a local Ollama model
via OpenAI-compatible API, writes results to /workspace/outbox/.
All activity logged as JSONL.
"""
import signal
import sys
import json
import os
import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

# â”€â”€ Graceful shutdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_shutdown_requested = False

def _handle_sigterm(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    print("[INFO] SIGTERM received â€” finishing current task then exiting", file=sys.stderr)

signal.signal(signal.SIGTERM, _handle_sigterm)

# â”€â”€ Config from environment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434/v1")
MODEL = os.getenv("MODEL", "qwen2.5:3b")
ALLOW_SHELL = os.getenv("ALLOW_SHELL", "true").lower() == "true"
REQUIRE_CONFIRMATION = os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"
LOG_OUTPUT = Path(os.getenv("LOG_OUTPUT", "/var/log/agent/agent.jsonl"))

WORKSPACE = Path("/workspace")
INBOX = WORKSPACE / "inbox"
OUTBOX = WORKSPACE / "outbox"
PROCESSED = WORKSPACE / "processed"

SYSTEM_PROMPT = """You are an AI coding agent running in a Linux container.
You work in /workspace and can read, write, and execute code there.

Rules:
- THINK before acting. Plan your approach in your response before calling tools.
- Be concise. Use tools to accomplish tasks â€” don't just describe what to do.
- When writing code, prefer working, minimal implementations.
- If you don't know something, say so rather than guessing.
- The workspace persists between sessions â€” use it for notes and state.
- You can call multiple tools in sequence to complete complex tasks."""

# Fallback system prompt for models without native tool calling support.
# Injects tool instructions directly into the system prompt so the model
# outputs tools as markdown code blocks instead of using the API tools array.
# Pattern matched from Aider + Open Interpreter's approach to model compatibility.
FALLBACK_TOOL_PROMPT = """

You have access to tools. Use them ONLY when you need to read files,
write files, run commands, or list directories. For normal conversation
and questions, just reply directly -- do NOT use tools.

Tool formats (use only when you need to DO something):

Run a shell command (working directory: /workspace):
```shell
<your command here>
```

Read a file:
```read
<path relative to /workspace>
```

Write/create a file:
```write
<path relative to /workspace>
<file content here>
```

List files in a directory:
```list
<path relative to /workspace, or . for root>
```"""


# â”€â”€ Tool definitions (OpenAI function-calling format) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file under /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path relative to /workspace, e.g. 'src/main.py'",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file under /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path relative to /workspace, e.g. 'src/output.txt'",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file contents to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories under a path in /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path relative to /workspace, e.g. 'src/' or '.' for root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Execute a shell command inside the container workspace. "
            "Commands run with /workspace as working directory. Output truncated at 50KB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
]

DANGEROUS_TOOLS = {"run_shell", "write_file"}

# Shell metacharacter blocklist — prevents command injection from LLM output (CRITICAL #2 fix)
DANGEROUS_SHELL_PATTERNS = ['|', ';', '&&', '||', '`', '$(', '>', '>>', '<', '&>', '\n', '\r']

# â”€â”€ Pluggable tool system (FIX #4) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
PLUGIN_TOOLS = {}
TOOLS_DIR = WORKSPACE / "tools"

def load_plugins():
    """Scan workspace/tools/*.py and register tools at startup."""
    if not TOOLS_DIR.exists():
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        return
    def add_tool(spec, handler):
        name = spec.get("function", {}).get("name", "unknown")
        PLUGIN_TOOLS[name] = {"spec": spec, "handler": handler}
        print(f"  [plugin] tool: {name}", file=sys.stderr)
    for f in sorted(TOOLS_DIR.glob("*.py")):
        if f.name.startswith("_"): continue
        try:
            code = compile(f.read_text(), str(f), 'exec')
            exec(code, {"register": add_tool, "__builtins__": __builtins__})
        except Exception as e:
            print(f"  [plugin] FAILED {f.name}: {e}", file=sys.stderr)

def get_all_tools():
    """Built-in + plugin tool specs merged."""
    return list(TOOLS) + [e["spec"] for e in PLUGIN_TOOLS.values()]

def execute_plugin_tool(name, args):
    if name not in PLUGIN_TOOLS: return {"error": f"Unknown: {name}"}
    try:
        r = PLUGIN_TOOLS[name]["handler"](**args)
        return r if isinstance(r, dict) else {"output": str(r)}
    except Exception as e:
        return {"error": str(e)}

# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def resolve_path(relative: str) -> Path:
    """Resolve a user-supplied path, keeping it within /workspace."""
    p = (WORKSPACE / relative).resolve()
    p.relative_to(WORKSPACE)  # raises ValueError on escape
    return p


def log_event(event_type: str, task_id: str = "", detail=None,
              model: str = "", tool_name: str = ""):
    """Append a JSONL log line."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "task_id": task_id,
    }
    if detail:
        record["detail"] = detail
    if model:
        record["model"] = model
    if tool_name:
        record["tool"] = tool_name
    try:
        LOG_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_OUTPUT, "a") as f:
            f.write(json.dumps(record, default=str) + chr(10))
    except Exception:
        print(f"[WARN] Cannot write log: {sys.exc_info()[1]}", file=sys.stderr)


def execute_tool(name: str, args: dict, task_id: str) -> dict:
    """Execute a single tool call and return the result."""
    try:
        if name == "read_file":
            p = resolve_path(args["path"])
            if not p.exists():
                return {"error": f"File not found: {args['path']}"}
            content = p.read_text()[:50_000]
            return {"output": content}

        elif name == "write_file":
            p = resolve_path(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"])
            log_event("file_written", task_id,
                      detail={"path": str(p), "size": len(args["content"])})
            return {"output": f"Wrote {len(args['content'])} bytes to {args['path']}"}

        elif name == "list_directory":
            p = resolve_path(args["path"])
            if not p.is_dir():
                return {"error": f"Not a directory: {args['path']}"}
            items = []
            for child in sorted(p.iterdir()):
                suffix = "/" if child.is_dir() else ""
                try:
                    size = child.stat().st_size if child.is_file() else 0
                except OSError:
                    size = 0
                label = f"  {child.name}{suffix}"
                if not suffix:
                    label += f"  ({size}B)"
                items.append(label)
            return {"output": chr(10).join(items) if items else "(empty directory)"}

        elif name == "run_shell":
            if not ALLOW_SHELL:
                return {"error": "Shell execution is disabled."}
            cmd = args["command"]
            # Block shell metacharacters to prevent command injection (CRITICAL #2 fix)
            if any(p in cmd for p in DANGEROUS_SHELL_PATTERNS):
                log_event("shell_blocked", task_id,
                          detail={"cmd": cmd, "reason": "dangerous metacharacter detected"})
                return {"error": "Command contains shell metacharacters — blocked for safety. Use separate tool calls or write a script file and execute it directly."}
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(WORKSPACE),
            )
            out = (result.stdout or "") + (result.stderr or "")
            if result.returncode != 0:
                out += f"\n[exit code: {result.returncode}]"
            log_event("shell_exec", task_id,
                      detail={"cmd": args["command"], "exit": result.returncode})
            return {"output": out.strip() or "(no output)"}

        else:
            # Check plugin tools before giving up
            if name in PLUGIN_TOOLS:
                return execute_plugin_tool(name, args)
            return {"error": f"Unknown tool: {name}"}

    except ValueError:
        return {"error": f"Path escapes /workspace: {args.get('path', '?')}"}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 120s"}
    except Exception:
        return {"error": str(sys.exc_info()[1])}


def request_confirmation(tool_name: str, args: dict, task_id: str) -> bool:
    """Write confirmation request and wait for approval."""
    confirm_path = OUTBOX / f"{task_id}.confirm.json"
    approve_path = INBOX / f"{task_id}.approved.json"

    confirm_path.parent.mkdir(parents=True, exist_ok=True)
    confirm_path.write_text(json.dumps({
        "task_id": task_id,
        "tool": tool_name,
        "args": args,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }))
    log_event("confirm_requested", task_id, detail={"tool": tool_name, "args": args})

    deadline = time.time() + 120
    while time.time() < deadline:
        if approve_path.exists():
            try:
                data = json.loads(approve_path.read_text())
                approved = data.get("approved", False)
                approve_path.unlink()
                return approved
            except (json.JSONDecodeError, OSError):
                pass  # partial write â€” retry next iteration
        time.sleep(0.5)

    # Timeout â€” deny
    try:
        confirm_path.unlink()
    except OSError:
        pass
    return False


def write_result(task_id: str, result: dict):
    OUTBOX.mkdir(parents=True, exist_ok=True)
    out_path = OUTBOX / f"{task_id}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str))


# â”€â”€ Prompt-based tool parser (for models without native tool calling) â”€â”€â”€â”€â”€

import re

def parse_prompt_tools(text: str):
    """Scan model output for tool blocks in markdown code fences.
    Returns list of (tool_name, args_dict, raw_block) tuples.
    Supported formats:
      ```shell\n<command>\n```           -> run_shell
      ```read\n<path>\n```              -> read_file
      ```write\n<path>\n<content>\n``` -> write_file
      ```list\n<path>\n```             -> list_directory
    """
    tools_found = []
    # Match code fences with a tool language tag
    pattern = r'```(shell|read|write|list)\s*\n(.*?)```'
    for match in re.finditer(pattern, text, re.DOTALL):
        tool_type = match.group(1)
        body = match.group(2).strip()

        if tool_type == 'shell':
            tools_found.append(('run_shell', {'command': body}, match.group(0)))
        elif tool_type == 'read':
            tools_found.append(('read_file', {'path': body.split('\n')[0].strip()}, match.group(0)))
        elif tool_type == 'write':
            lines = body.split('\n', 1)
            path = lines[0].strip()
            content = lines[1] if len(lines) > 1 else ''
            tools_found.append(('write_file', {'path': path, 'content': content}, match.group(0)))
        elif tool_type == 'list':
            path = body.split('\n')[0].strip() or '.'
            tools_found.append(('list_directory', {'path': path}, match.group(0)))

    return tools_found


def strip_tool_blocks(text: str):
    """Remove tool code fences from text, returning the clean response."""
    return re.sub(r'```(shell|read|write|list)\s*\n.*?```', '', text, flags=re.DOTALL).strip()


# â”€â”€ Core conversation loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def process_task(client: OpenAI, task: dict):
    """Run a single task through the local model with tool-calling loop.
    Supports both native OpenAI tool calling and prompt-based fallback
    for models that don't implement the tools API (dolphin, wizardlm2, etc)."""
    task_id = task["id"]
    prompt = task["prompt"]
    model = task.get("model", MODEL)
    use_native_tools = True  # will be set to False on first "does not support tools" error

    log_event("task_start", task_id,
              detail={"prompt": prompt[:500], "model": model}, model=model)

    system_content = SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompt},
    ]

    try:
        for _ in range(30):  # max tool-calling rounds
            if use_native_tools:
                # --- Native tool calling path ---
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=get_all_tools(),
                        max_tokens=4096,
                        temperature=0.3,
                    )
                except Exception as e:
                    err = str(e)
                    if "does not support tools" in err:
                        # Switch to prompt-based tools for this model
                        log_event("tools_fallback", task_id,
                                  detail={"model": model, "reason": "native tools not supported"})
                        use_native_tools = False
                        messages[0]["content"] = SYSTEM_PROMPT + FALLBACK_TOOL_PROMPT
                        continue  # retry the loop iteration without tools
                    else:
                        raise

                choice = response.choices[0]
                msg = choice.message
                text = msg.content or ""
                tool_calls = msg.tool_calls or []

                if text:
                    log_event("model_response", task_id,
                              detail={"text": text[:2000], "finish": choice.finish_reason})

                if not tool_calls:
                    result = {
                        "task_id": task_id, "status": "complete",
                        "response": text, "model": model,
                        "usage": {
                            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                            "output_tokens": response.usage.completion_tokens if response.usage else 0,
                        },
                    }
                    log_event("task_complete", task_id, detail=result)
                    write_result(task_id, result)
                    return

                # Append assistant message with native tool calls
                assistant_msg = {"role": "assistant", "content": text or None}
                tc_list = []
                for tc in tool_calls:
                    tc_list.append({
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    })
                assistant_msg["tool_calls"] = tc_list
                messages.append(assistant_msg)

                # Execute native tool calls
                for tc in tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    if REQUIRE_CONFIRMATION and name in DANGEROUS_TOOLS:
                        if not request_confirmation(name, args, task_id):
                            messages.append({"role": "tool", "tool_call_id": tc.id,
                                             "content": f"User denied execution of {name}."})
                            log_event("tool_denied", task_id, tool_name=name, detail={"args": args})
                            continue
                    log_event("tool_call_start", task_id, tool_name=name, detail={"args": args})
                    tres = execute_tool(name, args, task_id)
                    log_event("tool_call_end", task_id, tool_name=name)
                    output = tres.get("output", "") or tres.get("error", "")
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})

            else:
                # --- Prompt-based tool path (models without native tools) ---
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.3,
                )
                choice = response.choices[0]
                text = choice.message.content or ""

                if text:
                    log_event("model_response", task_id,
                              detail={"text": text[:2000], "finish": choice.finish_reason, "mode": "prompt_tools"})

                # Parse tool blocks from the response
                parsed = parse_prompt_tools(text)

                if not parsed:
                    # No tools found â€” model is done
                    clean_text = strip_tool_blocks(text)
                    result = {
                        "task_id": task_id, "status": "complete",
                        "response": clean_text, "model": model,
                        "usage": {
                            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                            "output_tokens": response.usage.completion_tokens if response.usage else 0,
                        },
                    }
                    log_event("task_complete", task_id, detail=result)
                    write_result(task_id, result)
                    return

                # Append the model's full response (with tool blocks) as assistant message
                messages.append({"role": "assistant", "content": text})

                # Execute each parsed tool
                tool_outputs = []
                for tool_name, args, raw_block in parsed:
                    if REQUIRE_CONFIRMATION and tool_name in DANGEROUS_TOOLS:
                        if not request_confirmation(tool_name, args, task_id):
                            tool_outputs.append(f"[DENIED] {tool_name}: user rejected execution.")
                            log_event("tool_denied", task_id, tool_name=tool_name, detail={"args": args})
                            continue

                    log_event("tool_call_start", task_id, tool_name=tool_name,
                              detail={"args": args, "mode": "prompt_tools"})
                    tres = execute_tool(tool_name, args, task_id)
                    log_event("tool_call_end", task_id, tool_name=tool_name)
                    output = tres.get("output", "") or tres.get("error", "")
                    tool_outputs.append(f"[{tool_name} result]\n{output}")

                # Feed tool results back as a user message (prompt-based convention)
                if tool_outputs:
                    feedback = "Tool execution results:\n\n" + "\n\n".join(tool_outputs)
                    feedback += "\n\nContinue with your response, or use another tool if needed."
                    messages.append({"role": "user", "content": feedback})

        # Exhausted tool rounds
        result = {
            "task_id": task_id,
            "status": "error",
            "error": "Exceeded maximum tool-calling rounds (30)",
        }
        write_result(task_id, result)

    except Exception:
        error_msg = traceback.format_exc()
        log_event("task_error", task_id, detail={"error": error_msg[:2000]})
        result = {
            "task_id": task_id,
            "status": "error",
            "error": str(sys.exc_info()[1]),
        }
        write_result(task_id, result)


# â”€â”€ Main loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    try:
        for d in [INBOX, OUTBOX, PROCESSED]:
            d.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"FATAL: Cannot create workspace directories: {e}", file=sys.stderr)
        print("Check that the host mount is owned by UID 1000:", file=sys.stderr)
        print(f"  sudo chown -R 1000:1000 <project-dir>", file=sys.stderr)
        sys.exit(1)

    # Wait for Ollama to be reachable
    client = OpenAI(base_url=OLLAMA_HOST, api_key="ollama")
    print(f"Connecting to Ollama at {OLLAMA_HOST}...")
    for i in range(30):
        try:
            models = client.models.list()
            model_ids = [m.id for m in models]
            print(f"  Available models: {', '.join(model_ids[:10])}")
            if MODEL in model_ids:
                print(f"  Using: {MODEL}")
            elif any(MODEL in m for m in model_ids):
                print(f"  Warning: '{MODEL}' not found â€” will attempt anyway")
            else:
                print(f"  Warning: '{MODEL}' not pulled â€” run: ollama pull {MODEL}")
            break
        except Exception as e:
            if i == 29:
                print(f"FATAL: Cannot reach Ollama after 30 attempts: {e}", file=sys.stderr)
                sys.exit(1)
            time.sleep(2)

    load_plugins()

    # Register SSDLC tools if module available
    try:
        from ssdlc import get_progress, check_item, add_risk, PHASES
        def ssdlc_status(args):
            project = args.get("project", "default")
            return get_progress(project)

        def ssdlc_check(args):
            project = args.get("project", "default")
            phase = args.get("phase", "")
            item_id = args.get("item_id", "")
            checked = args.get("checked", True)
            notes = args.get("notes", "")
            return check_item(project, phase, item_id, checked, notes)

        def ssdlc_risk(args):
            project = args.get("project", "default")
            phase = args.get("phase", "")
            title = args.get("title", "")
            description = args.get("description", "")
            likelihood = args.get("likelihood", 3)
            impact = args.get("impact", 3)
            stride_category = args.get("stride_category", "")
            mitigation = args.get("mitigation", "")
            return add_risk(project, phase, title, description, likelihood, impact, stride_category, mitigation)

        PLUGIN_TOOLS["ssdlc_status"] = {
            "spec": {
                "type": "function",
                "function": {
                    "name": "ssdlc_status",
                    "description": "Get SSDLC progress for a project. Shows all 6 phases, checklist completion, risks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string", "description": "Project name (default: 'default')"},
                        },
                    },
                },
            },
            "handler": ssdlc_status,
        }
        PLUGIN_TOOLS["ssdlc_check"] = {
            "spec": {
                "type": "function",
                "function": {
                    "name": "ssdlc_check",
                    "description": "Mark an SSDLC checklist item as checked/unchecked.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string", "description": "Project name"},
                            "phase": {"type": "string", "description": "Phase key: planning, analysis, design, implementation, maintenance, retirement"},
                            "item_id": {"type": "string", "description": "Checklist item ID, e.g. P1, A3, D2"},
                            "checked": {"type": "boolean", "description": "True to check, False to uncheck"},
                            "notes": {"type": "string", "description": "Optional notes about this item"},
                        },
                        "required": ["project", "phase", "item_id"],
                    },
                },
            },
            "handler": ssdlc_check,
        }
        PLUGIN_TOOLS["ssdlc_risk"] = {
            "spec": {
                "type": "function",
                "function": {
                    "name": "ssdlc_risk",
                    "description": "Add a security risk finding to an SSDLC phase.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string", "description": "Project name"},
                            "phase": {"type": "string", "description": "Phase key"},
                            "title": {"type": "string", "description": "Risk title"},
                            "description": {"type": "string", "description": "Risk description"},
                            "likelihood": {"type": "integer", "description": "Likelihood 1-5"},
                            "impact": {"type": "integer", "description": "Impact 1-5"},
                            "stride_category": {"type": "string", "description": "STRIDE category: spoofing, tampering, repudiation, information_disclosure, denial_of_service, elevation_of_privilege"},
                            "mitigation": {"type": "string", "description": "Proposed mitigation"},
                        },
                        "required": ["project", "phase", "title"],
                    },
                },
            },
            "handler": ssdlc_risk,
        }
        print(f"  [ssdlc] registered 3 SSDLC tools", file=sys.stderr)
    except ImportError:
        pass

    log_event("daemon_start", detail={
        "model": MODEL,
        "ollama_host": OLLAMA_HOST,
        "allow_shell": ALLOW_SHELL,
        "require_confirmation": REQUIRE_CONFIRMATION,
        "plugin_tools": list(PLUGIN_TOOLS.keys()),
    })
    log_event("daemon_ready")

    # Poll for incoming tasks
    while not _shutdown_requested:
        try:
            tasks = sorted(INBOX.glob("*.json"))
            for task_path in tasks:
                if task_path.name.endswith(".approved.json"):
                    continue

                try:
                    task = json.loads(task_path.read_text())
                except json.JSONDecodeError:
                    log_event("error", detail=f"Invalid JSON in {task_path.name}")
                    task_path.rename(PROCESSED / task_path.name)
                    continue

                if "id" not in task or "prompt" not in task:
                    log_event("error", detail=f"Missing id/prompt in {task_path.name}")
                    task_path.rename(PROCESSED / task_path.name)
                    continue

                process_task(client, task)
                task_path.rename(PROCESSED / task_path.name)

                # Check shutdown between tasks
                if _shutdown_requested:
                    break

        except Exception:
            log_event("error", detail=f"Main loop error: {traceback.format_exc()[:2000]}")

        time.sleep(1)

    log_event("daemon_stop", detail="Graceful shutdown completed")
    print("[INFO] Agent stopped gracefully", file=sys.stderr)


if __name__ == "__main__":
    main()
