chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.action !== "runMacro") {
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

    port.postMessage({
      action: "run",
      configIni: message.configIni || "",
    });
  } catch (error) {
    sendResponse({ ok: false, error: String(error) });
  }

  return true;
});
