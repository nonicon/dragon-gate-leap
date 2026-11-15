#!/usr/bin/env python3
"""Dragon Gate Leap — procedural poster for make.fun ai-excited-01.

A colossal golden koi leaps out of the sea along a great diagonal arc, and
at the top of its leap it is becoming a dragon: branching horns, a flowing
mane, long whiskers, an open roaring mouth. Below it a tiny red torii gate
stands in the waves. Behind it a huge full moon hangs in a burning
orange-to-indigo night sky, with cherry blossom petals drifting through the
air. One big diagonal, one focal point, bold flat-poster craft with a soft
glow — built to read at 300px and to surprise.

Pure Python standard library only (no Pillow, no numpy): the canvas is a
raw RGB bytearray, shapes are rasterised by hand, and the PNG is encoded
with zlib. Deterministic (fixed seed), so two runs write identical bytes.

Usage:  python3 generate.py            # writes entry.png next to this file
        python3 main.py                # entry point; writes to $MAKEFUN_OUTPUT_DIR
"""

import math
import os
import random
import struct
import zlib

W = H = 1024
RNG = random.Random(20261116)

# ---------------------------------------------------------------- palette ---
SKY_TOP = (8, 12, 44)
SKY_MID = (46, 24, 88)
SKY_LOW = (128, 40, 96)
HORIZON = (255, 112, 54)
MOON_DISC = (255, 236, 175)
MOON_RIM = (255, 246, 208)
MOON_CRATER = (232, 202, 138)
GLOW_COL = (255, 214, 130)
GOLD = (255, 178, 34)
GOLD_DEEP = (232, 110, 18)
GOLD_DARK = (176, 66, 8)
BELLY = (255, 234, 170)
KOI_RED = (214, 38, 38)
KOI_WHITE = (255, 246, 232)
MANE_RED = (190, 28, 20)
MANE_ORANGE = (255, 96, 20)
HORN = (255, 240, 190)
INK = (40, 16, 4)
WATER_DEEP = (8, 38, 70)
WATER_MID = (16, 62, 98)
WATER_TOP = (30, 96, 140)
FOAM = (198, 240, 255)
TORII = (206, 36, 32)
TORII_DARK = (140, 20, 20)
PETAL = (255, 179, 198)
PETAL_DARK = (244, 138, 170)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def bezier(p0, p1, p2, p3, n=120):
    """Sample a cubic bezier curve into a list of (x, y) points."""
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0]
             + 3 * mt * t * t * p2[0] + t ** 3 * p3[0])
        y = (mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1]
             + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])
        pts.append((x, y))
    return pts


def bezier_tangent(p0, p1, p2, p3, t):
    mt = 1 - t
    dx = (3 * mt * mt * (p1[0] - p0[0]) + 6 * mt * t * (p2[0] - p1[0])
          + 3 * t * t * (p3[0] - p2[0]))
    dy = (3 * mt * mt * (p1[1] - p0[1]) + 6 * mt * t * (p2[1] - p1[1])
          + 3 * t * t * (p3[1] - p2[1]))
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


