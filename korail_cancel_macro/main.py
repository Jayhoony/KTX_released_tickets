from __future__ import annotations

import argparse
import configparser
import getpass
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from korail2 import (
    AdultPassenger,
    ChildPassenger,
    Korail,
    KorailError,
    NoResultsError,
    ReserveOption,
    SeniorPassenger,
    SoldOutError,
    ToddlerPassenger,
    TrainType,
)

from .credential_storage import CredentialStorage
from .payment import KorailPaymentError, pay_reservation_with_card


TRAIN_TYPES = {
    "ALL": TrainType.ALL,
    "KTX": TrainType.KTX,
    "KTX_SANCHEON": TrainType.KTX_SANCHEON,
    "SAEMAEUL": TrainType.SAEMAEUL,
    "ITX_SAEMAEUL": TrainType.ITX_SAEMAEUL,
    "MUGUNGHWA": TrainType.MUGUNGHWA,
    "NURIRO": TrainType.NURIRO,
    "ITX_CHEONGCHUN": TrainType.ITX_CHEONGCHUN,
    "AIRPORT": TrainType.AIRPORT,
}

RESERVE_OPTIONS = {
    "GENERAL_FIRST": ReserveOption.GENERAL_FIRST,
    "GENERAL_ONLY": ReserveOption.GENERAL_ONLY,
    "SPECIAL_FIRST": ReserveOption.SPECIAL_FIRST,
    "SPECIAL_ONLY": ReserveOption.SPECIAL_ONLY,
}


@dataclass(frozen=True)
class AccountConfig:
    korail_id: str
    korail_pw: str


@dataclass(frozen=True)
class TripConfig:
    dep: str
    arr: str
    date: str
    time: str
    train_type: str
    train_numbers: tuple[str, ...]
    earliest_time: str
    latest_time: str


@dataclass(frozen=True)
class PassengerConfig:
    adults: int
    children: int
    toddlers: int
    seniors: int


@dataclass(frozen=True)
class MacroConfig:
    interval_seconds: float
    jitter_seconds: float
    max_attempts: int
    login_max_attempts: int
    reserve_when_found: bool
    reserve_option: str
    try_waiting: bool
    include_waiting_list: bool
    auto_payment: bool


@dataclass(frozen=True)
class NotificationConfig:
    beep: bool


@dataclass(frozen=True)
class AppConfig:
    account: AccountConfig
    trip: TripConfig
    passengers: PassengerConfig
    macro: MacroConfig
    notification: NotificationConfig


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def require_section(parser: configparser.ConfigParser, section: str) -> configparser.SectionProxy:
    if section not in parser:
        raise KeyError(f"설정 파일에 [{section}] 섹션이 없습니다.")
    return parser[section]


def env_or_config(section: configparser.SectionProxy, key: str, env_name: str) -> str:
    return os.environ.get(env_name, section.get(key, "")).strip()


def load_config(path: Path) -> AppConfig:
    parser = configparser.ConfigParser()
    read_files = parser.read(path, encoding="utf-8")
    if not read_files:
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {path}")

    account = require_section(parser, "account")
    trip = require_section(parser, "trip")
    passengers = require_section(parser, "passengers")
    macro = require_section(parser, "macro")
    notification = require_section(parser, "notification")

    train_type = trip.get("train_type", "KTX").strip().upper()
    reserve_option = macro.get("reserve_option", "GENERAL_ONLY").strip().upper()
    if train_type not in TRAIN_TYPES:
        raise ValueError(f"지원하지 않는 train_type입니다: {train_type}")
    if reserve_option not in RESERVE_OPTIONS:
        raise ValueError(f"지원하지 않는 reserve_option입니다: {reserve_option}")

    return AppConfig(
        account=AccountConfig(
            korail_id=env_or_config(account, "id", "KORAIL_ID"),
            korail_pw=env_or_config(account, "password", "KORAIL_PASSWORD"),
        ),
        trip=TripConfig(
            dep=trip.get("dep", "").strip(),
            arr=trip.get("arr", "").strip(),
            date=trip.get("date", "").strip(),
            time=trip.get("time", "000000").strip(),
            train_type=train_type,
            train_numbers=parse_csv(trip.get("train_numbers", "")),
            earliest_time=trip.get("earliest_time", "").strip(),
            latest_time=trip.get("latest_time", "").strip(),
        ),
        passengers=PassengerConfig(
            adults=passengers.getint("adults", 1),
            children=passengers.getint("children", 0),
            toddlers=passengers.getint("toddlers", 0),
            seniors=passengers.getint("seniors", 0),
        ),
        macro=MacroConfig(
            interval_seconds=macro.getfloat("interval_seconds", 12),
            jitter_seconds=macro.getfloat("jitter_seconds", 3),
            max_attempts=macro.getint("max_attempts", 0),
            login_max_attempts=macro.getint("login_max_attempts", 3),
            reserve_when_found=parse_bool(macro.get("reserve_when_found", "true")),
            reserve_option=reserve_option,
            try_waiting=parse_bool(macro.get("try_waiting", "false")),
            include_waiting_list=parse_bool(macro.get("include_waiting_list", "false")),
            auto_payment=parse_bool(macro.get("auto_payment", "false")),
        ),
        notification=NotificationConfig(
            beep=parse_bool(notification.get("beep", "true")),
        ),
    )


