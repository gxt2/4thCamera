import cv2
import numpy as np

from fourth_camera.cuboid_detector import (
    Debouncer, estimate_distance, find_cuboids, touches_border)

BLUE_LO, BLUE_HI = [85, 80, 40], [130, 255, 255]
BLUE = (200, 120, 0)  # BGR, H~100


def rotated_rect(img, center, size, angle, color):
    box = cv2.boxPoints((center, size, angle)).astype(int)
    cv2.fillPoly(img, [box], color)


def test_accepts_elongated_box_at_any_angle():
    for angle in (0, 30, 75):
        img = np.zeros((480, 640, 3), np.uint8)
        rotated_rect(img, (320, 240), (160, 45), angle, BLUE)  # aspect ~3.6
        acc, _ = find_cuboids(img, BLUE_LO, BLUE_HI)
        assert len(acc) == 1, angle
        assert abs(acc[0].long_px - 160) < 6


def test_rejects_cube_and_other_colors():
    img = np.zeros((480, 640, 3), np.uint8)
    rotated_rect(img, (150, 150), (100, 100), 20, BLUE)             # cube face: aspect 1
    rotated_rect(img, (450, 300), (160, 45), 0, (0, 0, 255))        # red stick
    acc, rej = find_cuboids(img, BLUE_LO, BLUE_HI)
    assert acc == []
    assert len(rej) == 1


def test_rejects_irregular_blob():
    img = np.zeros((480, 640, 3), np.uint8)
    # L shape: elongated bounding rect but poorly filled
    cv2.rectangle(img, (100, 100), (300, 130), BLUE, -1)
    cv2.rectangle(img, (100, 100), (130, 300), BLUE, -1)
    acc, _ = find_cuboids(img, BLUE_LO, BLUE_HI)
    assert acc == []


def test_distance_estimate():
    assert abs(estimate_distance(200, 650.0, 0.16) - 0.52) < 1e-9


def test_debouncer_hysteresis():
    d = Debouncer(on_frames=3, off_frames=2)
    assert [d.update(x) for x in (1, 1, 0, 1, 1, 1, 0, 1, 0, 0)] == \
        [False, False, False, False, False, True, True, True, True, False]


def test_touches_border():
    img = np.zeros((480, 640, 3), np.uint8)
    rotated_rect(img, (320, 240), (160, 45), 0, BLUE)
    rotated_rect(img, (40, 400), (160, 45), 0, BLUE)  # cut off at the left edge
    acc, _ = find_cuboids(img, BLUE_LO, BLUE_HI)
    centered = min(acc, key=lambda k: abs(k.cx - 320))
    edge = max(acc, key=lambda k: abs(k.cx - 320))
    assert not touches_border(centered, img.shape)
    assert touches_border(edge, img.shape)
