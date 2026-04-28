from __future__ import annotations

import json
import os
import signal
import struct
import subprocess
import sys
from pathlib import Path


HOST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = HOST_DIR.parent
RUN_SCRIPT = PROJECT_ROOT / "run_macro.ps1"
CONFIG_PATH = PROJECT_ROOT / "config.ini"
LOG_PATH = PROJECT_ROOT / "macro.log"
PID_PATH = PROJECT_ROOT / "macro.pid"


def read_message() -> dict | None:
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack("<I", raw_length)[0]
    raw_message = sys.stdin.buffer.read(message_length)
    return json.loads(raw_message.decode("utf-8"))


def send_message(message: dict) -> None:
    encoded = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def append_log(message: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(message.rstrip() + "\n")


def is_process_running(pid: int) -> bool:
    try:
        handle = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return str(pid) in handle.stdout
    except Exception:
        return False


def taskkill_pid(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def stop_matching_processes() -> int:
    script = (
        "$root = [regex]::Escape('" + str(PROJECT_ROOT).replace("'", "''") + "');"
        "$matches = Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -and ($_.CommandLine -match $root) -and "
        "($_.CommandLine -match 'run_macro.ps1|korail_cancel_macro.main') "
        "};"
        "$count = 0;"
        "foreach ($p in $matches) { "
        "try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; $count++ } catch {} "
        "};"
        "Write-Output $count"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        return int((result.stdout or "0").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0


def get_running_pid() -> int | None:
    if not PID_PATH.exists():
        return None
    try:
        pid = int(PID_PATH.read_text(encoding="ascii").strip())
    except ValueError:
        PID_PATH.unlink(missing_ok=True)
        return None
    if not is_process_running(pid):
        PID_PATH.unlink(missing_ok=True)
        return None
    return pid


def run_macro() -> None:
    running_pid = get_running_pid()
    if running_pid is not None:
        raise RuntimeError(f"Macro is already running. PID={running_pid}")

    LOG_PATH.write_text("\ufeff", encoding="utf-8")
    log_file = LOG_PATH.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-OutputFormat",
            "Text",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_SCRIPT),
            "-NonInteractive",
        ],
        cwd=str(PROJECT_ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    PID_PATH.write_text(str(process.pid), encoding="ascii")
    append_log(f"Macro started. PID={process.pid}")


def stop_macro() -> bool:
    pid = get_running_pid()
    stopped = False
    if pid is None:
        count = stop_matching_processes()
        if count:
            append_log(f"Macro stopped. matched_processes={count}")
            stopped = True
        else:
            append_log("Macro is not running.")
        return stopped

    taskkill_pid(pid)
    PID_PATH.unlink(missing_ok=True)
    append_log(f"Macro stopped. PID={pid}")
    count = stop_matching_processes()
    if count:
        append_log(f"Additional matching processes stopped: {count}")
    return True


def main() -> int:
    message = read_message()
    if message is None:
        return 0

    if message.get("action") == "saveConfig":
        config_ini = message.get("configIni")
        if not config_ini:
            send_message({"ok": False, "error": "configIni is empty"})
            return 0
        CONFIG_PATH.write_text(config_ini, encoding="utf-8")
        send_message({"ok": True})
        return 0

    if message.get("action") == "readLog":
        if LOG_PATH.exists():
            text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
            send_message({"ok": True, "log": text[-20000:]})
        else:
            send_message({"ok": True, "log": ""})
        return 0

    if message.get("action") == "clearLog":
        LOG_PATH.write_text("", encoding="utf-8")
        send_message({"ok": True})
        return 0

    if message.get("action") == "stop":
        stopped = stop_macro()
        send_message({"ok": True, "stopped": stopped})
        return 0

    if message.get("action") != "run":
        send_message({"ok": False, "error": "Unknown action"})
        return 0

    try:
        run_macro()
    except Exception as exc:
        send_message({"ok": False, "error": str(exc)})
    else:
        send_message({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
