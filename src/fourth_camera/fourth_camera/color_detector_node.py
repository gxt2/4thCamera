"""Color blob detector node.

Subscribes:  image_raw          (sensor_msgs/Image)
Publishes:   detections         (vision_msgs/Detection2DArray, pixel coordinates)
             image_annotated    (sensor_msgs/Image, bgr8)
"""

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

from fourth_camera.color_detector import detect_blobs, draw_blobs


class ColorDetectorNode(Node):

    def __init__(self):
        super().__init__('color_detector')
        self.label = self.declare_parameter('label', 'red').value
        # Default: red (hue wraps around 180).
        self.hsv_lower = list(self.declare_parameter('hsv_lower', [170, 120, 70]).value)
        self.hsv_upper = list(self.declare_parameter('hsv_upper', [10, 255, 255]).value)
        self.min_area = float(self.declare_parameter('min_area', 100.0).value)
        self.max_blobs = self.declare_parameter('max_blobs', 10).value
        self.publish_annotated = self.declare_parameter('publish_annotated', True).value

        self.bridge = CvBridge()
        self.det_pub = self.create_publisher(Detection2DArray, 'detections', 10)
        self.img_pub = self.create_publisher(Image, 'image_annotated', qos_profile_sensor_data)
        self.create_subscription(Image, 'image_raw', self.on_image, qos_profile_sensor_data)

    def on_image(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        blobs = detect_blobs(frame, self.hsv_lower, self.hsv_upper,
                             self.min_area, self.max_blobs)

        out = Detection2DArray(header=msg.header)
        frame_area = float(frame.shape[0] * frame.shape[1])
        for b in blobs:
            det = Detection2D(header=msg.header)
            det.bbox.center.position.x = b.cx
            det.bbox.center.position.y = b.cy
            det.bbox.size_x = b.width
            det.bbox.size_y = b.height
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = self.label
            # No classifier: score is the blob's share of the image area.
            hyp.hypothesis.score = b.area / frame_area
            det.results.append(hyp)
            out.detections.append(det)
        self.det_pub.publish(out)

        if self.publish_annotated and self.img_pub.get_subscription_count() > 0:
            annotated = self.bridge.cv2_to_imgmsg(draw_blobs(frame, blobs), encoding='bgr8')
            annotated.header = msg.header
            self.img_pub.publish(annotated)


def main(args=None):
    rclpy.init(args=args)
    node = ColorDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
