from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path


HOST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = HOST_DIR.parent
RUN_SCRIPT = PROJECT_ROOT / "run_macro.ps1"
CONFIG_PATH = PROJECT_ROOT / "config.ini"
LOG_PATH = PROJECT_ROOT / "macro.log"


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


def run_macro() -> None:
    log_file = LOG_PATH.open("w", encoding="utf-8")
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
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


def main() -> int:
    message = read_message()
    if message is None:
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

    if message.get("action") != "run":
        send_message({"ok": False, "error": "Unknown action"})
        return 0

    try:
        config_ini = message.get("configIni")
        if config_ini:
            CONFIG_PATH.write_text(config_ini, encoding="utf-8")
        run_macro()
    except Exception as exc:
        send_message({"ok": False, "error": str(exc)})
    else:
        send_message({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
