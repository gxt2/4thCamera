# 4thCamera

ROS 2 のカメラ画像処理プログラム。Gazebo シミュレーションと実機 (USB カメラ) の両方で、
**同じトピック構成・同じ処理ノード** が動くように作っている。

## 動作環境 (検証済み)

| 項目 | バージョン |
|---|---|
| OS | Ubuntu 24.04 |
| ROS 2 | Jazzy |
| Gazebo | Harmonic (gz sim 8.15, `ros_gz` 経由) |
| 実機カメラ | Sonix USB Camera (USB ID 26e0:3c13, UVC, `/dev/video0`) |
| 言語 | Python (rclpy, OpenCV 4.6, cv_bridge) |

## 構成

```
src/
  fourth_camera/            ノード本体 (ament_python)
    usb_camera_node.py      実機用 V4L2 カメラドライバ (OpenCV)
    color_detector.py       色ブロブ検出ロジック (ROS 非依存, テスト対象)
    color_detector_node.py  検出ノード
    test/                   pytest
  fourth_camera_bringup/    launch / 設定 / Gazebo ワールド
    launch/sim.launch.py        Gazebo + bridge + 処理
    launch/real.launch.py       USB カメラ + 処理
    launch/processing.launch.py 共通部分 (光学系 TF, 検出ノード, ビューア)
    config/*.yaml
    worlds/camera_world.sdf     固定カメラ + 赤いボール + 青い箱
```

### トピック (sim / real 共通)

| トピック | 型 | 発行元 |
|---|---|---|
| `/camera/image_raw` | sensor_msgs/Image | sim: gz bridge / real: `usb_camera_node` |
| `/camera/camera_info` | sensor_msgs/CameraInfo | 同上 |
| `/camera/detections` | vision_msgs/Detection2DArray | `color_detector` |
| `/camera/image_annotated` | sensor_msgs/Image | `color_detector` (購読者がいる時のみ) |

画像の `frame_id` は両方とも `camera_optical_frame`。
TF: `camera_link` → `camera_optical_frame` (光学系規約: z 前方, x 右, y 下)。
シミュレーションでは加えて `world` → `camera_link` を出す。

## ビルド

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Development/4thCamera
colcon build --symlink-install
source install/setup.bash
```

## 実行

```bash
# Gazebo シミュレーション (GUI + rqt_image_view)
ros2 launch fourth_camera_bringup sim.launch.py
#   headless:=true  … Gazebo GUI なし
#   viewer:=false   … rqt_image_view を開かない

# 実機
ros2 launch fourth_camera_bringup real.launch.py
#   device:=/dev/video2
#   camera_info_file:=/path/to/calibration.yaml
```

シミュレーションでは Gazebo GUI で赤いボールをドラッグすると検出結果が追従する。

## テスト

```bash
colcon test --packages-select fourth_camera && colcon test-result --verbose
```

## 決め打ちの値・制約

- **カメラ姿勢の二重定義**: シミュレーションのカメラ姿勢 (高さ 1.0 m, ピッチ 0.3 rad) は
  `worlds/camera_world.sdf` の `<pose>` と `launch/sim.launch.py` の `world_to_camera_tf` の
  両方に書いてある。片方を変えたら必ずもう片方も変えること。
- **シミュレーションのカメラ内部パラメータ** は実機の既定値に合わせて 640x480 / 30 fps /
  水平画角 60° (1.047 rad) にしている。実機の画角は未測定なので、キャリブレーション後に
  SDF の `horizontal_fov` を実測値に合わせること。
- **実機のフレームレート**: 実機カメラは YUYV 640x480 で 30 fps を申告するが、室内照明では
  実測 約16 fps だった (自動露光で露光時間が伸びるためと推測)。MJPG 1280x720 は 約17 fps。
- **キャリブレーション未実施**: `camera_info_file` が空の場合、`CameraInfo` は幅・高さ以外が
  すべて 0 の未校正データになる。`camera_calibration` パッケージで校正した YAML を指定すること。
- **`gz_frame_id` の警告**: Gazebo 起動時に
  `XML Element[gz_frame_id], child of element[sensor], not defined in SDF` という警告が出るが、
  gz-sensors は読んでおり frame_id は正しく `camera_optical_frame` になる (検証済み)。無害。
- **色検出のしきい値** (`config/color_detector.yaml`) は既定で赤 (H 170–10 を折り返し) 。
  シミュレーションでは赤いボールだけを検出するが、実機では既定値のままだと
  **肌色や赤っぽい物体も誤検出する**。実機では照明に合わせて S/V の下限を上げる等の調整が必要。
- `Detection2D` の `score` は分類器の確信度ではなく、「ブロブ面積 / 画像面積」を入れている。
- 実機ドライバは `usb_cam` / `v4l2_camera` を使わず、OpenCV (V4L2 バックエンド) で自作している
  (追加の apt パッケージを不要にするため)。露光・ホワイトバランス等の V4L2 コントロールは未対応。

## TODO

- [ ] 実機カメラのキャリブレーション (`ros2 run camera_calibration cameracalibrator`) と YAML の同梱
- [ ] 実機の画角を測定し、SDF の `horizontal_fov` と一致させる
- [ ] 実機用の色しきい値のチューニング (または実行時に調整できるよう動的パラメータ対応)
- [ ] 実際にやりたい画像処理の内容に合わせて検出ノードを置き換え / 追加する
      (現在の色ブロブ検出は動作確認用の雛形)
- [ ] シミュレーションで対象物を自動で動かす仕組み (現在は GUI で手動ドラッグ)
- [ ] 露光・ゲイン等の V4L2 コントロールをパラメータ化