class Canvas:
    def __init__(self):
        self.buf = bytearray(W * H * 3)

    def hspan(self, y, x0, x1, c):
        """Fill one horizontal run of pixels with an opaque colour."""
        if y < 0 or y >= H:
            return
        x0 = max(0, int(math.floor(x0)))
        x1 = min(W - 1, int(math.ceil(x1)))
        if x1 < x0:
            return
        i = (y * W + x0) * 3
        n = x1 - x0 + 1
        self.buf[i:i + n * 3] = bytes(c) * n

    def vgrad(self, stops):
        """Fill the whole canvas with a vertical gradient."""
        for y in range(H):
            t = y / (H - 1)
            for i in range(len(stops) - 1):
                p0, c0 = stops[i]
                p1, c1 = stops[i + 1]
                if p0 <= t <= p1:
                    f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                    col = lerp(c0, c1, f)
                    break
            else:
                col = stops[-1][1]
            i = y * W * 3
            self.buf[i:i + W * 3] = bytes(col) * W

    def circle(self, cx, cy, r, c):
        r = int(r)
        if r <= 0:
            return
        for y in range(max(0, int(cy) - r), min(H - 1, int(cy) + r) + 1):
            dy = y - cy
            dx = math.sqrt(max(0.0, r * r - dy * dy))
            self.hspan(y, cx - dx, cx + dx, c)

    def ellipse(self, cx, cy, rx, ry, c):
        rx = int(rx)
        ry = int(ry)
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, int(cy) - ry), min(H - 1, int(cy) + ry) + 1):
            dy = (y - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            self.hspan(y, cx - dx, cx + dx, c)

    def poly(self, pts, c):
        """Fill a polygon with the scanline rule."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.ceil(min(ys))))
        y1 = min(H - 1, int(math.floor(max(ys))))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hspan(y, xs[i], xs[i + 1], c)

    def thick_path(self, pts, width, c):
        """Draw a polyline as a chain of overlapping discs."""
        r = max(1.0, width / 2.0)
        step = max(1.0, r * 0.7)
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(seg / step))
            for j in range(n + 1):
                t = j / n
                self.circle(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, c)

    def glow(self, cx, cy, r, c, a0):
        """Soft radial glow: per-pixel alpha blend, strongest at the centre."""
        buf = self.buf
        for y in range(max(0, int(cy) - r), min(H - 1, int(cy) + r) + 1):
            dy = y - cy
            dx = math.sqrt(max(0.0, r * r - dy * dy))
            x0 = max(0, int(cx - dx))
            x1 = min(W - 1, int(cx + dx))
            for x in range(x0, x1 + 1):
                d = math.hypot(x - cx, dy) / r
                if d >= 1.0:
                    continue
                a = int(a0 * (1.0 - d) * (1.0 - d))
                if a <= 0:
                    continue
                i = (y * W + x) * 3
                buf[i] = (c[0] * a + buf[i] * (255 - a)) // 255
                buf[i + 1] = (c[1] * a + buf[i + 1] * (255 - a)) // 255
                buf[i + 2] = (c[2] * a + buf[i + 2] * (255 - a)) // 255


# ------------------------------------------------------------------- sky -----
def draw_sky(cv):
    cv.vgrad([(0.0, SKY_TOP), (0.42, SKY_MID), (0.70, SKY_LOW),
              (0.88, HORIZON), (1.0, (255, 140, 70))])
    # stars in the upper sky
    for _ in range(230):
        x = RNG.uniform(0, W)
        y = RNG.uniform(0, H * 0.62)
        if math.hypot(x - 715, y - 215) < 175:
            continue
        r = RNG.uniform(0.7, 2.1)
        a = RNG.randint(110, 255)
        col = (a, a, min(255, a + 20))
        cv.circle(x, y, r, col)
    # a few four-point sparkles
    for _ in range(14):
        x = RNG.uniform(40, W - 40)
        y = RNG.uniform(30, H * 0.55)
        if math.hypot(x - 715, y - 215) < 185:
            continue
        L = RNG.uniform(6, 13)
        w = 1.6
        cv.thick_path([(x - L, y), (x + L, y)], w, (255, 255, 240))
        cv.thick_path([(x, y - L), (x, y + L)], w, (255, 255, 240))


def draw_moon(cv):
    # halo, then rim, then disc, then craters
    cv.glow(715, 215, 380, GLOW_COL, 150)
    cv.circle(715, 215, 148, MOON_RIM)
    cv.circle(715, 215, 140, MOON_DISC)
    for (cx, cy, r) in [(672, 178, 20), (748, 252, 26), (700, 258, 13),
                        (762, 178, 11), (688, 212, 9)]:
        cv.circle(cx, cy, r, MOON_CRATER)
    # a comet streaking past, top-left of the moon
    pts = bezier((150, 96), (220, 130), (300, 168), (372, 210), 40)
    for i, (x, y) in enumerate(pts):
        t = i / (len(pts) - 1)
        cv.circle(x, y, 1.2 + 3.4 * t, (255, 244, 200))
    cv.circle(372, 210, 5.5, (255, 252, 230))
    cv.thick_path([(372, 210), (392, 222)], 2.0, (255, 252, 230))


# ------------------------------------------------------------------ water ----
def draw_water(cv):
    # sea from y=830 down, darker at the bottom
    for y in range(830, H):
        t = (y - 830) / (H - 830)
        col = lerp(WATER_TOP, WATER_DEEP, t)
        i = y * W * 3
        cv.buf[i:i + W * 3] = bytes(col) * W
    # rolling wave backs
    for (cy, rx, col) in [(852, 560, WATER_MID), (905, 640, (14, 52, 86)),
                          (962, 720, WATER_DEEP)]:
        cv.ellipse(512, cy, rx, 46, col)
    # white foam crests, scattered along wavy lines (not in neat rows)
    for base_y, amp in [(846, 7), (898, 8), (956, 9)]:
        x = 0
        while x < W:
            y = (base_y + amp * math.sin(x * 0.011 + base_y)
                 + RNG.uniform(-9, 9))
            r = RNG.uniform(2.5, 6.5)
            cv.circle(x, y, r, FOAM)
            if RNG.random() < 0.4:
                cv.circle(x + RNG.uniform(-14, 14), y + RNG.uniform(-7, 7),
                          RNG.uniform(1.5, 3.5), FOAM)
            x += RNG.uniform(20, 40)
    # spray where the tail bursts out of the sea
    for _ in range(46):
        a = RNG.uniform(-math.pi, 0)
        d = RNG.uniform(8, 95)
        x = 212 + d * math.cos(a)
        y = 876 + d * math.sin(a) * 0.55
        cv.circle(x, y, RNG.uniform(2.0, 7.0), FOAM)


def draw_torii(cv):
    """A tiny red torii gate standing in the waves, right of the tail."""
    x0, y0 = 438, 916  # gate centre, waterline
    s = 1.15
    def X(dx):
        return x0 + dx * s
    def Y(dy):
        return y0 + dy * s
    # reflection streaks
    for dx in (-26, -8, 10, 28):
        cv.thick_path([(X(dx), Y(34)), (X(dx + 4), Y(92))], 5, TORII_DARK)
    # pillars
    cv.poly([(X(-34), Y(34)), (X(-26), Y(34)), (X(-24), Y(-34)),
             (X(-32), Y(-34))], TORII)
    cv.poly([(X(34), Y(34)), (X(26), Y(34)), (X(24), Y(-34)),
             (X(32), Y(-34))], TORII)
    # lower tie beam
    cv.poly([(X(-30), Y(6)), (X(30), Y(6)), (X(30), Y(-2)),
             (X(-30), Y(-2))], TORII_DARK)
    # upper lintel, gently curved, with black cap
    cv.poly([(X(-52), Y(-30)), (X(52), Y(-30)), (X(48), Y(-42)),
             (X(-48), Y(-42))], TORII)
    cv.poly([(X(-56), Y(-42)), (X(56), Y(-42)), (X(50), Y(-50)),
             (X(-50), Y(-50))], (24, 12, 12))
    # centre plaque
    cv.poly([(X(-5), Y(-28)), (X(5), Y(-28)), (X(5), Y(-8)),
             (X(-5), Y(-8))], (24, 12, 12))


def draw_petals(cv):
    for _ in range(46):
        x = RNG.uniform(20, W - 20)
        y = RNG.uniform(30, H * 0.85)
        rx = RNG.uniform(6, 13)
        ry = RNG.uniform(4, 8)
        col = PETAL if RNG.random() < 0.6 else PETAL_DARK
        cv.ellipse(x, y, rx, ry, col)
        cv.ellipse(x - rx * 0.25, y - ry * 0.25, rx * 0.45, ry * 0.45,
                   (255, 214, 224))


def tapered_stroke(cv, pts, w0, w1, col):
    """A stroke that narrows from width w0 at its start to w1 at its end."""
    left, right = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        t = i / (n - 1)
        w = w0 + (w1 - w0) * t
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == n - 1:
            dx, dy = x - pts[i - 1][0], y - pts[i - 1][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    cv.poly(left + right[::-1], col)


# ------------------------------------------------------------ koi / dragon ---
SPINE = ((212, 895), (320, 780), (520, 430), (748, 318))


def spine_point(t):
    pts = bezier(*SPINE, 200)
    return pts[min(200, int(t * 200))]


def spine_radius(t):
    return 8 + 54 * (math.sin(math.pi * (0.05 + 0.9 * t)) ** 1.1)


def shrink_poly(pts, f):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return [(cx + (x - cx) * f, cy + (y - cy) * f) for (x, y) in pts]


def draw_tail(cv):
    base = spine_point(0.0)
    tx, ty = bezier_tangent(*SPINE, 0.0)
    bx, by = -tx, -ty  # tail points down-left, back along the spine
    # two flowing lobes, layered deep -> red -> gold
    for scale, col in [(1.0, GOLD_DEEP), (0.82, KOI_RED), (0.6, GOLD)]:
        s = scale
        upper = [base,
                 (base[0] + bx * 95 * s - 18 * s, base[1] + by * 95 * s - 62 * s),
                 (base[0] + bx * 195 * s - 30 * s, base[1] + by * 195 * s - 55 * s),
                 (base[0] + bx * 150 * s + 8 * s, base[1] + by * 150 * s + 12 * s),
                 (base[0] + bx * 62 * s + 22 * s, base[1] + by * 62 * s + 30 * s)]
        lower = [base,
                 (base[0] + bx * 78 * s + 26 * s, base[1] + by * 78 * s + 52 * s),
                 (base[0] + bx * 178 * s + 42 * s, base[1] + by * 178 * s + 118 * s),
                 (base[0] + bx * 128 * s - 6 * s, base[1] + by * 128 * s + 132 * s),
                 (base[0] + bx * 52 * s - 18 * s, base[1] + by * 52 * s + 52 * s)]
        cv.poly(upper, col)
        cv.poly(lower, col)
    # fin rays fanning from the tail base
    for ang in (-0.9, -0.45, 0.0, 0.45, 0.9):
        ex = base[0] + bx * 150 + math.cos(ang) * 60 - math.sin(ang) * 40
        ey = base[1] + by * 150 + math.sin(ang) * 60 + math.cos(ang) * 40
        cv.thick_path([base, (ex, ey)], 2.5, GOLD_DARK)


def draw_koi(cv):
    # ---- fins behind the body -------------------------------------------
    for t, size in [(0.80, 1.0), (0.88, 0.72)]:
        c = spine_point(t)
        tx, ty = bezier_tangent(*SPINE, t)
        nx, ny = -ty, tx  # belly side (down-right)
        fin = [(c[0], c[1]),
               (c[0] - tx * 34 * size + nx * 14, c[1] - ty * 34 * size + ny * 14),
               (c[0] - tx * 128 * size + nx * 96 * size,
                c[1] - ty * 128 * size + ny * 96 * size),
               (c[0] - tx * 66 * size + nx * 138 * size,
                c[1] - ty * 66 * size + ny * 138 * size),
               (c[0] + tx * 34 * size + nx * 78 * size,
                c[1] + ty * 34 * size + ny * 78 * size),
               (c[0] + tx * 48 * size + nx * 22 * size,
                c[1] + ty * 48 * size + ny * 22 * size)]
        cv.poly(fin, GOLD_DEEP)
        cv.poly(shrink_poly(fin, 0.82), GOLD)
    # ---- dorsal spikes along the back ------------------------------------
    spikes = []
    for i in range(7):
        t = 0.32 + i * 0.036
        c = spine_point(t)
        tx, ty = bezier_tangent(*SPINE, t)
        nx, ny = ty, -tx  # back side (up-left)
        r = spine_radius(t)
        spikes.append((c[0] + nx * r * 0.95, c[1] + ny * r * 0.95))
        spikes.append((c[0] + nx * r * 1.38 - tx * 12,
                       c[1] + ny * r * 1.38 - ty * 12))
    cv.poly(spikes, GOLD_DEEP)
    # ---- body: overlapping discs along the spine ------------------------
    samples = bezier(*SPINE, 160)
    for i, (x, y) in enumerate(samples):
        t = i / (len(samples) - 1)
        cv.circle(x, y, spine_radius(t), GOLD)
    # ---- back shading (up-left side) ------------------------------------
    for i, (x, y) in enumerate(samples):
        t = i / (len(samples) - 1)
        tx, ty = bezier_tangent(*SPINE, t)
        nx, ny = ty, -tx
        r = spine_radius(t)
        cv.circle(x + nx * r * 0.52, y + ny * r * 0.52, r * 0.42, GOLD_DEEP)
    # ---- belly (down-right side) -----------------------------------------
    for i, (x, y) in enumerate(samples):
        t = i / (len(samples) - 1)
        tx, ty = bezier_tangent(*SPINE, t)
        nx, ny = -ty, tx
        r = spine_radius(t)
        cv.circle(x + nx * r * 0.5, y + ny * r * 0.5, r * 0.46, BELLY)
    # ---- koi marking bands ----------------------------------------------
    for t, col in [(0.30, KOI_RED), (0.48, KOI_WHITE), (0.66, KOI_RED),
                   (0.82, GOLD_DEEP)]:
        c0 = spine_point(t)
        c1 = spine_point(min(1.0, t + 0.045))
        tx, ty = bezier_tangent(*SPINE, t)
        nx, ny = -ty, tx
        r0 = spine_radius(t) * 1.02
        r1 = spine_radius(min(1.0, t + 0.045)) * 1.02
        cv.poly([(c0[0] + nx * r0, c0[1] + ny * r0),
                 (c0[0] - nx * r0, c0[1] - ny * r0),
                 (c1[0] - nx * r1, c1[1] - ny * r1),
                 (c1[0] + nx * r1, c1[1] + ny * r1)], col)


def draw_head(cv):
    hx, hy = spine_point(1.0)
    ux, uy = bezier_tangent(*SPINE, 1.0)
    vx, vy = -uy, ux  # across: down-right side

    def L(a, b):
        return (hx + ux * 34 + ux * a + vx * b,
                hy + uy * 34 + uy * a + vy * b)

    # ---- mane: flowing strands streaming back along the neck -----------
    for (pts, w0, w1, col) in [
            ([(-30, -20), (-110, -40), (-190, -42), (-262, -28)], 19, 3,
             MANE_RED),
            ([(-28, -6), (-105, -18), (-180, -12), (-246, 4)], 15, 2.5,
             MANE_ORANGE),
            ([(-26, 8), (-100, 2), (-170, 16), (-232, 30)], 12, 2, GOLD)]:
        strand = bezier(L(*pts[0]), L(*pts[1]), L(*pts[2]), L(*pts[3]), 30)
        tapered_stroke(cv, strand, w0, w1, col)
    # ---- head ------------------------------------------------------------
    head = [L(108, 2), L(72, -30), L(18, -38), L(-28, -30), L(-52, -6),
            L(-40, 18), L(0, 30), L(58, 26)]
    cv.poly(head, GOLD)
    # ---- horns: tapered antlers, dark outline then pale core ------------
    for (bx, by, cx, cy, ex, ey, brx, bry) in [
            (-12, -30, -60, -88, -122, -122, -96, -168),
            (6, -34, -38, -96, -96, -138, -64, -176)]:
        stem = bezier(L(bx, by), L(cx, cy), L((cx + ex) / 2, (cy + ey) / 2),
                      L(ex, ey), 30)
        mid = stem[14]
        branch = bezier(mid, (mid[0] - 18, mid[1] - 30),
                        L(brx + 14, bry + 18), L(brx, bry), 18)
        tapered_stroke(cv, stem, 20, 4, GOLD_DARK)
        tapered_stroke(cv, stem, 13, 2.5, HORN)
        tapered_stroke(cv, branch, 11, 2.5, GOLD_DARK)
        tapered_stroke(cv, branch, 7, 1.5, HORN)
    # ---- open mouth -------------------------------------------------------
    mouth = [L(104, 2), L(66, 22), L(22, 28), L(-6, 20), L(28, 8), L(72, 0)]
    cv.poly(mouth, (122, 12, 10))
    cv.ellipse(*L(54, 18), 24, 8, (255, 92, 80))  # tongue
    for (ax, ay) in [(84, 8), (58, 14), (32, 19)]:
        cv.poly([L(ax - 7, ay - 5), L(ax + 7, ay - 5), L(ax, ay + 9)],
                KOI_WHITE)
    # ---- eye + brow -------------------------------------------------------
    cv.circle(*L(28, -16), 13, KOI_WHITE)
    cv.circle(*L(30, -15), 6, INK)
    cv.circle(*L(33, -18), 3.5, (255, 255, 255))
    cv.thick_path([L(6, -30), L(48, -26)], 5, GOLD_DARK)
    # ---- whiskers ---------------------------------------------------------
    for pts in [[(95, 8), (150, 30), (210, 20), (246, 46)],
                [(90, 14), (140, 55), (200, 60), (236, 92)]]:
        cv.thick_path([L(a, b) for (a, b) in bezier(
            L(*pts[0]), L(*pts[1]), L(*pts[2]), L(*pts[3]), 30)], 5, HORN)


def draw_splash(cv):
    for _ in range(30):
        a = RNG.uniform(-math.pi, 0)
        d = RNG.uniform(6, 80)
        x = 212 + d * math.cos(a)
        y = 882 + d * math.sin(a) * 0.5
        cv.circle(x, y, RNG.uniform(2.0, 6.0), FOAM)


# ------------------------------------------------------------------ output ---
def write_png(path, buf):
    raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3])
                   for y in range(H))
    comp = zlib.compress(raw, 6)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def render(out_path):
    cv = Canvas()
    draw_sky(cv)
    draw_moon(cv)
    draw_water(cv)
    draw_torii(cv)
    draw_tail(cv)
    draw_koi(cv)
    draw_head(cv)
    draw_splash(cv)
    draw_petals(cv)
    return write_png(out_path, cv.buf)


if __name__ == "__main__":
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", ".")
    os.makedirs(out, exist_ok=True)
    size = render(os.path.join(out, "entry.png"))
    print(f"entry.png: {W}x{H}, {size} bytes")
