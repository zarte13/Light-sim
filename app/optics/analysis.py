from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import numpy as np

from app.optics.vec2 import Vec2


@dataclass(frozen=True)
class RayLine:
    p0: Vec2
    d: Vec2  # assumed normalized


def estimate_focus(lines: Iterable[RayLine]) -> Optional[Tuple[Vec2, float]]:
    """Least-squares intersection of 2D lines.

    Returns (focus_point, spot_rms) where spot_rms is RMS perpendicular distance.
    """
    lines = list(lines)
    if len(lines) < 2:
        return None

    A = np.zeros((2, 2), dtype=float)
    b = np.zeros((2,), dtype=float)

    for ln in lines:
        u = np.array([ln.d.x, ln.d.y], dtype=float)
        u /= np.linalg.norm(u) + 1e-15
        P = np.eye(2) - np.outer(u, u)  # projects onto normal space
        p0 = np.array([ln.p0.x, ln.p0.y], dtype=float)
        A += P
        b += P @ p0

    det = np.linalg.det(A)
    if abs(det) < 1e-12:
        return None

    p = np.linalg.solve(A, b)
    focus = Vec2(float(p[0]), float(p[1]))

    # RMS perpendicular distance to focus
    ds = []
    for ln in lines:
        u = np.array([ln.d.x, ln.d.y], dtype=float)
        u /= np.linalg.norm(u) + 1e-15
        p0 = np.array([ln.p0.x, ln.p0.y], dtype=float)
        pf = np.array([focus.x, focus.y], dtype=float)
        # perpendicular distance from point to line
        w = pf - p0
        perp = w - (w @ u) * u
        ds.append(float(np.linalg.norm(perp)))
    spot_rms = float(np.sqrt(np.mean(np.square(ds)))) if ds else 0.0

    return focus, spot_rms


def intensity_profile_at_x(
    lines: Iterable[RayLine],
    detector_x: float,
    bins: int = 200,
) -> Optional[dict]:
    """Compute a 1D histogram of ray intersections with the vertical line x=detector_x."""
    ys = []
    for ln in lines:
        dx = ln.d.x
        if abs(dx) < 1e-12:
            continue
        t = (detector_x - ln.p0.x) / dx
        if t <= 0:
            continue
        ys.append(ln.p0.y + t * ln.d.y)

    if len(ys) < 10:
        return None

    y = np.array(ys, dtype=float)
    y05, y95 = np.percentile(y, [5, 95])
    pad = max(1e-6, 0.1 * (y95 - y05))
    y_min = float(y05 - pad)
    y_max = float(y95 + pad)
    counts, edges = np.histogram(y, bins=bins, range=(y_min, y_max))
    peak_idx = int(np.argmax(counts))
    peak_y = float(0.5 * (edges[peak_idx] + edges[peak_idx + 1]))

    return {
        "detector": {"x": float(detector_x), "y_min": y_min, "y_max": y_max, "bins": int(bins)},
        "counts": counts.tolist(),
        "edges": edges.tolist(),
        "peak": {"y": peak_y, "count": int(counts[peak_idx])},
        "samples": int(len(ys)),
    }


def _ys_at_x(lines: Iterable[RayLine], detector_x: float) -> list[float]:
    ys: list[float] = []
    for ln in lines:
        dx = ln.d.x
        if abs(dx) < 1e-12:
            continue
        t = (detector_x - ln.p0.x) / dx
        if t <= 0:
            continue
        ys.append(ln.p0.y + t * ln.d.y)
    return ys


def best_focus_scan(
    lines: Iterable[RayLine],
    x_min: float,
    x_max: float,
    steps: int = 200,
    min_samples: int = 30,
) -> Optional[Tuple[Vec2, float]]:
    """Find best focus by scanning detector planes and minimizing spot RMS.

    Returns (focus_point, spot_rms). This remains meaningful even with aberrations,
    where rays do not intersect at a single point.
    """

    if steps < 2:
        return None

    best = None
    for i in range(steps):
        x = float(x_min + (x_max - x_min) * (i / (steps - 1)))
        ys = _ys_at_x(lines, detector_x=x)
        if len(ys) < min_samples:
            continue
        y = np.array(ys, dtype=float)
        y_mean = float(np.mean(y))
        rms = float(np.sqrt(np.mean(np.square(y - y_mean))))
        if best is None or rms < best[1]:
            best = (Vec2(x, y_mean), rms)

    return best

