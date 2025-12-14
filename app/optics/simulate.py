from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

from app.optics.analysis import RayLine, estimate_focus, intensity_profile_at_x
from app.optics.elements import ConicMirror, FresnelThinLens
from app.optics.schema import Scene
from app.optics.transform import Pose2
from app.optics.vec2 import Vec2


def _vec(v) -> Vec2:
    return Vec2(float(v.x), float(v.y))


def simulate_scene(scene: Scene) -> Dict:
    lenses = [
        FresnelThinLens(
            id=l.id,
            pose=Pose2(pos=_vec(l.pos), theta=float(l.theta)),
            f=float(l.f),
            aperture=float(l.aperture),
        )
        for l in scene.lenses
    ]
    mirrors = [
        ConicMirror(
            id=m.id,
            pose=Pose2(pos=_vec(m.pos), theta=float(m.theta)),
            R=float(m.R),
            kappa=float(m.kappa),
            aperture=float(m.aperture),
        )
        for m in scene.mirrors
    ]

    max_bounces = int(scene.settings.max_bounces)
    max_dist = float(scene.settings.max_distance)
    angular_jitter = float(scene.settings.angular_jitter)
    rng = np.random.default_rng(scene.settings.seed)

    rays_out: List[Dict] = []
    outgoing_lines: List[RayLine] = []

    for s in scene.sources:
        if s.ray_count <= 0:
            continue
        origin = _vec(s.pos)
        n = int(s.ray_count)
        for i in range(n):
            ang = (2.0 * math.pi) * (i / n)
            if angular_jitter > 0:
                ang += float(rng.uniform(-angular_jitter, angular_jitter))
            rd = Vec2(math.cos(ang), math.sin(ang)).normalized()
            poly = _trace_one(origin, rd, lenses, mirrors, max_bounces, max_dist)
            rays_out.append({"points": [[p.x, p.y] for p in poly]})

            if len(poly) >= 2:
                p0 = poly[-2]
                p1 = poly[-1]
                d = (p1 - p0).normalized()
                if d.norm() > 0:
                    outgoing_lines.append(RayLine(p0=p0, d=d))

    focus = estimate_focus(outgoing_lines)
    if focus is None:
        analysis = {
            "focus": None,
            "spot_rms": None,
            "ray_count": len(outgoing_lines),
            "profile": None,
        }
    else:
        fp, rms = focus
        profile = intensity_profile_at_x(outgoing_lines, detector_x=fp.x, bins=200)
        analysis = {
            "focus": [fp.x, fp.y],
            "spot_rms": rms,
            "ray_count": len(outgoing_lines),
            "profile": profile,
        }

    return {"rays": rays_out, "analysis": analysis}


def _trace_one(
    ro: Vec2,
    rd: Vec2,
    lenses: List[FresnelThinLens],
    mirrors: List[ConicMirror],
    max_bounces: int,
    max_dist: float,
) -> List[Vec2]:
    pts: List[Vec2] = [ro]
    o = ro
    d = rd.normalized()

    for _ in range(max_bounces + 1):
        hit_best = None

        for ln in lenses:
            h = ln.intersect(o, d)
            if h is None:
                continue
            if hit_best is None or h.t < hit_best.t:
                hit_best = ("lens", ln, h)

        for mr in mirrors:
            h = mr.intersect(o, d)
            if h is None:
                continue
            if hit_best is None or h.t < hit_best[2].t:
                hit_best = ("mirror", mr, h)

        if hit_best is None:
            pts.append(o + d * max_dist)
            break

        kind, elem, h = hit_best
        pts.append(h.p_world)

        # Offset origin to avoid self-intersection.
        o = h.p_world + d * 1e-6

        if kind == "lens":
            d = elem.transmit(h.p_world, d)
        else:
            d = elem.reflect(d, h.n_world)

    return pts

