const demoFrames = [
  {
    image: "",
    imageName: "Waiting for first detection",
    result: "unknown",
    confidence: 0,
    detail: "Dashboard is ready. Live classification data appears after the first capture.",
    frontDistance: "--",
    binDistance: "--",
    fillPercent: null,
    fillDetail: "Waiting for device heartbeat telemetry.",
    servoPosition: "Neutral",
    queueState: "Awaiting Object",
    statusText: "System Ready",
    timestamp: "Waiting for sync",
  },
];

const state = {
  frameIndex: 0,
  history: [],
  latestDetectionKey: null,
  eventsConnected: false,
};

const cameraImage = document.querySelector("#cameraImage");
const imageName = document.querySelector("#imageName");
const resultPill = document.querySelector("#resultPill");
const resultDetail = document.querySelector("#resultDetail");
const confidenceValue = document.querySelector("#confidenceValue");
const confidenceBar = document.querySelector("#confidenceBar");
const frontDistance = document.querySelector("#frontDistance");
const binDistance = document.querySelector("#binDistance");
const fillPercentage = document.querySelector("#fillPercentage");
const fillBar = document.querySelector("#fillBar");
const fillDetail = document.querySelector("#fillDetail");
const servoPosition = document.querySelector("#servoPosition");
const queueState = document.querySelector("#queueState");
const statusText = document.querySelector("#statusText");
const lastSync = document.querySelector("#lastSync");
const historyList = document.querySelector("#historyList");
const backendHealthValue = document.querySelector("#backendHealthValue");
const backendHealthDetail = document.querySelector("#backendHealthDetail");
const deviceHealthValue = document.querySelector("#deviceHealthValue");
const deviceHealthDetail = document.querySelector("#deviceHealthDetail");
const bufferCountValue = document.querySelector("#bufferCountValue");
const bufferCountDetail = document.querySelector("#bufferCountDetail");
const imageUpload = document.querySelector("#imageUpload");
const previewShell = document.querySelector("#previewShell");
const previewImage = document.querySelector("#previewImage");
const uploadStatus = document.querySelector("#uploadStatus");
const analyzeButton = document.querySelector("#analyzeButton");
const bootScreen = document.querySelector("#bootScreen");
const activityOverlay = document.querySelector("#activityOverlay");
const activityTitle = document.querySelector("#activityTitle");
const activityDetail = document.querySelector("#activityDetail");
const modalBackdrop = document.querySelector("#modalBackdrop");
const detailModal = document.querySelector("#detailModal");
const modalClose = document.querySelector("#modalClose");
const modalImage = document.querySelector("#modalImage");
const modalTitle = document.querySelector("#modalTitle");
const modalClass = document.querySelector("#modalClass");
const modalConfidence = document.querySelector("#modalConfidence");
const modalDetail = document.querySelector("#modalDetail");

let selectedFile = null;
document.body.classList.add("app-loading");

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function extractCentimeters(value) {
  const numeric = Number.parseFloat(String(value).replace(/[^\d.]/g, ""));
  return Number.isFinite(numeric) ? numeric : null;
}

function parseNullableNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatDistance(distanceCm) {
  const numeric = parseNullableNumber(distanceCm);
  return numeric === null ? "--" : `${numeric} cm`;
}

function describeFillLevel(fillPercent, detailText) {
  if (!Number.isFinite(fillPercent)) {
    return {
      percent: 0,
      detail: detailText || "Fill level unavailable.",
      color: "linear-gradient(90deg, #75e0bf, #84de96)",
    };
  }

  const percent = Math.max(0, Math.min(100, Math.round(fillPercent)));
  if (percent >= 85) {
    return {
      percent,
      detail: detailText || "Bin is nearly full and should be emptied soon.",
      color: "linear-gradient(90deg, #ff9a52, #ff735b)",
    };
  }

  if (percent >= 55) {
    return {
      percent,
      detail: detailText || "Bin is over half full.",
      color: "linear-gradient(90deg, #ffb36a, #ffd36f)",
    };
  }

  return {
    percent,
    detail: detailText || "Bin has plenty of remaining space.",
    color: "linear-gradient(90deg, #75e0bf, #84de96)",
  };
}

