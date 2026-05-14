import argparse
import atexit
import base64
import threading
import time

import cv2
from flask import Flask, Response, jsonify, render_template, request
import numpy as np
from ultralytics import YOLO


MODEL_ALIASES = {
    "nano": "yolov8n.pt",
    "small": "yolov8s.pt",
}


class WebcamYoloApp:
    def __init__(self, camera_index: int, model_name: str, conf: float, width: int, height: int):
        self.camera_index = camera_index
        self.model_name = model_name
        self.conf = conf
        self.width = width
        self.height = height
        self.model = YOLO(model_name)
        self.lock = threading.Lock()
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {camera_index}，请检查权限或设备编号。")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.latest_annotated = None
        self.latest_info = {
            "fps": 0.0,
            "detections": 0,
            "model": model_name,
            "camera": camera_index,
            "conf": conf,
        }
        self.running = True
        self.last_time = time.time()
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()

    def _reader_loop(self):
        fps_smooth = 0.0
        while self.running:
            success, frame = self.cap.read()
            if not success:
                time.sleep(0.02)
                continue

            results = self.model.predict(frame, conf=self.conf, verbose=False)
            annotated = results[0].plot()
            detections = len(results[0].boxes) if results and results[0].boxes is not None else 0

            now = time.time()
            instant_fps = 1.0 / max(now - self.last_time, 1e-6)
            self.last_time = now
            fps_smooth = instant_fps if fps_smooth == 0.0 else (fps_smooth * 0.9 + instant_fps * 0.1)

            self._draw_overlay(annotated, fps_smooth, detections)

            with self.lock:
                self.latest_annotated = annotated
                self.latest_info = {
                    "fps": round(fps_smooth, 2),
                    "detections": detections,
                    "model": self.model_name,
                    "camera": self.camera_index,
                    "conf": round(self.conf, 2),
                }

    def _draw_overlay(self, frame, fps: float, detections: int):
        text = f"FPS: {fps:.1f} | Detections: {detections} | Model: {self.model_name}"
        cv2.rectangle(frame, (12, 12), (760, 54), (0, 0, 0), -1)
        cv2.putText(
            frame,
            text,
            (24, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    def get_jpeg(self):
        with self.lock:
            frame = None if self.latest_annotated is None else self.latest_annotated.copy()
        if frame is None:
            return None
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        return buffer.tobytes()

    def get_info(self):
        with self.lock:
            return dict(self.latest_info)

    def close(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.cap.release()


app = Flask(__name__, template_folder="templates", static_folder="static")
controller = None
startup_error = None
detector_model = None
detector_conf = 0.35
webcam_enabled = False


def resolve_model_name(model_value: str) -> str:
    return MODEL_ALIASES.get(model_value, model_value)


def parse_args():
    parser = argparse.ArgumentParser(description="YOLO webcam web demo")
    parser.add_argument("--model", default="nano", choices=["nano", "small", "yolov8n.pt", "yolov8s.pt"])
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--webcam", action="store_true", help="Open webcam stream on startup.")
    return parser.parse_args()


@app.route("/")
def home():
    return render_template("index.html", webcam_enabled=webcam_enabled)


@app.route("/api/status")
def status():
    if startup_error is not None:
        return jsonify({"error": startup_error}), 500
    if controller is None:
        return jsonify({
            "fps": 0.0,
            "detections": 0,
            "model": getattr(detector_model, "ckpt_path", "yolov8n.pt"),
            "camera": "未启用",
            "conf": detector_conf,
        })
    return jsonify(controller.get_info())


@app.route("/api/frame")
def frame():
    if controller is None:
        return ("Controller not ready", 503)

    jpeg = controller.get_jpeg()
    if jpeg is None:
        return ("Frame not ready", 503)
    return Response(jpeg, mimetype="image/jpeg")


@app.route("/api/stream")
def stream():
    if controller is None:
        return ("Controller not ready", 503)

    def generate():
        while True:
            jpeg = controller.get_jpeg()
            if jpeg is None:
                time.sleep(0.05)
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            )
            time.sleep(0.03)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/reconfigure", methods=["POST"])
def reconfigure():
    global detector_conf

    data = request.get_json(force=True, silent=True) or {}
    detector_conf = max(0.05, min(0.95, float(data.get("conf", detector_conf))))
    if controller is not None:
        controller.conf = detector_conf
    return jsonify({"ok": True, "conf": detector_conf})


@app.route("/api/detect", methods=["POST"])
def detect_image():
    if detector_model is None:
        return jsonify({"ok": False, "error": "model not ready"}), 503

    uploaded = request.files.get("image")
    if uploaded is None:
        return jsonify({"ok": False, "error": "missing image"}), 400

    file_bytes = np.frombuffer(uploaded.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        return jsonify({"ok": False, "error": "invalid image"}), 400

    results = detector_model.predict(image, conf=detector_conf, verbose=False)
    result = results[0]
    annotated = result.plot()
    ok, buffer = cv2.imencode(".jpg", annotated)
    if not ok:
        return jsonify({"ok": False, "error": "encode failed"}), 500

    names = result.names
    detections = []
    if result.boxes is not None:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "label": names.get(cls_id, str(cls_id)),
                "confidence": round(float(box.conf[0]), 3),
            })

    encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
    return jsonify({
        "ok": True,
        "image": f"data:image/jpeg;base64,{encoded}",
        "detections": detections,
    })


@atexit.register
def cleanup():
    global controller
    if controller is not None:
        controller.close()


def main():
    global controller, detector_model, detector_conf, webcam_enabled
    args = parse_args()
    detector_conf = args.conf
    model_name = resolve_model_name(args.model)
    detector_model = YOLO(model_name)
    webcam_enabled = args.webcam
    if args.webcam:
        controller = WebcamYoloApp(args.camera, model_name, args.conf, args.width, args.height)
    print(f"网页端 demo 已启动：http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
