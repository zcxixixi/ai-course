import argparse
import time
from collections import Counter

import cv2
from ultralytics import YOLO


MODEL_ALIASES = {
    "nano": "yolov8n.pt",
    "small": "yolov8s.pt",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Simple command-line YOLO webcam demo.")
    parser.add_argument("--model", default="nano", choices=["nano", "small", "yolov8n.pt", "yolov8s.pt"])
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between terminal outputs.")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    return parser.parse_args()


def resolve_model_name(model_value: str) -> str:
    return MODEL_ALIASES.get(model_value, model_value)


def summarize_detections(result):
    if result.boxes is None or len(result.boxes) == 0:
        return "未识别到物体"

    names = result.names
    labels = []
    details = []

    for box in result.boxes:
        cls_id = int(box.cls[0])
        label = names.get(cls_id, str(cls_id))
        confidence = float(box.conf[0])
        labels.append(label)
        details.append(f"{label} {confidence:.2f}")

    counts = Counter(labels)
    summary = ", ".join(f"{name} x{count}" for name, count in counts.items())
    return f"{summary} | " + ", ".join(details[:8])


def main():
    args = parse_args()
    model_name = resolve_model_name(args.model)
    model = YOLO(model_name)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 {args.camera}，请检查权限或设备编号。")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    print("YOLO 命令行识别已启动。按 Ctrl+C 停止。")
    print(f"模型：{model_name} | 摄像头：{args.camera} | 置信度：{args.conf}")

    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("读取摄像头失败，正在重试...")
                time.sleep(args.interval)
                continue

            result = model.predict(frame, conf=args.conf, verbose=False)[0]
            now = time.strftime("%H:%M:%S")
            print(f"[{now}] {summarize_detections(result)}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        cap.release()


if __name__ == "__main__":
    main()