function renderHistory() {
  historyList.innerHTML = "";

  if (state.history.length === 0) {
    const emptyState = document.createElement("article");
    emptyState.className = "history-item";
    emptyState.innerHTML = `
      <div></div>
      <div>
        <div class="history-name">No detections yet</div>
      </div>
      <div><span class="history-result">Waiting</span></div>
      <div class="history-score">--</div>
    `;
    historyList.appendChild(emptyState);
    return;
  }

  state.history.forEach((item) => {
    const row = document.createElement("article");
    row.className = "history-item";

    const resultClass = item.result === "nonbio" ? "history-result nonbio" : "history-result";

    row.innerHTML = `
      <img class="history-thumb" src="${item.image}" alt="${item.name}" />
      <div>
        <div class="history-name">${item.name}</div>
      </div>
      <div><span class="${resultClass}">${titleCase(item.result)}</span></div>
      <div class="history-score">${item.confidence}</div>
    `;
    row.addEventListener("click", () => openDetailModal(item));

    historyList.appendChild(row);
  });
}

function toHistoryItem(record) {
  return {
    key: getDetectionKey(record),
    name: record.saved_as,
    result: record.result,
    confidence: `${Math.round(Number(record.confidence || 0) * 100)}%`,
    image: `${getBaseUrl()}${record.received_url}`,
    detail: `Model returned ${String(record.result || "unknown").toUpperCase()} from label ${record.raw}.`,
  };
}

function getDetectionKey(record) {
  return `${record.saved_as || "unknown"}::${record.created_at || "unknown"}`;
}

function applyDetection(record, options = {}) {
  const baseUrl = getBaseUrl();
  const detectionKey = getDetectionKey(record);
  const result = record.result || "unknown";
  const confidence = Number(record.confidence || 0);
  const imageUrl = `${baseUrl}${record.received_url}`;

  state.latestDetectionKey = detectionKey;

  renderFrame({
    image: imageUrl,
    imageName: record.saved_as || "Waiting for first detection",
    result,
    confidence,
    detail: `Model returned ${String(result).toUpperCase()} from label ${record.raw}.`,
    frontDistance: frontDistance.textContent,
    binDistance: binDistance.textContent,
    fillPercent: extractCentimeters(fillPercentage.textContent),
    fillDetail: fillDetail.textContent,
    servoPosition: result === "bio" ? "Left Gate" : result === "nonbio" ? "Right Gate" : "Neutral",
    queueState: options.queueState || "Prediction Complete",
    statusText: options.statusText || `Live Result: ${String(result).toUpperCase()}`,
    timestamp: record.created_at || lastSync.textContent,
  });

  const nextHistoryItem = toHistoryItem(record);
  state.history = [nextHistoryItem, ...state.history.filter((item) => item.key !== detectionKey)].slice(0, 6);
  renderHistory();
}

function setActivityState(title, detail) {
  activityTitle.textContent = title;
  activityDetail.textContent = detail;
}

function showActivity(title, detail) {
  setActivityState(title, detail);
  activityOverlay.classList.remove("hidden");
}

function hideActivity() {
  activityOverlay.classList.add("hidden");
}

function openDetailModal(item) {
  modalImage.src = item.image;
  modalTitle.textContent = item.name;
  modalClass.textContent = titleCase(item.result);
  modalConfidence.textContent = item.confidence;
  modalDetail.textContent = item.detail || "Saved detection preview from the recent detections log.";
  modalBackdrop.classList.remove("hidden");
  detailModal.classList.remove("hidden");
}

function closeDetailModal() {
  modalBackdrop.classList.add("hidden");
  detailModal.classList.add("hidden");
}

