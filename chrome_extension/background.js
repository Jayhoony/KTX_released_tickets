let reservationNotified = false;
let paymentNotified = false;

const allowedActions = [
  "saveConfig",
  "saveCredentials",
  "loadCredentials",
  "searchTrains",
  "runMacro",
  "stopMacro",
  "readLog",
  "clearLog",
];

function showNotification(id, title, message) {
  if (!chrome.notifications) return;

  chrome.notifications.create(id, {
    type: "basic",
    iconUrl: chrome.runtime.getURL("icon.svg"),
    title,
    message,
    priority: 2,
  });
}

function notifyFromLog(logText) {
  if (!logText) return;

  if (!reservationNotified && logText.includes("예약 성공:")) {
    reservationNotified = true;
    showNotification(
      "korail-reservation-success",
      "코레일 예약 성공",
      "예약이 완료되었습니다. 결제/발권 상태를 확인하세요."
    );
  }

  if (!paymentNotified && logText.includes("자동결제 성공")) {
    paymentNotified = true;
    showNotification(
      "korail-payment-success",
      "코레일 자동결제 성공",
      "자동결제가 완료되었습니다. 코레일 앱 또는 웹에서 발권 내역을 확인하세요."
    );
  }
}

function resetNotificationState() {
  reservationNotified = false;
  paymentNotified = false;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!allowedActions.includes(message?.action)) {
    return false;
  }

  try {
    const port = chrome.runtime.connectNative("com.ktx_released_tickets.macro");
    let responded = false;

    port.onMessage.addListener((response) => {
      responded = true;

      if (message.action === "readLog" && response?.ok) {
        notifyFromLog(response.log || "");
      }

      sendResponse(response);
      port.disconnect();
    });

    port.onDisconnect.addListener(() => {
      if (!responded) {
        sendResponse({
          ok: false,
          error: chrome.runtime.lastError?.message || "Native host 연결이 끊겼습니다.",
        });
      }
    });

    if (message.action === "saveConfig") {
      port.postMessage({
        action: "saveConfig",
        configIni: message.configIni || "",
      });
    } else if (message.action === "saveCredentials") {
      port.postMessage({
        action: "saveCredentials",
        login: message.login || {},
        payment: message.payment || {},
        email: message.email || {},
      });
    } else if (message.action === "loadCredentials") {
      port.postMessage({ action: "loadCredentials" });
    } else if (message.action === "searchTrains") {
      port.postMessage({
        action: "searchTrains",
        login: message.login || {},
        search: message.search || {},
      });
    } else if (message.action === "runMacro") {
      resetNotificationState();
      port.postMessage({ action: "run" });
    } else if (message.action === "stopMacro") {
      port.postMessage({ action: "stop" });
    } else if (message.action === "readLog") {
      port.postMessage({ action: "readLog" });
    } else {
      resetNotificationState();
      port.postMessage({ action: "clearLog" });
    }
  } catch (error) {
    sendResponse({ ok: false, error: String(error) });
  }

  return true;
});
