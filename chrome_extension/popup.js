const fields = [
  "korailId",
  "korailPassword",
  "saveLoginSecure",
  "savePaymentSecure",
  "cardNumber",
  "cardPassword",
  "cardExpire",
  "cardValidation",
  "cardCorporate",
  "autoPayment",
  "dep",
  "arr",
  "date",
  "time",
  "trainType",
  "reserveOption",
  "trainNumbers",
  "adults",
  "children",
  "toddlers",
  "seniors",
  "intervalSeconds",
  "maxAttempts",
  "reserveWhenFound",
  "includeWaitingList",
  "beep",
];

const defaults = {
  korailId: "",
  korailPassword: "",
  saveLoginSecure: true,
  savePaymentSecure: false,
  cardNumber: "",
  cardPassword: "",
  cardExpire: "",
  cardValidation: "",
  cardCorporate: false,
  autoPayment: false,
  dep: "서울",
  arr: "부산",
  date: "",
  time: "09:00",
  trainType: "KTX",
  reserveOption: "GENERAL_SPECIAL",
  trainNumbers: "",
  adults: "1",
  children: "0",
  toddlers: "0",
  seniors: "0",
  intervalSeconds: "12",
  maxAttempts: "0",
  reserveWhenFound: true,
  includeWaitingList: false,
  beep: true,
};

const $ = (id) => document.getElementById(id);

function todayIso() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function setStatus(text) {
  $("status").textContent = text;
  window.setTimeout(() => {
    $("status").textContent = "준비";
  }, 1600);
}

function readForm() {
  const data = {};
  for (const field of fields) {
    const element = $(field);
    data[field] = element.type === "checkbox" ? element.checked : element.value.trim();
  }
  return data;
}

function writeForm(data) {
  for (const field of fields) {
    const element = $(field);
    const value = data[field] ?? defaults[field];
    if (element.type === "checkbox") {
      element.checked = Boolean(value);
    } else {
      element.value = value;
    }
  }
}

function digitsOnly(value) {
  return String(value || "").replace(/\D/g, "");
}

function dateToIni(value) {
  return value.replaceAll("-", "");
}

function timeToIni(value) {
  if (!value) return "";
  return value.replace(":", "").padEnd(6, "0");
}

function numberValue(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? String(parsed) : fallback;
}

