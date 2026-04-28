const fields = [
  "korailId",
  "korailPassword",
  "dep",
  "arr",
  "date",
  "time",
  "trainType",
  "reserveOption",
  "earliestTime",
  "latestTime",
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
  dep: "서울",
  arr: "부산",
  date: "",
  time: "09:00",
  trainType: "KTX",
  reserveOption: "GENERAL_ONLY",
  earliestTime: "",
  latestTime: "",
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

function buildIni(data) {
  const date = dateToIni(data.date || todayIso());
  const time = timeToIni(data.time || "09:00");
  const earliestTime = timeToIni(data.earliestTime);
  const latestTime = timeToIni(data.latestTime);
  const waiting = data.includeWaitingList ? "true" : "false";

  return `[account]
; 확장 GUI에서 저장한 값입니다. 비워두면 실행 시 터미널에서 입력합니다.
id = ${data.korailId || ""}
password = ${data.korailPassword || ""}

[trip]
dep = ${data.dep || "서울"}
arr = ${data.arr || "부산"}
date = ${date}
time = ${time}
train_type = ${data.trainType || "KTX"}
train_numbers = ${data.trainNumbers || ""}
earliest_time = ${earliestTime}
latest_time = ${latestTime}

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
reserve_option = ${data.reserveOption || "GENERAL_ONLY"}
include_waiting_list = ${waiting}
try_waiting = ${waiting}

[notification]
beep = ${data.beep ? "true" : "false"}
`;
}

async function saveState() {
  await chrome.storage.local.set(readForm());
  setStatus("저장됨");
}

async function downloadIni() {
  const data = readForm();
  await chrome.storage.local.set(data);
  const blob = new Blob([buildIni(data)], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  await chrome.downloads.download({
    url,
    filename: "config.ini",
    saveAs: true,
    conflictAction: "overwrite",
  });
  setStatus("완료");
}

async function runMacro() {
  const data = readForm();
  await chrome.storage.local.set(data);
  await chrome.runtime.sendMessage({ action: "clearLog" });
  const response = await chrome.runtime.sendMessage({
    action: "runMacro",
    configIni: buildIni(data),
  });
  if (response?.ok) {
    setStatus("실행됨");
    return;
  }
  setStatus("설정필요");
  alert(response?.error || "Native host가 설치되지 않았습니다. install_native_host.ps1을 먼저 실행하세요.");
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

async function init() {
  const stored = await chrome.storage.local.get(fields);
  writeForm({ ...defaults, date: todayIso(), ...stored });
  $("saveState").addEventListener("click", saveState);
  $("downloadIni").addEventListener("click", downloadIni);
  $("runMacro").addEventListener("click", runMacro);
  $("refreshLog").addEventListener("click", refreshLog);
  $("clearLog").addEventListener("click", clearLog);
  window.setInterval(refreshLog, 2500);
  refreshLog();
}

init();
