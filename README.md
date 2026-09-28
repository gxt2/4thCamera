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
    config/usb_camera_calibration.yaml  実機カメラの校正結果
    worlds/camera_world.sdf     固定カメラ + 赤いボール + 青い箱
tools/
  make_checkerboard.py      印刷用チェッカーボード PDF 生成 (依存なし)
  refine_calibration.py     校正データからブレた画像を除いて再校正
docs/
  checkerboard_8x6_25mm.pdf 校正に使ったボード (A4 横, 100% で印刷)
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
#   camera_info_file:=/path/to/calibration.yaml  (既定: config/usb_camera_calibration.yaml)
```

シミュレーションでは Gazebo GUI で赤いボールをドラッグすると検出結果が追従する。

## 実機カメラのキャリブレーション

### 結果 (2026-09-28, Sonix USB Camera, 640x480)

| 項目 | 値 |
|---|---|
| fx, fy | 653.7, 649.4 px |
| cx, cy | 306.4, 239.6 px |
| 歪み (plumb_bob) | k1=-0.435, k2=0.204, p1=0.0002, p2=0.0021, k3=0 (固定) |
| 水平 / 垂直画角 | 52.2° / 40.6° |
| 再投影誤差 RMS | 0.80 px (採用 46 枚。全 65 枚だと 1.42 px) |
| ボード距離 / 傾き | 0.22–0.84 m / 最大 25° |

樽型歪みが強い (k1=-0.44) ので、画像の端を使う幾何計算では必ず歪み補正すること。

### 手順 (やり直す場合)

```bash
sudo apt install ros-jazzy-camera-calibration
python3 tools/make_checkerboard.py -o checkerboard.pdf   # 8x6 内側コーナー, 25mm
# 実際のサイズ (100%) で印刷し、下のバーが 100mm か定規で確認。板に平らに貼る。

ros2 launch fourth_camera_bringup real.launch.py viewer:=false camera_info_file:=''
# カメラのトピックが見えてから起動すること
ros2 run camera_calibration cameracalibrator --size 8x6 --square 0.025 \
    --no-service-check --ros-args -r image:=/camera/image_raw -p camera:=/camera
# ボードを動かす → CALIBRATE → SAVE (/tmp/calibrationdata.tar.gz)。COMMIT は使えない。

python3 tools/refine_calibration.py /tmp/calibrationdata.tar.gz \
    -o src/fourth_camera_bringup/config/usb_camera_calibration.yaml
```

### 注意点

- **ブレた画像が誤差の主因**: 実機が室内で約16fps (露光時間が長い) のため、ボードを動かしながら
  撮ると画像がブレる。1 枚ごとの誤差と画像の鮮鋭度は強い負の相関 (-0.72) があった。
  `cameracalibrator` はブレた画像も採用してしまうので、`refine_calibration.py` で
  1 枚あたりの誤差が 1.5 px を超える画像を除いて再計算している。撮影時は時々ボードを止めること。
- **GUI の 4 本のバーが伸びないことがある**: ボードが画面から少しでもはみ出すと検出されないため、
  端の位置が撮れずバーが伸びない。サンプルが 40 枚を超えると CALIBRATE は押せるようになるので、
  そこで計算し、`refine_calibration.py` の出力 (誤差・範囲) で良し悪しを判断すればよい。
- **COMMIT ボタンは使えない**: `usb_camera_node` は `set_camera_info` サービスを持たないため。
  SAVE した tarball から YAML を作る。
- **校正の元画像はリポジトリに入れていない** (約 9.5MB、人物が写っているため)。
  再計算したい場合は撮り直すこと。
- **k3 は 0 に固定**: k3 を自由にしても RMS は同じ (0.795 vs 0.796 px) で、画像の端で値が暴れにくい。
- 印刷したボードのマスを実測で補正していない (100mm バーの確認で済ませた)。
  マスの寸法がずれていると、焦点距離には影響しないが、距離の推定に比例した誤差が出る。

## テスト

```bash
colcon test --packages-select fourth_camera && colcon test-result --verbose
```

## 決め打ちの値・制約

- **カメラ姿勢の二重定義**: シミュレーションのカメラ姿勢 (高さ 1.0 m, ピッチ 0.3 rad) は
  `worlds/camera_world.sdf` の `<pose>` と `launch/sim.launch.py` の `world_to_camera_tf` の
  両方に書いてある。片方を変えたら必ずもう片方も変えること。
- **シミュレーションのカメラ内部パラメータ** は実機に合わせて 640x480 / 30 fps /
  水平画角 52.2° (0.911 rad, 校正結果から算出) にしている。Gazebo の fx=653.3 で、実機の 653.7 とほぼ一致。
  ただし **レンズ歪みはシミュレーションしていない**、また Gazebo の画素は正方形 (fx=fy) で
  主点は画像中心固定。実機を再校正したら SDF の `horizontal_fov` も更新すること。
- **実機のフレームレート**: 実機カメラは YUYV 640x480 で 30 fps を申告するが、室内照明では
  実測 約16 fps だった (自動露光で露光時間が伸びるためと推測)。MJPG 1280x720 は 約17 fps。
- **キャリブレーション**: `real.launch.py` は既定で `config/usb_camera_calibration.yaml` を読む。
  `camera_info_file:=''` を指定すると、`CameraInfo` は幅・高さ以外がすべて 0 の未校正データになる。
  校正値は 640x480 専用。解像度を変えたら再校正が必要。
- **実機ドライバの QoS は reliable (depth 5)**: best-effort だと、`cameracalibrator` のように
  起動時に配信元が見つからず reliable で購読したノードとつながらない。reliable で配信すれば
  reliable / best-effort どちらの購読側ともつながる。
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

- [ ] 露光を固定してブレを減らしたうえで再校正する (現状 RMS 0.80 px。目標 0.5 px 以下)。
      ボードの傾きを 45° 程度まで増やすと焦点距離の精度も上がる
- [ ] 必要ならシミュレーションのカメラにもレンズ歪み (`<distortion>`) を入れる
- [ ] 実機用の色しきい値のチューニング (または実行時に調整できるよう動的パラメータ対応)
- [ ] 実際にやりたい画像処理の内容に合わせて検出ノードを置き換え / 追加する
      (現在の色ブロブ検出は動作確認用の雛形)
- [ ] シミュレーションで対象物を自動で動かす仕組み (現在は GUI で手動ドラッグ)
- [ ] 露光・ゲイン等の V4L2 コントロールをパラメータ化