function selectedTrainNumbers() {
  return $("trainNumbers")
    .value.split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function syncTrainNumberField() {
  const selected = [...document.querySelectorAll(".train-check:checked")].map((input) => input.value);
  $("trainNumbers").value = selected.join(",");
}

function buildIni(data) {
  const date = dateToIni(data.date || todayIso());
  const time = timeToIni(data.time || "09:00");
  const waiting = data.includeWaitingList ? "true" : "false";
  const writePlainLogin = !data.saveLoginSecure;

  return `[account]
; 보안 저장을 켜면 계정정보는 Windows 자격 증명 저장소에 저장되고 ini에는 남지 않습니다.
id = ${writePlainLogin ? data.korailId || "" : ""}
password = ${writePlainLogin ? data.korailPassword || "" : ""}

[trip]
dep = ${data.dep || "서울"}
arr = ${data.arr || "부산"}
date = ${date}
time = ${time}
train_type = ${data.trainType || "KTX"}
train_numbers = ${data.trainNumbers || ""}

[passengers]
adults = ${numberValue(data.adults, "1")}
children = ${numberValue(data.children, "0")}
toddlers = ${numberValue(data.toddlers, "0")}
seniors = ${numberValue(data.seniors, "0")}

[macro]
interval_seconds = ${numberValue(data.intervalSeconds, "12")}
jitter_seconds = 3
max_attempts = ${numberValue(data.maxAttempts, "0")}
login_max_attempts = 3
reserve_when_found = ${data.reserveWhenFound ? "true" : "false"}
reserve_option = ${data.reserveOption || "GENERAL_SPECIAL"}
include_waiting_list = ${waiting}
try_waiting = ${waiting}
auto_payment = ${data.autoPayment ? "true" : "false"}

[notification]
beep = ${data.beep ? "true" : "false"}
`;
}

function buildCredentialPayload(data) {
  const cardNumber = digitsOnly(data.cardNumber);
  const cardPassword = digitsOnly(data.cardPassword);
  const expire = digitsOnly(data.cardExpire);
  const validationNumber = digitsOnly(data.cardValidation);

  return {
    login: data.saveLoginSecure
      ? {
          save: Boolean(data.korailId && data.korailPassword),
          username: data.korailId,
          password: data.korailPassword,
        }
      : { delete: true },
    payment: data.savePaymentSecure
      ? {
          save: Boolean(cardNumber && cardPassword && expire && validationNumber),
          cardNumber,
          cardPassword,
          expire,
          validationNumber,
          isCorporate: data.cardCorporate,
        }
      : { delete: true },
  };
}

function validateSensitiveSettings(data) {
  if (data.saveLoginSecure && (!data.korailId || !data.korailPassword)) {
    setStatus("확인필요");
    alert("보안 저장을 켠 상태에서는 코레일 ID와 비밀번호를 입력해야 합니다.");
    return false;
  }
  if (
    (data.savePaymentSecure || data.autoPayment) &&
    (!digitsOnly(data.cardNumber) ||
      !digitsOnly(data.cardPassword) ||
      !digitsOnly(data.cardExpire) ||
      !digitsOnly(data.cardValidation))
  ) {
    setStatus("확인필요");
    alert("결제정보 보안 저장 또는 자동결제를 쓰려면 카드정보를 모두 입력해야 합니다.");
    return false;
  }
  if (data.autoPayment && !data.savePaymentSecure) {
    setStatus("확인필요");
    alert("자동결제를 쓰려면 결제정보 보안 저장을 켜야 합니다.");
    return false;
  }
  return true;
}

async function saveCredentials(data) {
  const response = await chrome.runtime.sendMessage({
    action: "saveCredentials",
    ...buildCredentialPayload(data),
  });
  if (!response?.ok) {
    setStatus("실패");
    alert(response?.error || "보안 저장에 실패했습니다.");
    return false;
  }
  return true;
}

async function saveConfig() {
  const data = readForm();
  if (!validateSensitiveSettings(data)) return false;

  await chrome.storage.local.set({
    ...data,
    korailPassword: data.saveLoginSecure ? "" : data.korailPassword,
    cardNumber: "",
    cardPassword: "",
    cardExpire: "",
    cardValidation: "",
  });

  if (!(await saveCredentials(data))) return false;

  const response = await chrome.runtime.sendMessage({
    action: "saveConfig",
    configIni: buildIni(data),
  });
  if (!response?.ok) {
    setStatus("실패");
    alert(response?.error || "설정 저장에 실패했습니다.");
    return false;
  }
  setStatus("저장됨");
  return true;
}

function renderTrainList(trains) {
  const list = $("trainList");
  if (!trains.length) {
    list.textContent = "조회 결과가 없습니다.";
    return;
  }

  const selected = new Set(selectedTrainNumbers());
  list.textContent = "";
  for (const train of trains) {
    const label = document.createElement("label");
    label.className = "train-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "train-check";
    checkbox.value = train.trainNo;
    checkbox.checked = selected.size ? selected.has(train.trainNo) : train.available;
    checkbox.addEventListener("change", syncTrainNumberField);

    const main = document.createElement("span");
    main.className = "train-main";
    main.textContent = `${train.trainTypeName} ${train.trainNo} ${train.depTime}-${train.arrTime}`;

    const seats = document.createElement("span");
    seats.className = "train-seats";
    seats.textContent = [
      train.general ? "일반 가능" : "일반 매진",
      train.special ? "특실 가능" : "특실 매진",
      train.waiting ? "대기 가능" : "",
    ]
      .filter(Boolean)
      .join(" · ");

    label.append(checkbox, main, seats);
    list.append(label);
  }
  syncTrainNumberField();
}

async function searchTrains() {
  const data = readForm();
  if (!data.korailId || !data.korailPassword) {
    setStatus("확인필요");
    alert("열차 조회를 하려면 코레일 ID와 비밀번호를 입력해야 합니다.");
    return;
  }
  if (!data.dep || !data.arr || !data.date || !data.time) {
    setStatus("확인필요");
    alert("출발, 도착, 날짜, 시간을 먼저 입력하세요.");
    return;
  }

  setStatus("조회중");
  if (data.saveLoginSecure && !(await saveCredentials(data))) return;

  const response = await chrome.runtime.sendMessage({
    action: "searchTrains",
    login: {
      username: data.korailId,
      password: data.korailPassword,
    },
    search: {
      dep: data.dep,
      arr: data.arr,
      date: dateToIni(data.date),
      time: timeToIni(data.time),
      trainType: data.trainType,
      includeWaitingList: data.includeWaitingList,
      adults: numberValue(data.adults, "1"),
      children: numberValue(data.children, "0"),
      toddlers: numberValue(data.toddlers, "0"),
      seniors: numberValue(data.seniors, "0"),
    },
  });
  if (!response?.ok) {
    setStatus("실패");
    alert(response?.error || "열차 조회에 실패했습니다.");
    return;
  }
  renderTrainList(response.trains || []);
  setStatus("조회됨");
}

async function runMacro() {
  const saved = await saveConfig();
  if (!saved) return;
  await chrome.runtime.sendMessage({ action: "clearLog" });
  const response = await chrome.runtime.sendMessage({ action: "runMacro" });
  if (response?.ok) {
    setStatus("실행중");
    await refreshLog();
    return;
  }
  setStatus("실패");
  alert(response?.error || "Native host가 설치되지 않았습니다. install_native_host.ps1을 먼저 실행하세요.");
}

async function stopMacro() {
  const response = await chrome.runtime.sendMessage({ action: "stopMacro" });
  if (response?.ok) {
    setStatus("멈춤");
    await refreshLog();
    return;
  }
  setStatus("실패");
  alert(response?.error || "매크로를 멈추지 못했습니다.");
}

async function refreshLog() {
  const response = await chrome.runtime.sendMessage({ action: "readLog" });
  const output = $("logOutput");
  if (!response?.ok) {
    output.textContent = response?.error || "로그를 읽지 못했습니다.";
    return;
  }

  output.textContent = response.log || "아직 로그가 없습니다.";
  output.scrollTop = output.scrollHeight;
}

async function clearLog() {
  await chrome.runtime.sendMessage({ action: "clearLog" });
  $("logOutput").textContent = "아직 로그가 없습니다.";
}

async function loadSecureCredentials() {
  const response = await chrome.runtime.sendMessage({ action: "loadCredentials" });
  if (!response?.ok) return {};

  const loaded = {};
  if (response.login) {
    loaded.korailId = response.login.username || "";
    loaded.korailPassword = response.login.password || "";
    loaded.saveLoginSecure = true;
  }
  if (response.payment) {
    loaded.cardNumber = response.payment.cardNumber || "";
    loaded.cardPassword = response.payment.cardPassword || "";
    loaded.cardExpire = response.payment.expire || "";
    loaded.cardValidation = response.payment.validationNumber || "";
    loaded.cardCorporate = Boolean(response.payment.isCorporate);
    loaded.savePaymentSecure = true;
  }
  return loaded;
}

function wireDigitFilters() {
  for (const id of ["cardNumber", "cardPassword", "cardExpire", "cardValidation"]) {
    $(id).addEventListener("input", (event) => {
      event.target.value = digitsOnly(event.target.value);
    });
  }
}

async function init() {
  const stored = await chrome.storage.local.get(fields);
  const secure = await loadSecureCredentials();
  writeForm({ ...defaults, date: todayIso(), ...stored, ...secure });
  wireDigitFilters();
  $("saveConfig").addEventListener("click", saveConfig);
  $("searchTrains").addEventListener("click", searchTrains);
  $("runMacro").addEventListener("click", runMacro);
  $("stopMacro").addEventListener("click", stopMacro);
  $("refreshLog").addEventListener("click", refreshLog);
  $("clearLog").addEventListener("click", clearLog);
  window.setInterval(refreshLog, 2500);
  refreshLog();
}

init();

