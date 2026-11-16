"""Manage only this project's detached development backend (Linux/WSL)."""

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".tools" / "dev"
STATE = RUNTIME / "backend.json"
LOG = RUNTIME / "backend.log"
COMMAND = [str(ROOT / ".venv/bin/python"), "-m", "uvicorn", "app.main:app",
           "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"]


def process_info(pid):
    proc = Path("/proc") / str(pid)
    try:
        fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        return {
            "cwd": str((proc / "cwd").resolve(strict=True)),
            "args": [part.decode() for part in (proc / "cmdline").read_bytes().split(b"\0") if part],
            "start": fields[19], "state": fields[0],
        }
    except (OSError, ValueError, IndexError):
        return None


def owned(state):
    info = process_info(state.get("pid", 0))
    return bool(info and info["state"] != "Z" and info["cwd"] == str(ROOT)
                and info["args"] == COMMAND and info["start"] == state.get("start"))


def load_state():
    if not STATE.exists():
        return {}
    return json.loads(STATE.read_text())


def start():
    old = load_state()
    if owned(old):
        print(f"Backend already running: PID {old['pid']}, http://127.0.0.1:8000")
        return
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", 8000))
        except OSError:
            raise SystemExit("Port 8000 is occupied; no existing process was stopped.") from None
    if not Path(COMMAND[0]).is_file():
        raise SystemExit("Create the project .venv and install backend requirements first.")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with LOG.open("ab") as output:
        child = subprocess.Popen(COMMAND, cwd=ROOT, stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT,
                                 start_new_session=True, close_fds=True)
    info = process_info(child.pid)
    if not info:
        raise SystemExit("Backend failed to start; inspect .tools/dev/backend.log locally.")
    STATE.write_text(json.dumps({"pid": child.pid, "start": info["start"]}) + "\n")
    STATE.chmod(0o600)
    # Ignore unrelated proxy variables for this strictly local readiness probe.
    opener = build_opener(ProxyHandler({}))
    for _ in range(50):
        if child.poll() is not None:
            break
        try:
            with opener.open("http://127.0.0.1:8000/docs", timeout=0.5) as response:
                if response.status == 200:
                    print(f"Backend started: PID {child.pid}, http://127.0.0.1:8000")
                    print("Log: .tools/dev/backend.log (no global service installed)")
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.1)
    raise SystemExit("Backend not ready; inspect .tools/dev/backend.log and use this script's status/stop.")


def stop():
    state = load_state()
    if not owned(state):
        print("No matching managed backend; no process was stopped.")
        return
    os.kill(state["pid"], signal.SIGTERM)
    for _ in range(50):
        if not owned(state):
            STATE.unlink(missing_ok=True)
            print("Project backend stopped. MySQL was not touched.")
            return
        time.sleep(0.1)
    raise SystemExit("Backend is still shutting down; inspect its local log. No forced kill sent.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status"])
    action = parser.parse_args().action
    if action == "start":
        start()
    elif action == "stop":
        stop()
    else:
        state = load_state()
        print(f"Running: PID {state['pid']}" if owned(state) else "No matching managed backend running.")
