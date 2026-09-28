"""ROS-independent color blob detection (unit-testable)."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Blob:
    cx: float
    cy: float
    width: float
    height: float
    area: float


def make_mask(bgr, hsv_lower, hsv_upper):
    """Threshold in HSV. If hue lower > upper the range wraps around 180 (e.g. red)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lo = np.array(hsv_lower, dtype=np.uint8)
    hi = np.array(hsv_upper, dtype=np.uint8)
    if lo[0] <= hi[0]:
        mask = cv2.inRange(hsv, lo, hi)
    else:
        mask = cv2.inRange(hsv, lo, np.array([179, hi[1], hi[2]], dtype=np.uint8))
        mask |= cv2.inRange(hsv, np.array([0, lo[1], lo[2]], dtype=np.uint8), hi)
    kernel = np.ones((5, 5), np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def detect_blobs(bgr, hsv_lower, hsv_upper, min_area=100.0, max_blobs=10):
    """Return blobs sorted by area (largest first)."""
    mask = make_mask(bgr, hsv_lower, hsv_upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        blobs.append(Blob(x + w / 2.0, y + h / 2.0, float(w), float(h), float(area)))
    blobs.sort(key=lambda b: b.area, reverse=True)
    return blobs[:max_blobs]


def draw_blobs(bgr, blobs, color=(0, 255, 0)):
    out = bgr.copy()
    for b in blobs:
        p1 = (int(b.cx - b.width / 2), int(b.cy - b.height / 2))
        p2 = (int(b.cx + b.width / 2), int(b.cy + b.height / 2))
        cv2.rectangle(out, p1, p2, color, 2)
        cv2.drawMarker(out, (int(b.cx), int(b.cy)), color, cv2.MARKER_CROSS, 12, 2)
    return out