def validate_config(config: AppConfig) -> None:
    missing = []
    if not config.trip.dep:
        missing.append("trip.dep")
    if not config.trip.arr:
        missing.append("trip.arr")
    if not config.trip.date:
        missing.append("trip.date")
    if not config.trip.time:
        missing.append("trip.time")
    if missing:
        raise ValueError("필수 설정이 비었습니다: " + ", ".join(missing))

    total_passengers = (
        config.passengers.adults
        + config.passengers.children
        + config.passengers.toddlers
        + config.passengers.seniors
    )
    if total_passengers <= 0:
        raise ValueError("승객 수는 최소 1명이어야 합니다.")


def ask_credentials(config: AppConfig, *, force_prompt: bool = False) -> AppConfig:
    noninteractive = parse_bool(os.environ.get("KORAIL_NONINTERACTIVE", "false"))

    if not force_prompt and (not config.account.korail_id or not config.account.korail_pw):
        saved_login = CredentialStorage.load_login()
        if saved_login:
            config = AppConfig(
                account=AccountConfig(
                    korail_id=config.account.korail_id or saved_login.username,
                    korail_pw=config.account.korail_pw or saved_login.password,
                ),
                trip=config.trip,
                passengers=config.passengers,
                macro=config.macro,
                notification=config.notification,
            )

    if noninteractive and (force_prompt or not config.account.korail_id or not config.account.korail_pw):
        raise ValueError("GUI 실행에서는 코레일 ID와 비밀번호를 입력해야 합니다.")

    if force_prompt:
        korail_id = input("코레일 ID/회원번호/전화번호/이메일: ").strip()
        korail_pw = masked_password_input("코레일 비밀번호: ")
    else:
        korail_id = config.account.korail_id or input("코레일 ID/회원번호/전화번호/이메일: ").strip()
        korail_pw = config.account.korail_pw or masked_password_input("코레일 비밀번호: ")

    return AppConfig(
        account=AccountConfig(korail_id=korail_id, korail_pw=korail_pw),
        trip=config.trip,
        passengers=config.passengers,
        macro=config.macro,
        notification=config.notification,
    )


def masked_password_input(prompt: str) -> str:
    try:
        import msvcrt
    except ImportError:
        return getpass.getpass(prompt)

    print(prompt, end="", flush=True)
    chars: list[str] = []
    while True:
        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            print()
            return "".join(chars)
        if key == "\003":
            raise KeyboardInterrupt
        if key == "\b":
            if chars:
                chars.pop()
                print("\b \b", end="", flush=True)
            continue
        if key in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue

        chars.append(key)
        print("*", end="", flush=True)


def build_passengers(config: PassengerConfig):
    passengers = []
    if config.adults:
        passengers.append(AdultPassenger(config.adults))
    if config.children:
        passengers.append(ChildPassenger(config.children))
    if config.toddlers:
        passengers.append(ToddlerPassenger(config.toddlers))
    if config.seniors:
        passengers.append(SeniorPassenger(config.seniors))
    return passengers


def format_time(hhmmss: str) -> str:
    if len(hhmmss) < 4:
        return hhmmss
    return f"{hhmmss[:2]}:{hhmmss[2:4]}"


def train_summary(train) -> str:
    seat_state = []
    if train.has_general_seat():
        seat_state.append("일반실")
    if train.has_special_seat():
        seat_state.append("특실")
    if train.has_waiting_list():
        seat_state.append("예약대기")
    seats = ", ".join(seat_state) if seat_state else "매진"
    return (
        f"{train.train_type_name} {train.train_no} "
        f"{train.dep_name}->{train.arr_name} "
        f"{format_time(train.dep_time)}~{format_time(train.arr_time)} "
        f"({seats})"
    )


def matches_train_filter(train, config: TripConfig) -> bool:
    if config.train_numbers and train.train_no not in config.train_numbers:
        return False
    if config.earliest_time and train.dep_time < config.earliest_time:
        return False
    if config.latest_time and train.dep_time > config.latest_time:
        return False
    return True


def choose_candidate(trains, trip: TripConfig, include_waiting: bool):
    for train in trains:
        if not matches_train_filter(train, trip):
            continue
        if train.has_seat() or (include_waiting and train.has_waiting_list()):
            return train
    return None


