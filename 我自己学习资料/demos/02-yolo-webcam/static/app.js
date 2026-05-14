const frame = document.querySelector("#frame");
const loading = document.querySelector("#loading");
const fps = document.querySelector("#fps");
const detections = document.querySelector("#detections");
const model = document.querySelector("#model");
const camera = document.querySelector("#camera");
const confidence = document.querySelector("#confidence");
const confidenceValue = document.querySelector("#confidenceValue");
const imageInput = document.querySelector("#imageInput");
const message = document.querySelector("#message");
const resultList = document.querySelector("#resultList");
const cameraPreview = document.querySelector("#cameraPreview");
const captureCanvas = document.querySelector("#captureCanvas");
const captureContext = captureCanvas.getContext("2d");

let updateTimer = null;
let detecting = false;

frame.addEventListener("load", () => {
  loading.classList.add("is-hidden");
});

if (frame.complete && frame.naturalWidth > 0) {
  loading.classList.add("is-hidden");
}

frame.addEventListener("error", () => {
  loading.classList.remove("is-hidden");
});

async function refreshStatus() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();

    fps.textContent = Number(data.fps || 0).toFixed(1);
    detections.textContent = data.detections ?? 0;
    model.textContent = data.model || "-";
    camera.textContent = data.camera ?? "-";

    if (typeof data.conf === "number" && document.activeElement !== confidence) {
      confidence.value = data.conf;
      confidenceValue.textContent = data.conf.toFixed(2);
    }
  } catch {
    loading.classList.remove("is-hidden");
  }
}

async function updateConfidence(value) {
  confidenceValue.textContent = Number(value).toFixed(2);
  await fetch("/api/reconfigure", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conf: Number(value) })
  });
}

confidence.addEventListener("input", () => {
  confidenceValue.textContent = Number(confidence.value).toFixed(2);
  clearTimeout(updateTimer);
  updateTimer = setTimeout(() => updateConfidence(confidence.value), 160);
});

async function startBrowserCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 1280, height: 720 },
      audio: false
    });
    cameraPreview.srcObject = stream;
    await cameraPreview.play();
    loading.querySelector("strong").textContent = "摄像头已连接";
    loading.querySelector("span").textContent = "正在进行 YOLO 识别";
    setInterval(detectCameraFrame, 450);
  } catch (error) {
    loading.querySelector("strong").textContent = "摄像头未授权";
    loading.querySelector("span").textContent = "请在浏览器地址栏允许摄像头权限后刷新页面";
    message.textContent = error.message;
  }
}

async function detectCameraFrame() {
  if (detecting || cameraPreview.videoWidth === 0) return;
  detecting = true;

  captureCanvas.width = cameraPreview.videoWidth;
  captureCanvas.height = cameraPreview.videoHeight;
  captureContext.drawImage(cameraPreview, 0, 0, captureCanvas.width, captureCanvas.height);

  captureCanvas.toBlob(async (blob) => {
    if (!blob) {
      detecting = false;
      return;
    }

    const formData = new FormData();
    formData.append("image", blob, "camera.jpg");

    try {
      const response = await fetch("/api/detect", {
        method: "POST",
        body: formData
      });
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "识别失败");

      frame.src = data.image;
      loading.classList.add("is-hidden");
      detections.textContent = data.detections.length;
      resultList.innerHTML = data.detections.slice(0, 8).map((item) => (
        `<div class="result-item"><span>${item.label}</span><strong>${Math.round(item.confidence * 100)}%</strong></div>`
      )).join("");
    } catch (error) {
      message.textContent = error.message;
    } finally {
      detecting = false;
    }
  }, "image/jpeg", 0.8);
}

imageInput.addEventListener("change", async () => {
  const file = imageInput.files[0];
  if (!file) return;

  loading.classList.remove("is-hidden");
  loading.querySelector("strong").textContent = "正在识别";
  loading.querySelector("span").textContent = file.name;
  message.textContent = "模型正在处理图片...";

  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch("/api/detect", {
      method: "POST",
      body: formData
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "识别失败");

    frame.src = data.image;
    detections.textContent = data.detections.length;
    resultList.innerHTML = data.detections.map((item) => (
      `<div class="result-item"><span>${item.label}</span><strong>${Math.round(item.confidence * 100)}%</strong></div>`
    )).join("");
    message.textContent = data.detections.length
      ? `识别到 ${data.detections.length} 个目标`
      : "没有识别到目标，可以降低置信度阈值再试。";
  } catch (error) {
    message.textContent = error.message;
  } finally {
    loading.classList.add("is-hidden");
  }
});

refreshStatus();
setInterval(refreshStatus, 600);
startBrowserCamera();