function renderFrame(frame) {
  if (frame.image) {
    cameraImage.src = frame.image;
  } else {
    cameraImage.removeAttribute("src");
  }
  imageName.textContent = frame.imageName;
  resultPill.textContent = frame.result.toUpperCase();
  resultPill.className = frame.result === "nonbio" ? "result-pill nonbio" : "result-pill";
  resultDetail.textContent = frame.detail;
  confidenceValue.textContent = `${Math.round(frame.confidence * 100)}%`;
  confidenceBar.style.width = `${Math.round(frame.confidence * 100)}%`;
  confidenceBar.style.background =
    frame.result === "nonbio"
      ? "linear-gradient(90deg, #ff9a52, #f3c97b)"
      : "linear-gradient(90deg, #72d26d, #f3c97b)";

  frontDistance.textContent = frame.frontDistance;
  binDistance.textContent = frame.binDistance;
  const fillState = describeFillLevel(frame.fillPercent, frame.fillDetail);
  fillPercentage.textContent = `${fillState.percent}%`;
  fillBar.style.width = `${fillState.percent}%`;
  fillBar.style.background = fillState.color;
  fillDetail.textContent = fillState.detail;
  servoPosition.textContent = frame.servoPosition;
  queueState.textContent = frame.queueState;
  statusText.textContent = frame.statusText;
  lastSync.textContent = frame.timestamp;
}

function getBaseUrl() {
  if (window.location.origin && window.location.origin !== "null") {
    return window.location.origin;
  }

  return "http://127.0.0.1:5000";
}

async function checkHealth() {
  const baseUrl = getBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/status`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Health check failed.");
    }

    applyStatus(payload);
  } catch (_error) {
    backendHealthValue.textContent = "Down";
    backendHealthDetail.textContent = "Backend status poll failed.";
  }
}

function applyStatus(payload) {
  const backendHealthy = Boolean(payload?.backend?.healthy);
  const checkedAt = payload?.backend?.checked_at || "unknown";
  const deviceOnline = Boolean(payload?.esp32?.online);
  const lastHeartbeat = payload?.esp32?.last_heartbeat_at;
  const timeoutSeconds = payload?.esp32?.timeout_seconds ?? 150;
  const deviceStatus = payload?.esp32?.device_status || "unknown";
  const binDistanceCm = parseNullableNumber(payload?.esp32?.bin?.distance_cm);
  const binFillPercent = parseNullableNumber(payload?.esp32?.bin?.fill_percent);
  const binFillDetail = payload?.esp32?.bin?.detail;
  const captureCount = Number(payload?.capture_buffer?.count ?? 0);

  backendHealthValue.textContent = backendHealthy ? "Healthy" : "Down";
  backendHealthDetail.textContent = `Last status check: ${checkedAt}`;

  deviceHealthValue.textContent = deviceOnline ? "Online" : "Offline";
  deviceHealthDetail.textContent = lastHeartbeat
    ? `Last heartbeat: ${lastHeartbeat} | ${deviceStatus} | timeout ${timeoutSeconds}s`
    : `No heartbeat yet | timeout ${timeoutSeconds}s`;

  bufferCountValue.textContent = `${captureCount} item${captureCount === 1 ? "" : "s"}`;
  bufferCountDetail.textContent = "Saved image files currently present in `received/`.";

  binDistance.textContent = formatDistance(binDistanceCm);
  const fillState = describeFillLevel(binFillPercent, binFillDetail);
  fillPercentage.textContent = `${fillState.percent}%`;
  fillBar.style.width = `${fillState.percent}%`;
  fillBar.style.background = fillState.color;
  fillDetail.textContent = fillState.detail;
}

async function loadDetections() {
  const baseUrl = getBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/detections`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Could not load detections.");
    }

    const detections = Array.isArray(payload.detections) ? payload.detections : [];
    state.history = detections.slice(0, 6).map(toHistoryItem);
    renderHistory();

    if (detections.length > 0) {
      applyDetection(detections[0]);
    }
  } catch (_error) {
    renderHistory();
  }
}

