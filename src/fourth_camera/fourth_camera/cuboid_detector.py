"""ROS-independent detection of a colored cuboid of known size (unit-testable).

A 16 x 5 x 4 cm stick-shaped box seen from most viewpoints projects to an
elongated, roughly rectangular blob. Candidates are color blobs whose minimum-area
rectangle has a long/short aspect within [min_aspect, max_aspect] and which fill
that rectangle well (fill_ratio), which rejects cubes and irregular blue things.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from fourth_camera.color_detector import make_mask


@dataclass
class Cuboid:
    cx: float
    cy: float
    long_px: float
    short_px: float
    angle_deg: float
    fill: float
    box: np.ndarray  # 4x2 corner points (int)

    @property
    def aspect(self):
        return self.long_px / max(self.short_px, 1e-6)


def find_cuboids(bgr, hsv_lower, hsv_upper, min_area=300.0,
                 min_aspect=2.0, max_aspect=6.0, min_fill=0.7):
    """Return (accepted, rejected) candidate lists, accepted sorted by size."""
    mask = make_mask(bgr, hsv_lower, hsv_upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    accepted, rejected = [], []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        (cx, cy), (w, h), angle = cv2.minAreaRect(c)
        long_px, short_px = max(w, h), min(w, h)
        fill = area / max(w * h, 1e-6)
        box = cv2.boxPoints(((cx, cy), (w, h), angle)).astype(int)
        cand = Cuboid(cx, cy, long_px, short_px, angle, fill, box)
        if min_aspect <= cand.aspect <= max_aspect and fill >= min_fill:
            accepted.append(cand)
        else:
            rejected.append(cand)
    accepted.sort(key=lambda k: k.long_px * k.short_px, reverse=True)
    return accepted, rejected


def touches_border(cuboid, shape, margin=3):
    """True if the rectangle reaches the image edge (object likely cut off)."""
    h, w = shape[:2]
    xs, ys = cuboid.box[:, 0], cuboid.box[:, 1]
    return xs.min() < margin or ys.min() < margin or xs.max() >= w - margin or ys.max() >= h - margin


def estimate_distance(long_px, fx, length_m):
    """Pinhole range estimate, valid when the long edge is roughly parallel to the image."""
    return fx * length_m / long_px if long_px > 0 else float('nan')


class Debouncer:
    """Found after `on_frames` consecutive hits, lost after `off_frames` consecutive misses."""

    def __init__(self, on_frames=3, off_frames=10):
        self.on_frames, self.off_frames = on_frames, off_frames
        self.state = False
        self._hits = self._misses = 0

    def update(self, detected):
        if detected:
            self._hits += 1
            self._misses = 0
            if self._hits >= self.on_frames:
                self.state = True
        else:
            self._misses += 1
            self._hits = 0
            if self._misses >= self.off_frames:
                self.state = False
        return self.state


def draw_indicator(bgr, found, accepted, rejected, distance_m=None):
    out = bgr.copy()
    for k in rejected:
        cv2.drawContours(out, [k.box], 0, (128, 128, 128), 1)
    for k in accepted:
        cv2.drawContours(out, [k.box], 0, (0, 255, 0), 2)
    if accepted and distance_m is not None and np.isfinite(distance_m):
        k = accepted[0]
        x, y = k.box[:, 0].min(), k.box[:, 1].min()
        cv2.putText(out, f'~{distance_m * 100:.0f} cm', (int(x), max(int(y) - 8, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    h, w = out.shape[:2]
    color = (0, 200, 0) if found else (80, 80, 80)
    label = 'FOUND' if found else 'SEARCHING'
    cv2.rectangle(out, (w - 190, 8), (w - 8, 58), (0, 0, 0), -1)
    cv2.circle(out, (w - 165, 33), 18, color, -1)
    cv2.circle(out, (w - 165, 33), 18, (255, 255, 255), 2)
    cv2.putText(out, label, (w - 140, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    if found:
        cv2.rectangle(out, (0, 0), (w - 1, h - 1), (0, 200, 0), 6)
    return out
