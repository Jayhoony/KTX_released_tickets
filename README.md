# Korail Cancel Ticket Macro

`korail2` API를 이용해 코레일 취소표를 반복 조회하고, 좌석이 생기면 예약을 시도하는 Python 매크로입니다. Chrome 확장 팝업에서 설정을 바꾸고 실행 로그를 확인할 수 있습니다.

참고 API: [dhfhfk/korail2 bypassDynapath](https://github.com/dhfhfk/korail2/tree/bypassDynapath)

## 면책사항

이 프로젝트는 교육 및 개인 학습 목적의 예제입니다. 코레일 또는 관련 서비스의 공식 도구가 아니며, 사용자는 코레일 이용약관과 관련 법령을 직접 확인하고 준수해야 합니다.

- 상업적 목적, 재판매, 대량 예약, 부정 예약, 서비스 방해 목적의 사용을 금지합니다.
- 과도한 반복 조회는 계정 제한, 접속 차단, 예약 취소 등 불이익으로 이어질 수 있습니다.
- 이 도구 사용으로 발생하는 계정 제한, 결제 문제, 예약 실패, 약관 위반, 법적 책임은 사용자 본인에게 있습니다.
- 캡차, 본인인증, 결제 인증 등 보안 절차를 우회하지 않습니다.
- 예약 성공 후 결제와 발권은 사용자가 직접 확인하고 진행해야 합니다.

## 결제정보 저장 방식

참고한 `winwx/ktx-srt-macro` 프로젝트처럼 민감정보는 `keyring`을 통해 운영체제 자격 증명 저장소에 저장합니다. Windows에서는 Windows Credential Manager에 저장되며, `config.ini`에는 카드번호나 카드 비밀번호를 쓰지 않습니다.

Chrome 팝업에서 `예약 성공 시 자동결제`를 켜면 예약 성공 직후 저장된 카드정보로 결제를 시도합니다. 이 옵션은 실제 결제가 발생할 수 있으므로 본인 카드와 본인 계정에서만 사용하세요. 옵션을 끄면 예약만 진행하고 결제/발권은 코레일 앱 또는 웹에서 직접 진행합니다.

## 설치

Python 3.11 이상을 설치한 뒤 프로젝트 루트에서 실행하세요.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Git이 없어도 설치되도록 `requirements.txt`는 GitHub zip 주소를 사용합니다.

## 설정 파일

```powershell
Copy-Item config.example.ini config.ini
notepad config.ini
```

`config.ini`는 개인 설정 파일입니다. 배포하거나 커밋하지 마세요.

주요 설정:

- `dep`, `arr`: 역 이름을 한글로 입력합니다. 예: `서울`, `부산`
- `date`: `yyyyMMdd`
- `time`: `hhmmss`
- `train_type`: `KTX`, `ALL`, `ITX_SAEMAEUL`, `MUGUNGHWA` 등
- `train_numbers`: 특정 열차번호만 예약하려면 쉼표로 입력합니다.
- `reserve_option`: `GENERAL_ONLY`, `GENERAL_FIRST`, `SPECIAL_ONLY`, `SPECIAL_FIRST`
- `interval_seconds = 1`, `jitter_seconds = 3`: 1~4초 사이 랜덤 간격으로 다시 조회합니다.
- `auto_payment`: `true`이면 예약 성공 직후 저장된 결제정보로 자동결제를 시도합니다.

## 실행

```powershell
python -m korail_cancel_macro.main --config config.ini
```

비밀번호를 터미널에서 입력하면 `*`로 표시됩니다. Chrome GUI의 보안 저장을 켜면 로그인 정보는 Windows 자격 증명 저장소에서 불러옵니다.

## Chrome 확장 GUI

1. Chrome 주소창에 `chrome://extensions`를 입력합니다.
2. 오른쪽 위 `개발자 모드`를 켭니다.
3. `압축해제된 확장 프로그램을 로드합니다`를 누릅니다.
4. 이 프로젝트의 `chrome_extension` 폴더를 선택합니다.

팝업에서 출발/도착, 날짜, 시간, 승객, 반복 간격, 로그인, 결제정보를 입력할 수 있습니다. `열차 조회`를 누르면 현재 날짜/시간 조건으로 열차 목록을 불러오고, 체크한 열차번호만 `train_numbers`에 반영됩니다. `설정 저장`은 `config.ini` 저장과 보안 저장소 저장을 한 번에 처리합니다. 자동결제를 쓰려면 `결제정보 보안 저장`과 `예약 성공 시 자동결제`를 함께 켜야 합니다.

## Native Host 등록

확장 팝업에서 `실행`, `멈춤`, 로그 표시를 쓰려면 Native Messaging host를 등록해야 합니다.

프로젝트 루트에서 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_native_host.ps1 -ExtensionId "복사한_확장_ID"
```

만약 현재 위치가 `C:\Windows\system32`라면 먼저 이동하거나 전체 경로를 쓰세요.

```powershell
cd C:\Users\사용자명\Documents\GitHub\KTX_released_tickets
powershell -ExecutionPolicy Bypass -File .\install_native_host.ps1 -ExtensionId "복사한_확장_ID"
```

또는:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\사용자명\Documents\GitHub\KTX_released_tickets\install_native_host.ps1" -ExtensionId "복사한_확장_ID"
```

등록 후 Chrome 확장 관리 화면에서 확장을 새로고침하고 팝업을 다시 열어 실행하세요.

## 문제 해결

이전 백그라운드 실행을 모두 정리하려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_all_macro.ps1
```

한글 로그가 깨져 보이면 팝업에서 로그를 지우고 다시 실행하세요. 새 실행은 UTF-8 로그로 기록됩니다.

## 배포 전 체크리스트

배포 전에 아래 파일과 폴더가 포함되지 않도록 확인하세요.

- `.venv/`
- `config.ini`
- `macro.log`
- `macro.pid`
- `native_host/com.ktx_released_tickets.macro.json`
- `__pycache__/`
