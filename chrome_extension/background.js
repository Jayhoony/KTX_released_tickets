chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!["saveConfig", "runMacro", "stopMacro", "readLog", "clearLog"].includes(message?.action)) {
    return false;
  }

  try {
    const port = chrome.runtime.connectNative("com.ktx_released_tickets.macro");
    let responded = false;

    port.onMessage.addListener((response) => {
      responded = true;
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
    } else if (message.action === "runMacro") {
      port.postMessage({
        action: "run",
      });
    } else if (message.action === "stopMacro") {
      port.postMessage({ action: "stop" });
    } else if (message.action === "readLog") {
      port.postMessage({ action: "readLog" });
    } else {
      port.postMessage({ action: "clearLog" });
    }
  } catch (error) {
    sendResponse({ ok: false, error: String(error) });
  }

  return true;
});
