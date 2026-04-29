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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUN_SCRIPT = PROJECT_ROOT / "run_macro.ps1"
CONFIG_PATH = PROJECT_ROOT / "config.ini"
LOG_PATH = PROJECT_ROOT / "macro.log"
PID_PATH = PROJECT_ROOT / "macro.pid"

TRAIN_TYPES = {
    "ALL": "109",
    "KTX": "100",
    "KTX_SANCHEON": "100",
    "SAEMAEUL": "101",
    "ITX_SAEMAEUL": "101",
    "MUGUNGHWA": "102",
    "NURIRO": "102",
    "ITX_CHEONGCHUN": "104",
    "AIRPORT": "105",
}


def credential_storage():
    from korail_cancel_macro.credential_storage import CredentialStorage

    return CredentialStorage


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


def parse_int(value, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def format_hhmm(value: str) -> str:
    value = value or ""
    if len(value) < 4:
        return value
    return f"{value[:2]}:{value[2:4]}"


def build_search_passengers(search: dict):
    from korail2 import AdultPassenger, ChildPassenger, SeniorPassenger, ToddlerPassenger

    passengers = []
    adults = parse_int(search.get("adults"), 1)
    children = parse_int(search.get("children"), 0)
    toddlers = parse_int(search.get("toddlers"), 0)
    seniors = parse_int(search.get("seniors"), 0)
    if adults:
        passengers.append(AdultPassenger(adults))
    if children:
        passengers.append(ChildPassenger(children))
    if toddlers:
        passengers.append(ToddlerPassenger(toddlers))
    if seniors:
        passengers.append(SeniorPassenger(seniors))
    return passengers or [AdultPassenger(1)]


def search_trains(message: dict) -> dict:
    from korail2 import Korail, KorailError, NoResultsError

    CredentialStorage = credential_storage()
    login = message.get("login") or {}
    saved_login = CredentialStorage.load_login()
    username = login.get("username") or (saved_login.username if saved_login else "")
    password = login.get("password") or (saved_login.password if saved_login else "")
    if not username or not password:
        raise RuntimeError("코레일 ID와 비밀번호가 필요합니다.")

    search = message.get("search") or {}
    dep = (search.get("dep") or "").strip()
    arr = (search.get("arr") or "").strip()
    date = (search.get("date") or "").strip()
    time = (search.get("time") or "").strip()
    if not dep or not arr or not date or not time:
        raise RuntimeError("출발, 도착, 날짜, 시간이 필요합니다.")

    korail = Korail(username, password, auto_login=False)
    if not korail.login():
        raise RuntimeError("코레일 로그인에 실패했습니다.")

    try:
        trains = korail.search_train(
            dep,
            arr,
            date,
            time,
            train_type=TRAIN_TYPES.get((search.get("trainType") or "KTX").upper(), "100"),
            passengers=build_search_passengers(search),
            include_no_seats=True,
            include_waiting_list=bool(search.get("includeWaitingList")),
        )
    except NoResultsError:
        trains = []
    except KorailError as exc:
        raise RuntimeError(str(exc)) from exc

    results = []
    for train in trains:
        general = bool(train.has_general_seat())
        special = bool(train.has_special_seat())
        waiting = bool(train.has_waiting_list())
        results.append(
            {
                "trainNo": str(train.train_no),
                "trainTypeName": str(train.train_type_name),
                "depName": str(train.dep_name),
                "arrName": str(train.arr_name),
                "depTime": format_hhmm(train.dep_time),
                "arrTime": format_hhmm(train.arr_time),
                "general": general,
                "special": special,
                "waiting": waiting,
                "available": general or special or waiting,
            }
        )
    return {"ok": True, "trains": results}


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

    if message.get("action") == "saveCredentials":
        try:
            CredentialStorage = credential_storage()
            login = message.get("login") or {}
            payment = message.get("payment") or {}
            email = message.get("email") or {}

            if login.get("save"):
                username = login.get("username", "")
                password = login.get("password", "")
                if username and password:
                    CredentialStorage.save_login(username, password)
            elif login.get("delete"):
                CredentialStorage.delete_login()

            if payment.get("save"):
                CredentialStorage.save_payment(
                    card_number=payment.get("cardNumber", ""),
                    card_password=payment.get("cardPassword", ""),
                    expire=payment.get("expire", ""),
                    validation_number=payment.get("validationNumber", ""),
                    is_corporate=bool(payment.get("isCorporate")),
                )
            elif payment.get("delete"):
                CredentialStorage.delete_payment()

            if email.get("save"):
                password = email.get("password", "")
                if password:
                    CredentialStorage.save_email(password)
            elif email.get("delete"):
                CredentialStorage.delete_email()
        except Exception as exc:
            send_message({"ok": False, "error": str(exc)})
            return 0

        saved_email = None
        try:
            saved_email = CredentialStorage.load_email()
        except Exception:
            saved_email = None
        send_message({"ok": True, "emailSaved": bool(saved_email and saved_email.password)})
        return 0

    if message.get("action") == "loadCredentials":
        try:
            CredentialStorage = credential_storage()
            login = CredentialStorage.load_login()
            payment = CredentialStorage.load_payment()
            email = CredentialStorage.load_email()
        except Exception:
            login = None
            payment = None
            email = None
        send_message(
            {
                "ok": True,
                "login": {
                    "username": login.username,
                    "password": login.password,
                }
                if login
                else None,
                "payment": {
                    "cardNumber": payment.card_number,
                    "cardPassword": payment.card_password,
                    "expire": payment.expire,
                    "validationNumber": payment.validation_number,
                    "isCorporate": payment.is_corporate,
                }
                if payment
                else None,
                "email": {
                    "password": email.password,
                }
                if email
                else None,
            }
        )
        return 0

    if message.get("action") == "searchTrains":
        try:
            send_message(search_trains(message))
        except Exception as exc:
            send_message({"ok": False, "error": str(exc)})
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
