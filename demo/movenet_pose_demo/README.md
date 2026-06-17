# MoveNet Pose Demo

本地浏览器 demo，用 **MoveNet Lightning** 对当前摄像头画面做人体 17 个关节点实时识别。

## 为什么选它

- 小模型，适合实时姿态估计
- 识别 17 个 COCO 人体关键点
- 浏览器里用 TensorFlow.js 跑推理
- 支持摄像头实时画面

MoveNet 官方说明：它是 ultra fast and accurate pose detection model，可以检测人体 17 个 keypoints；Lightning 面向低延迟场景。

## 运行

```bash
cd /Users/kaijimima1234/Desktop/课件资料/demo/movenet_pose_demo
python3 -m http.server 8765
```

然后打开：

```text
http://localhost:8765
```

## 注意

- 首次打开需要联网加载 TensorFlow.js 和 MoveNet 模型。
- 模型下载后，推理在本机浏览器里运行。
- 摄像头权限只在 `localhost` 或 HTTPS 下可用。
- 页面只做实时摄像头识别，不包含上传图片模式。

## 关节点

`nose, left_eye, right_eye, left_ear, right_ear, left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle`

## 参考

- GitHub: https://github.com/tensorflow/tfjs-models/tree/master/pose-detection
- MoveNet README: https://github.com/tensorflow/tfjs-models/blob/master/pose-detection/src/movenet/README.md
- TensorFlow tutorial: https://www.tensorflow.org/hub/tutorials/movenet
