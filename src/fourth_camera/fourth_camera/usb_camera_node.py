"""V4L2 (UVC) USB camera driver.

Publishes the same interface as the Gazebo camera bridge so downstream
nodes do not need to know whether they run in simulation or on hardware:
  image_raw     (sensor_msgs/Image, bgr8)
  camera_info   (sensor_msgs/CameraInfo)
"""

import threading

import cv2
import rclpy
import yaml
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image


def load_camera_info(path):
    """Load a ROS camera calibration YAML (camera_calibration output format)."""
    with open(path) as f:
        calib = yaml.safe_load(f)
    info = CameraInfo()
    info.width = calib['image_width']
    info.height = calib['image_height']
    info.distortion_model = calib.get('distortion_model', 'plumb_bob')
    info.d = [float(v) for v in calib['distortion_coefficients']['data']]
    info.k = [float(v) for v in calib['camera_matrix']['data']]
    info.r = [float(v) for v in calib['rectification_matrix']['data']]
    info.p = [float(v) for v in calib['projection_matrix']['data']]
    return info


class UsbCameraNode(Node):

    def __init__(self):
        super().__init__('usb_camera')
        self.device = self.declare_parameter('device', '/dev/video0').value
        self.width = self.declare_parameter('width', 640).value
        self.height = self.declare_parameter('height', 480).value
        self.fps = self.declare_parameter('fps', 30.0).value
        self.pixel_format = self.declare_parameter('pixel_format', 'YUYV').value
        self.frame_id = self.declare_parameter('frame_id', 'camera_optical_frame').value
        camera_info_file = self.declare_parameter('camera_info_file', '').value

        self.camera_info = CameraInfo()
        if camera_info_file:
            self.camera_info = load_camera_info(camera_info_file)
            self.get_logger().info(f'Loaded calibration: {camera_info_file}')
        else:
            self.get_logger().warn('camera_info_file not set; publishing uncalibrated CameraInfo')

        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise RuntimeError(f'Cannot open camera device {self.device}')
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.pixel_format))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        actual = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                  int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                  self.cap.get(cv2.CAP_PROP_FPS))
        self.get_logger().info(
            f'Opened {self.device}: {actual[0]}x{actual[1]} @ {actual[2]:.1f} fps')
        if (actual[0], actual[1]) != (self.width, self.height):
            self.get_logger().warn(
                f'Requested {self.width}x{self.height}, device gave {actual[0]}x{actual[1]}')

        self.bridge = CvBridge()
        self.image_pub = self.create_publisher(Image, 'image_raw', qos_profile_sensor_data)
        self.info_pub = self.create_publisher(CameraInfo, 'camera_info', qos_profile_sensor_data)

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        # cap.read() blocks until the next frame, so the device paces this loop.
        while self._running and rclpy.ok():
            ok, frame = self.cap.read()
            if not ok:
                self.get_logger().warn('Frame grab failed', throttle_duration_sec=2.0)
                continue
            stamp = self.get_clock().now().to_msg()
            img = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            img.header.stamp = stamp
            img.header.frame_id = self.frame_id
            self.camera_info.header = img.header
            if not self.camera_info.width:
                self.camera_info.width = frame.shape[1]
                self.camera_info.height = frame.shape[0]
            self.image_pub.publish(img)
            self.info_pub.publish(self.camera_info)

    def destroy_node(self):
        self._running = False
        self._thread.join(timeout=1.0)
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UsbCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