def notify(config: NotificationConfig) -> None:
    if not config.beep:
        return
    try:
        import winsound

        winsound.Beep(880, 350)
        winsound.Beep(1175, 450)
    except Exception:
        print("\a", end="", flush=True)


def sleep_between_attempts(config: MacroConfig) -> None:
    jitter = random.uniform(0, config.jitter_seconds) if config.jitter_seconds > 0 else 0
    time.sleep(config.interval_seconds + jitter)


def run(config: AppConfig) -> int:
    validate_config(config)
    config = ask_credentials(config)
    passengers = build_passengers(config.passengers)

    korail = None
    for login_attempt in range(1, config.macro.login_max_attempts + 1):
        print(f"코레일 로그인을 시도합니다... ({login_attempt}/{config.macro.login_max_attempts})")
        korail = Korail(config.account.korail_id, config.account.korail_pw, auto_login=False)
        if korail.login():
            break

        print("로그인에 실패했습니다. ID/비밀번호를 다시 입력하세요.", file=sys.stderr)
        if login_attempt >= config.macro.login_max_attempts:
            return 1
        config = ask_credentials(config, force_prompt=True)

    if korail is None:
        return 1

    print(f"로그인 성공: {korail.name or korail.membership_number}")
    print(
        "조회 조건: "
        f"{config.trip.dep}->{config.trip.arr}, "
        f"{config.trip.date} {format_time(config.trip.time)}, "
        f"{config.trip.train_type}"
    )

    attempt = 0
    while True:
        attempt += 1
        print(f"\n[{attempt}] 취소표를 조회합니다...")
        try:
            trains = korail.search_train(
                config.trip.dep,
                config.trip.arr,
                config.trip.date,
                config.trip.time,
                train_type=TRAIN_TYPES[config.trip.train_type],
                passengers=passengers,
                include_no_seats=True,
                include_waiting_list=config.macro.include_waiting_list,
            )
        except NoResultsError:
            trains = []
            print("조회 결과가 없습니다.")
        except KorailError as exc:
            print(f"코레일 API 오류: {exc}")
            sleep_between_attempts(config.macro)
            continue

        for train in trains:
            if matches_train_filter(train, config.trip):
                print(" - " + train_summary(train))

        candidate = choose_candidate(
            trains,
            config.trip,
            include_waiting=config.macro.include_waiting_list and config.macro.try_waiting,
        )
        if candidate is not None:
            print(f"\n예약 후보 발견: {train_summary(candidate)}")
            notify(config.notification)
            if not config.macro.reserve_when_found:
                print("reserve_when_found=false 이므로 예약하지 않고 종료합니다.")
                return 0

            try:
                reservation = korail.reserve(
                    candidate,
                    passengers=passengers,
                    option=RESERVE_OPTIONS[config.macro.reserve_option],
                    try_waiting=config.macro.try_waiting,
                )
            except SoldOutError:
                print("예약 시점에 이미 매진되었습니다. 다시 조회합니다.")
            except KorailError as exc:
                print(f"예약 실패: {exc}")
            else:
                notify(config.notification)
                print("\n예약 성공:")
                print(reservation)
                payment = CredentialStorage.load_payment()
                if config.macro.auto_payment:
                    if payment is None:
                        print("자동결제가 켜져 있지만 저장된 결제정보가 없습니다.")
                        print("구매기한 안에 코레일 앱 또는 웹에서 직접 결제하세요.")
                    else:
                        print("저장된 결제정보로 자동결제를 시도합니다...")
                        try:
                            if pay_reservation_with_card(korail, reservation, payment):
                                print("자동결제 성공. 코레일 앱 또는 웹에서 발권 내역을 확인하세요.")
                        except KorailPaymentError as exc:
                            print(f"자동결제 실패: {exc}")
                            print("구매기한 안에 코레일 앱 또는 웹에서 직접 결제하세요.")
                elif payment:
                    print("저장된 결제정보가 있습니다. 자동결제 옵션이 꺼져 있어 결제하지 않았습니다.")
                    print("결제/발권은 코레일 앱 또는 웹에서 구매기한 안에 직접 진행하세요.")
                else:
                    print("결제/발권은 코레일 앱 또는 웹에서 구매기한 안에 직접 진행하세요.")
                return 0

        if config.macro.max_attempts and attempt >= config.macro.max_attempts:
            print("최대 시도 횟수에 도달했습니다.")
            return 2

        sleep_between_attempts(config.macro)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Korail cancel ticket reservation macro")
    parser.add_argument(
        "--config",
        default="config.ini",
        help="설정 파일 경로입니다. 기본값: config.ini",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config))
        return run(config)
    except KeyboardInterrupt:
        print("\n사용자가 중지했습니다.")
        return 130
    except Exception as exc:
        print(f"실행 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
