"""Exercise real upstream tools through a local synthetic OpenAI-compatible API.

The model is synthetic; OpenCode, its file tools and its shell execution are real.
No implementation of those tools is duplicated here.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    entry = parser.add_mutually_exclusive_group(required=True)
    entry.add_argument("--binary", type=Path)
    entry.add_argument("--launcher", type=Path)
    parser.add_argument("--resume-last", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    binary = (args.launcher or args.binary).resolve()
    audit: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="pocketagent-test-") as temporary:
        profile = Path(temporary)
        project = (binary.parent / "workspaces/验证 项目") if args.launcher else (profile / "验证 项目")
        project.mkdir(parents=True, exist_ok=True)
        old, new = ("beta", "gamma") if args.resume_last else ("alpha", "beta")
        if args.resume_last:
            assert (project / "input.txt").read_text(encoding="utf-8") == old + "\n", "Project data did not survive relocation"
        else:
            (project / "input.txt").write_text(old + "\n", encoding="utf-8")
        marker = project / "executed.txt"
        marker.unlink(missing_ok=True)
        (project / "verify.cjs").write_text(
            "const fs=require('node:fs');const cp=require('node:child_process');\n"
            f"if(fs.readFileSync('input.txt','utf8').trim()!=={json.dumps(new)})process.exit(21);\n"
            "const p=cp.spawnSync('python',['-c','print(6*7)'],{encoding:'utf8'});\n"
            "if(p.status!==0||p.stdout.trim()!=='42')process.exit(22);\n"
            "fs.writeFileSync('executed.txt','node-and-python-ok');console.log('POCKETAGENT_TOOLCHAIN_OK');\n",
            encoding="utf-8",
        )

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_: object) -> None:
                pass

            def do_POST(self) -> None:
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                available = [tool.get("function", {}).get("name", "") for tool in request.get("tools", [])]
                message: dict = {"role": "assistant", "content": "PocketAgent integration test"}
                finish = "stop"
                if available:
                    messages = request.get("messages", [])
                    latest = max((i for i, item in enumerate(messages) if item.get("role") == "user"), default=-1)
                    step = sum(item.get("role") == "tool" for item in messages[latest + 1:])
                    if step == 0:
                        name, arguments = "read", {"filePath": str(project / "input.txt")}
                    elif step == 1:
                        if "edit" in available:
                            name, arguments = "edit", {"filePath": str(project / "input.txt"), "oldString": old, "newString": new}
                        else:
                            name, arguments = "apply_patch", {"patchText": f"*** Begin Patch\n*** Update File: {project / 'input.txt'}\n@@\n-{old}\n+{new}\n*** End Patch"}
                    elif step == 2:
                        name = "bash" if "bash" in available else "shell"
                        arguments = {"command": "node verify.cjs", "description": "Verify edited file with bundled Node and Python"}
                    else:
                        name, arguments = "", {}
                    if name:
                        if name not in available:
                            audit.append({"error": "Expected upstream tool missing", "tool": name, "available": available})
                            self.send_error(500, "Expected upstream tool missing")
                            return
                        audit.append({"tool": name, "step": step})
                        message = {"role": "assistant", "content": None, "tool_calls": [{
                            "id": f"portable_{step}_{len(audit)}", "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }]}
                        finish = "tool_calls"
                    else:
                        message = {"role": "assistant", "content": "POCKETAGENT_ROUNDTRIP_COMPLETE"}

                base = {"id": "pocketagent-test", "created": int(time.time()), "model": "portable-test"}
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream" if request.get("stream") else "application/json")
                self.end_headers()
                if not request.get("stream"):
                    body = {**base, "object": "chat.completion", "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}}
                    self.wfile.write(json.dumps(body).encode())
                    return
                delta = {"role": "assistant"}
                if message.get("tool_calls"):
                    delta["tool_calls"] = [{"index": 0, **message["tool_calls"][0]}]
                else:
                    delta["content"] = message["content"]
                for data in [
                    {**base, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                    {**base, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
                     "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}},
                ]:
                    self.wfile.write(("data: " + json.dumps(data) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        config = profile / "model.json"
        config.write_text(json.dumps({
            "autoupdate": False,
            "model": "pocket-test/portable-test",
            "small_model": "pocket-test/portable-test",
            "permission": {"*": "allow"},
            "provider": {"pocket-test": {
                "npm": "@ai-sdk/openai-compatible", "name": "Local integration fixture",
                "options": {"baseURL": f"http://127.0.0.1:{server.server_port}/v1", "apiKey": "synthetic-test-key"},
                "models": {"portable-test": {"name": "Synthetic test model", "limit": {"context": 128000, "output": 8192}}},
            }},
        }), encoding="utf-8")
        env = os.environ.copy()
        env.update({
            "OPENCODE_CONFIG": str(config), "OPENCODE_DISABLE_MODELS_FETCH": "1",
            "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_EXPERIMENTAL_DISABLE_FILEWATCHER": "1",
            "PWD": str(project),
        })
        if not args.launcher:
            for key, name in [("XDG_DATA_HOME", "share"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state")]:
                env[key] = str(profile / name)
        command = [str(binary)]
        if args.launcher:
            command += ["--project", str(project)]
        run = ["run", "--format", "json", "--model", "pocket-test/portable-test", "--title", 'PocketAgent "portable" integration test']
        if args.resume_last:
            run += ["--session", (project / "session-id.txt").read_text(encoding="utf-8").strip()]
        run += [f'Read input.txt, replace "{old}" with "{new}", then run node verify.cjs and report the result.']
        try:
            result = subprocess.run(command + run, cwd=project, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            report = {"platform": os.name, "resumed": args.resume_last, "returncode": result.returncode,
                      "audit": audit, "stdout": result.stdout, "stderr": result.stderr}
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            assert result.returncode == 0, json.dumps(report, ensure_ascii=False)[-18000:]
            assert (project / "input.txt").read_text(encoding="utf-8").strip() == new, json.dumps(report, ensure_ascii=False)[-18000:]
            assert marker.exists() and marker.read_text(encoding="utf-8") == "node-and-python-ok", json.dumps(report, ensure_ascii=False)[-18000:]
            assert len([item for item in audit if "tool" in item]) >= 3, audit
            sessions = subprocess.run(command + ["session", "list", "--format", "json"], cwd=project, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            assert sessions.returncode == 0, sessions.stderr
            entries = json.loads(sessions.stdout)
            found = next(item for item in entries if item.get("title") == 'PocketAgent "portable" integration test')
            (project / "session-id.txt").write_text(found["id"], encoding="utf-8")
            print(json.dumps({"result": "PASS", "real_tools": [item["tool"] for item in audit if "tool" in item],
                              "resumed": args.resume_last, "session_persisted": True}, ensure_ascii=False))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()

