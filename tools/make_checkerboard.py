#!/usr/bin/env python3
"""Generate a printable A4 checkerboard PDF for camera calibration (no dependencies).

Usage: make_checkerboard.py [--cols 8] [--rows 6] [--square-mm 25] [-o checkerboard.pdf]
--cols/--rows are INNER corner counts (what camera_calibration's --size expects).
"""

import argparse

MM = 72.0 / 25.4  # PDF points per mm
A4_LANDSCAPE = (297.0, 210.0)


def build_content(cols, rows, sq, page_w, page_h):
    nx, ny = cols + 1, rows + 1  # squares
    board_w, board_h = nx * sq, ny * sq
    if board_w > page_w - 20 or board_h > page_h - 30:
        raise SystemExit(f'Board {board_w}x{board_h} mm does not fit on A4 with margins')
    x0 = (page_w - board_w) / 2
    y0 = (page_h - board_h) / 2 + 5  # leave room for the label/scale at the bottom

    ops = ['0 g']
    for j in range(ny):
        for i in range(nx):
            if (i + j) % 2 == 0:
                ops.append(f'{(x0 + i * sq) * MM:.3f} {(y0 + j * sq) * MM:.3f} '
                           f'{sq * MM:.3f} {sq * MM:.3f} re f')
    # 100 mm scale bar to verify the printer did not rescale
    by = 8
    ops.append(f'{x0 * MM:.3f} {by * MM:.3f} {100 * MM:.3f} {1 * MM:.3f} re f')
    label = (f'{cols}x{rows} inner corners, {sq:g} mm squares. '
             f'Print at 100% (actual size). Bar above = 100 mm.')
    ops.append(f'BT /F1 9 Tf {x0 * MM:.3f} {(by - 5) * MM:.3f} Td ({label}) Tj ET')
    return '\n'.join(ops).encode()


def write_pdf(path, content, page_w, page_h):
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w * MM:.3f} {page_h * MM:.3f}] '
         f'/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>').encode(),
        b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    out = bytearray(b'%PDF-1.4\n')
    offsets = []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % n + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for off in offsets:
        out += b'%010d 00000 n \n' % off
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xref)
    with open(path, 'wb') as f:
        f.write(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cols', type=int, default=8, help='inner corners horizontally')
    p.add_argument('--rows', type=int, default=6, help='inner corners vertically')
    p.add_argument('--square-mm', type=float, default=25.0)
    p.add_argument('-o', '--output', default='checkerboard.pdf')
    a = p.parse_args()
    w, h = A4_LANDSCAPE
    write_pdf(a.output, build_content(a.cols, a.rows, a.square_mm, w, h), w, h)
    print(f'Wrote {a.output}: {a.cols}x{a.rows} inner corners, {a.square_mm:g} mm squares')


if __name__ == '__main__':
    main()
