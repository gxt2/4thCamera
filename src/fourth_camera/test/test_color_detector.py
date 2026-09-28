import numpy as np

from fourth_camera.color_detector import detect_blobs

RED_LO, RED_HI = [170, 120, 70], [10, 255, 255]


def test_detects_red_square():
    img = np.zeros((240, 320, 3), np.uint8)
    img[100:140, 50:90] = (0, 0, 255)  # BGR red, 40x40
    blobs = detect_blobs(img, RED_LO, RED_HI)
    assert len(blobs) == 1
    b = blobs[0]
    assert abs(b.cx - 70) <= 1 and abs(b.cy - 120) <= 1
    assert b.width == 40 and b.height == 40


def test_ignores_other_colors_and_small_blobs():
    img = np.zeros((240, 320, 3), np.uint8)
    img[10:60, 10:60] = (255, 0, 0)   # blue
    img[200:205, 200:205] = (0, 0, 255)  # red but tiny
    assert detect_blobs(img, RED_LO, RED_HI, min_area=100) == []


def test_sorted_by_area():
    img = np.zeros((240, 320, 3), np.uint8)
    img[10:30, 10:30] = (0, 0, 255)
    img[100:180, 150:230] = (0, 0, 255)
    blobs = detect_blobs(img, RED_LO, RED_HI)
    assert len(blobs) == 2
    assert blobs[0].area > blobs[1].area
