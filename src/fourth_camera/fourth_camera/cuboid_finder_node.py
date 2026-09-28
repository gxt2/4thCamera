"""Search for a known cuboid and signal it with an indicator.

Subscribes:  image_raw          (sensor_msgs/Image)
             camera_info        (sensor_msgs/CameraInfo, for the distance estimate)
Publishes:   target_found       (std_msgs/Bool, latched: transient_local)
             detections         (vision_msgs/Detection2DArray, pixel coordinates)
             image_indicator    (sensor_msgs/Image, bgr8, image + indicator lamp)
"""

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

from fourth_camera.cuboid_detector import (
    Debouncer, draw_indicator, estimate_distance, find_cuboids, touches_border)


class CuboidFinderNode(Node):

    def __init__(self):
        super().__init__('cuboid_finder')
        self.label = self.declare_parameter('label', 'blue_cuboid').value
        self.hsv_lower = list(self.declare_parameter('hsv_lower', [85, 80, 40]).value)
        self.hsv_upper = list(self.declare_parameter('hsv_upper', [130, 255, 255]).value)
        self.min_area = float(self.declare_parameter('min_area', 300.0).value)
        self.min_aspect = float(self.declare_parameter('min_aspect', 2.0).value)
        self.max_aspect = float(self.declare_parameter('max_aspect', 6.0).value)
        self.min_fill = float(self.declare_parameter('min_fill', 0.7).value)
        self.length_m = float(self.declare_parameter('length_m', 0.16).value)
        self.debounce = Debouncer(self.declare_parameter('on_frames', 3).value,
                                  self.declare_parameter('off_frames', 10).value)

        self.fx = 0.0
        self.bridge = CvBridge()
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.found_pub = self.create_publisher(Bool, 'target_found', latched)
        self.det_pub = self.create_publisher(Detection2DArray, 'detections', 10)
        self.img_pub = self.create_publisher(Image, 'image_indicator', qos_profile_sensor_data)
        self.create_subscription(CameraInfo, 'camera_info', self.on_info, qos_profile_sensor_data)
        self.create_subscription(Image, 'image_raw', self.on_image, qos_profile_sensor_data)
        self.found_pub.publish(Bool(data=False))

    def on_info(self, msg):
        self.fx = msg.k[0]

    def on_image(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        accepted, rejected = find_cuboids(
            frame, self.hsv_lower, self.hsv_upper, self.min_area,
            self.min_aspect, self.max_aspect, self.min_fill)

        was_found = self.debounce.state
        found = self.debounce.update(bool(accepted))
        if found != was_found:
            self.found_pub.publish(Bool(data=found))
            self.get_logger().info('TARGET FOUND' if found else 'target lost')

        distance = None
        # A cut-off object looks shorter, which would overestimate closeness.
        if accepted and self.fx > 0 and not touches_border(accepted[0], frame.shape):
            distance = estimate_distance(accepted[0].long_px, self.fx, self.length_m)

        out = Detection2DArray(header=msg.header)
        for k in accepted:
            det = Detection2D(header=msg.header)
            det.bbox.center.position.x = k.cx
            det.bbox.center.position.y = k.cy
            det.bbox.center.theta = k.angle_deg
            det.bbox.size_x = k.long_px
            det.bbox.size_y = k.short_px
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = self.label
            # No classifier: score is how well the blob fills its rectangle.
            hyp.hypothesis.score = k.fill
            det.results.append(hyp)
            out.detections.append(det)
        self.det_pub.publish(out)

        if self.img_pub.get_subscription_count() > 0:
            img = self.bridge.cv2_to_imgmsg(
                draw_indicator(frame, found, accepted, rejected, distance), encoding='bgr8')
            img.header = msg.header
            self.img_pub.publish(img)


def main(args=None):
    rclpy.init(args=args)
    node = CuboidFinderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
