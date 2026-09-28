#!/usr/bin/env python3
"""Recalibrate from camera_calibration's saved tarball, dropping blurred views.

cameracalibrator keeps every accepted sample, including motion-blurred ones, which
inflates the reprojection error. This script redetects the corners in the saved
images, calibrates, drops views whose RMS error exceeds --max-view-err, calibrates
again, and writes a ROS camera_info YAML.

Usage:
  refine_calibration.py /tmp/calibrationdata.tar.gz -o calibration.yaml \
      [--size 8x6] [--square 0.025] [--max-view-err 1.5] [--camera-name usb_camera]
"""

import argparse
import glob
import os
import tarfile
import tempfile

import cv2
import numpy as np


def detect(files, size):
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)
    corners, shape = [], None
    for f in files:
        g = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        shape = g.shape[::-1]
        ok, c = cv2.findChessboardCorners(
            g, size, flags=cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
        if ok:
            corners.append(cv2.cornerSubPix(g, c, (11, 11), (-1, -1), crit))
    return corners, shape


def calibrate(objp, corners, shape):
    # k3 fixed to 0: same RMS as free k3 on this camera, and extrapolates better at the edges.
    rms, K, D, R, T = cv2.calibrateCamera(
        [objp] * len(corners), corners, shape, None, None, flags=cv2.CALIB_FIX_K3)
    errs = np.array([
        np.sqrt(np.mean(np.sum((cv2.projectPoints(objp, r, t, K, D)[0] - c) ** 2, axis=2)))
        for c, r, t in zip(corners, R, T)])
    return rms, K, D, errs


def fmt(values):
    return '[' + ', '.join(f'{v:.6f}' for v in np.ravel(values)) + ']'


def write_yaml(path, name, shape, K, D, P):
    w, h = shape
    with open(path, 'w') as f:
        f.write(f'image_width: {w}\nimage_height: {h}\ncamera_name: {name}\n')
        f.write(f'camera_matrix:\n  rows: 3\n  cols: 3\n  data: {fmt(K)}\n')
        f.write('distortion_model: plumb_bob\n')
        f.write(f'distortion_coefficients:\n  rows: 1\n  cols: 5\n  data: {fmt(D)}\n')
        f.write(f'rectification_matrix:\n  rows: 3\n  cols: 3\n  data: {fmt(np.eye(3))}\n')
        f.write(f'projection_matrix:\n  rows: 3\n  cols: 4\n  data: {fmt(P)}\n')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('tarball')
    p.add_argument('-o', '--output', required=True)
    p.add_argument('--size', default='8x6', help='inner corners, COLSxROWS')
    p.add_argument('--square', type=float, default=0.025, help='square size [m]')
    p.add_argument('--max-view-err', type=float, default=1.5, help='drop views above this RMS [px]')
    p.add_argument('--camera-name', default='usb_camera')
    a = p.parse_args()

    cols, rows = map(int, a.size.lower().split('x'))
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * a.square

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(a.tarball) as tar:
            tar.extractall(tmp, filter='data')
        files = sorted(glob.glob(os.path.join(tmp, 'left-*.png')))
        corners, shape = detect(files, (cols, rows))
    print(f'Board detected in {len(corners)}/{len(files)} images')

    rms, K, D, errs = calibrate(objp, corners, shape)
    print(f'All views:  RMS {rms:.3f} px')
    kept = [c for c, e in zip(corners, errs) if e < a.max_view_err]
    rms, K, D, errs = calibrate(objp, kept, shape)
    print(f'Kept {len(kept)} views (< {a.max_view_err} px): RMS {rms:.3f} px')

    # Same as camera_calibration: alpha=0 (only valid pixels) for the rectified projection.
    newK, _ = cv2.getOptimalNewCameraMatrix(K, D, shape, 0.0)
    P = np.hstack([newK, np.zeros((3, 1))])
    write_yaml(a.output, a.camera_name, shape, K, D, P)

    hfov = np.degrees(2 * np.arctan(shape[0] / 2 / K[0, 0]))
    vfov = np.degrees(2 * np.arctan(shape[1] / 2 / K[1, 1]))
    print(f'fx={K[0, 0]:.1f} fy={K[1, 1]:.1f} cx={K[0, 2]:.1f} cy={K[1, 2]:.1f}')
    print(f'D={np.ravel(D).round(4).tolist()}')
    print(f'HFOV={hfov:.1f} deg ({np.radians(hfov):.3f} rad)  VFOV={vfov:.1f} deg')
    print(f'Wrote {a.output}')


if __name__ == '__main__':
    main()
