import argparse
import time

import cv2
from ultralytics import YOLO


MODEL_ALIASES = {
    "nano": "yolov8n.pt",
    "small": "yolov8s.pt",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Camera demo with YOLO object detection and on-screen visualization."
    )
    parser.add_argument(
        "--model",
        default="nano",
        choices=["nano", "small", "yolov8n.pt", "yolov8s.pt"],
        help="YOLO model to use. 'nano' is the fastest default.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index, usually 0 for the built-in webcam.",
    )
    parser.add_argument("--width", type=int, default=1280, help="Camera capture width.")
    parser.add_argument("--height", type=int, default=720, help="Camera capture height.")
    parser.add_argument("--conf", type=float, default=0.35, help="Confidence threshold.")
    parser.add_argument("--target-fps", type=int, default=60, help="Target visualization refresh rate.")
    return parser.parse_args()


def resolve_model_name(model_value: str) -> str:
    return MODEL_ALIASES.get(model_value, model_value)


def draw_fps(frame, fps: float, detection_count: int):
    overlay = f"FPS: {fps:.1f} | Detections: {detection_count} | Press Q to quit"
    cv2.rectangle(frame, (12, 12), (560, 54), (0, 0, 0), -1)
    cv2.putText(
        frame,
        overlay,
        (24, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def main():
    args = parse_args()
    model_name = resolve_model_name(args.model)

    model = YOLO(model_name)
    cap = cv2.VideoCapture(args.camera)

    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 {args.camera}，请检查权限或设备编号。")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    target_frame_time = 1.0 / max(args.target_fps, 1)
    last_time = time.time()
    fps_smooth = 0.0

    print("摄像头已启动，按 Q 退出。")
    print(f"模型：{model_name}")

    try:
        while True:
            loop_start = time.time()
            success, frame = cap.read()
            if not success:
                print("读取摄像头帧失败，正在重试...")
                continue

            results = model.predict(frame, conf=args.conf, verbose=False)
            annotated = results[0].plot()
            detection_count = len(results[0].boxes) if results and results[0].boxes is not None else 0

            now = time.time()
            instant_fps = 1.0 / max(now - last_time, 1e-6)
            last_time = now
            fps_smooth = instant_fps if fps_smooth == 0.0 else (fps_smooth * 0.9 + instant_fps * 0.1)

            draw_fps(annotated, fps_smooth, detection_count)
            cv2.imshow("YOLO Webcam Demo", annotated)

            elapsed = time.time() - loop_start
            wait_ms = max(int((target_frame_time - elapsed) * 1000), 1)
            key = cv2.waitKey(wait_ms) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