function connectDetectionStream() {
  const baseUrl = getBaseUrl();
  const eventSource = new EventSource(`${baseUrl}/events`);

  eventSource.addEventListener("connected", () => {
    state.eventsConnected = true;
  });

  eventSource.addEventListener("detection", (event) => {
    try {
      const record = JSON.parse(event.data);
      const detectionKey = getDetectionKey(record);

      if (detectionKey === state.latestDetectionKey) {
        return;
      }

      applyDetection(record, {
        queueState: "Live Update Received",
        statusText: `Live Result: ${String(record.result || "unknown").toUpperCase()}`,
      });
      checkHealth();
    } catch (_error) {
      // Ignore malformed events and keep the stream alive.
    }
  });

  eventSource.onerror = () => {
    state.eventsConnected = false;
  };
}

function handleImageUpload(event) {
  const [file] = event.target.files || [];

  if (!file) {
    selectedFile = null;
    previewImage.src = "";
    previewShell.classList.add("hidden");
    analyzeButton.disabled = true;
    uploadStatus.textContent = "No local file selected yet.";
    return;
  }

  selectedFile = file;
  const objectUrl = URL.createObjectURL(file);
  previewShell.classList.remove("hidden");
  previewImage.src = objectUrl;
  cameraImage.src = objectUrl;
  imageName.textContent = file.name;
  analyzeButton.disabled = false;
  uploadStatus.textContent = `Loaded local preview: ${file.name}`;
}

async function analyzeSelectedImage() {
  if (!selectedFile) {
    uploadStatus.textContent = "Choose an image first.";
    return;
  }

  const baseUrl = getBaseUrl();
  showActivity("Analyzing Image", "Uploading image to the Flask backend.");
  uploadStatus.textContent = `Uploading ${selectedFile.name} to ${baseUrl}/predict ...`;

  try {
    const response = await fetch(`${baseUrl}/predict`, {
      method: "POST",
      headers: {
        "Content-Type": selectedFile.type || "application/octet-stream",
      },
      body: selectedFile,
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Prediction failed.");
    }

    const timestamp = new Date().toLocaleString();
    const result = payload.result || "unknown";
    const confidence = typeof payload.confidence === "number" ? payload.confidence : 0;
    const receivedImageUrl = payload.received_url ? `${baseUrl}${payload.received_url}` : previewImage.src;

    renderFrame({
      image: receivedImageUrl,
      imageName: payload.saved_as || selectedFile.name,
      result,
      confidence,
      detail: `Model returned ${result.toUpperCase()} from label ${payload.raw}.`,
      frontDistance: frontDistance.textContent,
      binDistance: binDistance.textContent,
      fillPercent: extractCentimeters(fillPercentage.textContent),
      fillDetail: fillDetail.textContent,
      servoPosition: result === "bio" ? "Left Gate" : result === "nonbio" ? "Right Gate" : "Neutral",
      queueState: "Prediction Complete",
      statusText: `Live Result: ${result.toUpperCase()}`,
      timestamp,
    });

    await loadDetections();
    uploadStatus.textContent = `Prediction complete: ${result.toUpperCase()} (${Math.round(confidence * 100)}%)`;
    openDetailModal({
      name: payload.saved_as || selectedFile.name,
      result,
      confidence: `${Math.round(confidence * 100)}%`,
      image: receivedImageUrl,
      detail: `Model returned ${result.toUpperCase()} from label ${payload.raw}.`,
    });
  } catch (error) {
    uploadStatus.textContent = `Prediction failed: ${error.message}`;
  } finally {
    hideActivity();
  }
}

imageUpload.addEventListener("change", handleImageUpload);
analyzeButton.addEventListener("click", analyzeSelectedImage);
modalClose.addEventListener("click", closeDetailModal);
modalBackdrop.addEventListener("click", closeDetailModal);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDetailModal();
  }
});

renderFrame(demoFrames[state.frameIndex]);
renderHistory();
loadDetections();
checkHealth();
window.setInterval(checkHealth, 15000);
window.setInterval(loadDetections, 30000);
connectDetectionStream();
analyzeButton.disabled = true;
window.addEventListener("load", () => {
  window.setTimeout(() => {
    bootScreen.classList.add("hidden");
    document.body.classList.remove("app-loading");
  }, 1200);
});
