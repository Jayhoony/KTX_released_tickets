# Korail Cancel Ticket Macro

`korail2` API를 이용해 코레일 취소표를 반복 조회하고, 좌석이 생기면 예약을 시도하는 파이썬 매크로입니다. 크롬 확장 팝업으로 설정을 바꾸고 실행 로그를 확인할 수 있습니다.

참고 API: [dhfhfk/korail2 bypassDynapath](https://github.com/dhfhfk/korail2/tree/bypassDynapath)

## 면책사항

이 프로젝트는 교육 및 개인 학습 목적의 예제입니다. 코레일 또는 관련 서비스의 공식 도구가 아니며, 사용자는 코레일 이용약관과 관련 법령을 직접 확인하고 준수해야 합니다.

- 상업적 목적, 재판매, 대행 예약, 대량 예약, 서비스 방해 목적의 사용을 금지합니다.
- 과도한 반복 조회나 자동 예약 시도는 계정 제한, 접속 차단, 예약 취소 등의 불이익으로 이어질 수 있습니다.
- 본 도구 사용으로 발생하는 계정 제한, 결제 문제, 예약 실패, 약관 위반, 법적 책임은 사용자 본인에게 있습니다.
- 캡차, 본인인증, 결제 인증 등 보안 절차를 우회하지 않습니다.
- 예약 성공 후 결제와 발권은 반드시 사용자가 직접 확인하고 진행해야 합니다.

## 동작 방식

1. 코레일 계정으로 API 로그인합니다.
2. 설정한 출발역, 도착역, 날짜, 시간, 열차종류로 반복 조회합니다.
3. 일반실/특실 좌석이 생기면 `korail.reserve(...)`로 예약합니다.
4. 예약 성공 후 결제/발권은 코레일 앱 또는 웹에서 직접 진행합니다.

## 설치

Python 3.11 이상을 설치한 뒤 프로젝트 루트에서 실행하세요.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 설정 파일

```powershell
Copy-Item config.example.ini config.ini
notepad config.ini
```

`config.ini`는 개인 설정 파일입니다. 배포하거나 커밋하지 마세요.

중요 설정:

- `dep`, `arr`: 역 이름을 한글로 입력합니다. 예: `서울`, `부산`
- `date`: `yyyyMMdd`
- `time`: `hhmmss`
- `train_type`: `KTX`, `ALL`, `ITX_SAEMAEUL`, `MUGUNGHWA` 등
- `train_numbers`: 특정 열차번호만 예약하려면 쉼표로 입력합니다.
- `reserve_option`: `GENERAL_ONLY`, `GENERAL_FIRST`, `SPECIAL_ONLY`, `SPECIAL_FIRST`
- `reserve_when_found`: `false`로 두면 발견 알림만 하고 예약하지 않습니다.
- `interval_seconds = 1`, `jitter_seconds = 3`: 조회/예약 실패 후 1~4초 사이 랜덤 간격으로 재시도합니다.

계정 정보는 `config.ini`에 적지 않고 실행 시 터미널에서 입력해도 됩니다. 환경변수를 쓰려면:

```powershell
$env:KORAIL_ID="회원번호 또는 이메일 또는 전화번호"
$env:KORAIL_PASSWORD="비밀번호"
```

## 실행

```powershell
python -m korail_cancel_macro.main --config config.ini
```

예약에 성공하면 예약 내역과 구매기한이 출력됩니다. 구매기한 안에 코레일 앱 또는 웹에서 결제를 완료하세요.

## 크롬 확장 GUI

1. 크롬 주소창에 `chrome://extensions`를 입력합니다.
2. 오른쪽 위 `개발자 모드`를 켭니다.
3. `압축해제된 확장 프로그램을 로드합니다`를 누릅니다.
4. 이 프로젝트의 `chrome_extension` 폴더를 선택합니다.

확장 아이콘을 누르면 코레일 ID/비밀번호, 날짜, 시간, 출발역, 도착역, 인원, 예약 옵션을 바꿀 수 있습니다. `설정 저장` 버튼을 누르면 프로젝트 루트의 `config.ini`에 바로 반영됩니다.

주의: 확장 팝업에 입력한 비밀번호는 이 PC의 크롬 저장소와 `config.ini`에 평문으로 저장됩니다. 공용 PC에서는 비밀번호를 비워두고 실행 시 터미널에서 입력하세요.

### 확장에서 바로 실행하기

크롬 확장 팝업의 `실행` 버튼까지 쓰려면 Native Messaging host를 한 번 등록해야 합니다.

1. `chrome://extensions`에서 방금 로드한 확장의 ID를 복사합니다.
2. PowerShell에서 아래 명령을 실행합니다.

```powershell
.\install_native_host.ps1 -ExtensionId "복사한_확장_ID"
```

PowerShell 실행 정책 때문에 막히면:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_native_host.ps1 -ExtensionId "복사한_확장_ID"
```

이후 확장 팝업에서:

- `설정 저장`: 현재 팝업 값을 `config.ini`에 저장
- `실행`: 현재 설정을 저장한 뒤 백그라운드에서 매크로 실행
- `멈춤`: 실행 중인 매크로 프로세스 종료
- `지우기`: 로그 화면 지우기

팝업을 닫아도 매크로는 계속 실행됩니다. 중지하려면 `멈춤`을 누르세요.

## 문제 해결

이전 백그라운드 실행을 모두 정리하려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_all_macro.ps1
```

그 다음 `chrome://extensions`에서 확장을 새로고침하고 다시 실행하세요.

## 배포 전 체크리스트

배포 전에 아래 파일과 폴더가 포함되지 않도록 확인하세요.

- `.venv/`
- `config.ini`
- `macro.log`
- `macro.pid`
- `native_host/com.ktx_released_tickets.macro.json`
- `__pycache__/`

