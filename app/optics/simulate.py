from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

from app.optics.analysis import RayLine, best_focus_scan, estimate_focus, intensity_profile_at_x
from app.optics.elements import ConicMirror, FresnelFacetLens, FresnelThinLens, Sensor
from app.optics.schema import Scene
from app.optics.transform import Pose2
from app.optics.vec2 import Vec2


def _vec(v) -> Vec2:
    return Vec2(float(v.x), float(v.y))


def simulate_scene(scene: Scene) -> Dict:
    lenses = []
    for l in scene.lenses:
        if l.type == "fresnel_facet":
            lenses.append(
                FresnelFacetLens(
                    id=l.id,
                    pose=Pose2(pos=_vec(l.pos), theta=float(l.theta)),
                    f=float(l.f),
                    aperture=float(l.aperture),
                    n1=float(l.n1),
                    n2=float(l.n2),
                )
            )
        else:
            lenses.append(
                FresnelThinLens(
                    id=l.id,
                    pose=Pose2(pos=_vec(l.pos), theta=float(l.theta)),
                    f=float(l.f),
                    aperture=float(l.aperture),
                )
            )
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
    sensors = [
        Sensor(
            id=s.id,
            pose=Pose2(pos=_vec(s.pos), theta=float(s.theta)),
            length=float(s.length),
        )
        for s in scene.sensors
    ]

    max_bounces = int(scene.settings.max_bounces)
    max_dist = float(scene.settings.max_distance)
    angular_jitter = float(scene.settings.angular_jitter)
    rng = np.random.default_rng(scene.settings.seed)

    rays_out: List[Dict] = []
    outgoing_lines: List[RayLine] = []
    sensor_hits: Dict[str, int] = {s.id: 0 for s in sensors}
    total_rays = 0

    for s in scene.sources:
        if s.ray_count <= 0:
            continue

        n = int(s.ray_count)
        total_rays += n
        src_pos = _vec(s.pos)

        if s.type == "collimated":
            base = float(s.theta)
            d0 = Vec2(math.cos(base), math.sin(base)).normalized()
            u = d0.perp().normalized()
            w = float(s.width)
            denom = max(1, n - 1)
            for i in range(n):
                off = (-0.5 * w) + (w * (i / denom))
                origin = src_pos + u * off
                ang = base
                if angular_jitter > 0:
                    ang += float(rng.uniform(-angular_jitter, angular_jitter))
                rd = Vec2(math.cos(ang), math.sin(ang)).normalized()
                poly = _trace_one(origin, rd, lenses, mirrors, sensors, sensor_hits, max_bounces, max_dist)
                rays_out.append({"points": [[p.x, p.y] for p in poly]})
                if len(poly) >= 2:
                    p0 = poly[-2]
                    p1 = poly[-1]
                    d = (p1 - p0).normalized()
                    if d.norm() > 0:
                        outgoing_lines.append(RayLine(p0=p0, d=d))
        else:
            origin = src_pos
            for i in range(n):
                ang = (2.0 * math.pi) * (i / n)
                if angular_jitter > 0:
                    ang += float(rng.uniform(-angular_jitter, angular_jitter))
                rd = Vec2(math.cos(ang), math.sin(ang)).normalized()
                poly = _trace_one(origin, rd, lenses, mirrors, sensors, sensor_hits, max_bounces, max_dist)
                rays_out.append({"points": [[p.x, p.y] for p in poly]})

                if len(poly) >= 2:
                    p0 = poly[-2]
                    p1 = poly[-1]
                    d = (p1 - p0).normalized()
                    if d.norm() > 0:
                        outgoing_lines.append(RayLine(p0=p0, d=d))

    focus = None
    if outgoing_lines:
        dx_mean = float(np.mean([ln.d.x for ln in outgoing_lines]))
        if dx_mean >= 0:
            x_min = min(ln.p0.x for ln in outgoing_lines)
            x_max = x_min + max_dist
        else:
            x_max = max(ln.p0.x for ln in outgoing_lines)
            x_min = x_max - max_dist
        focus = best_focus_scan(outgoing_lines, x_min=x_min, x_max=x_max, steps=240)
    if focus is None:
        focus = estimate_focus(outgoing_lines)
    if focus is None:
        analysis = {
            "focus": None,
            "spot_rms": None,
            "ray_count": len(outgoing_lines),
            "profile": None,
            "sensors": None,
        }
    else:
        fp, rms = focus
        profile = intensity_profile_at_x(outgoing_lines, detector_x=fp.x, bins=200)
        analysis = {
            "focus": [fp.x, fp.y],
            "spot_rms": rms,
            "ray_count": len(outgoing_lines),
            "profile": profile,
            "sensors": None,
        }

    # Add sensor analysis if any sensors exist
    if sensors:
        sensor_analysis = {}
        for s_id, hit_count in sensor_hits.items():
            percentage = (hit_count / total_rays * 100) if total_rays > 0 else 0.0
            sensor_analysis[s_id] = {
                "ray_count": hit_count,
                "percentage": round(percentage, 2),
            }
        analysis["sensors"] = sensor_analysis

    return {"rays": rays_out, "analysis": analysis}


def _trace_one(
    ro: Vec2,
    rd: Vec2,
    lenses: List[object],
    mirrors: List[ConicMirror],
    sensors: List[Sensor],
    sensor_hits: Dict[str, int],
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
            if hit_best is None or h.t < hit_best[2].t:
                hit_best = ("lens", ln, h)

        for mr in mirrors:
            h = mr.intersect(o, d)
            if h is None:
                continue
            if hit_best is None or h.t < hit_best[2].t:
                hit_best = ("mirror", mr, h)

        # Check sensors (they don't affect ray direction, just count hits)
        for sn in sensors:
            h = sn.intersect(o, d)
            if h is None:
                continue
            # Record sensor hit
            if h.element_id in sensor_hits:
                sensor_hits[h.element_id] += 1
            # Continue checking for other elements
            if hit_best is None or h.t < hit_best[2].t:
                hit_best = ("sensor", sn, h)

        if hit_best is None:
            pts.append(o + d * max_dist)
            break

        kind, elem, h = hit_best
        pts.append(h.p_world)

        if kind == "lens":
            d2 = elem.transmit(h.p_world, d)
        elif kind == "mirror":
            d2 = elem.reflect(d, h.n_world)
        else:
            # Sensor: ray continues straight through
            d2 = d

        # Offset origin to avoid self-intersection (along the *new* direction).
        d = d2
        o = h.p_world + d * 1e-6

    return pts

