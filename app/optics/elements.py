from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from app.optics.transform import Pose2
from app.optics.vec2 import Vec2


@dataclass(frozen=True)
class Hit:
    t: float
    p_world: Vec2
    n_world: Vec2
    element_id: str
    element_type: str


@dataclass(frozen=True)
class FresnelThinLens:
    id: str
    pose: Pose2
    f: float
    aperture: float  # full height

    def intersect(self, ro: Vec2, rd: Vec2) -> Optional[Hit]:
        # Lens plane is x=0 in local coordinates.
        ro_l = self.pose.world_to_local(ro)
        rd_l = self.pose.dir_world_to_local(rd)
        if abs(rd_l.x) < 1e-12:
            return None
        t = -ro_l.x / rd_l.x
        if t <= 1e-9:
            return None
        p_l = Vec2(ro_l.x + t * rd_l.x, ro_l.y + t * rd_l.y)
        if abs(p_l.y) > self.aperture / 2:
            return None
        p_w = self.pose.local_to_world(p_l)
        n_w = self.pose.dir_local_to_world(Vec2(1.0, 0.0)).normalized()
        return Hit(t=t, p_world=p_w, n_world=n_w, element_id=self.id, element_type="lens")

    def transmit(self, p_world: Vec2, rd_world: Vec2) -> Vec2:
        # Paraxial thin-lens: m2 = m - y/f in lens local coordinates.
        p_l = self.pose.world_to_local(p_world)
        d_l = self.pose.dir_world_to_local(rd_world).normalized()
        # Preserve propagation direction sign across lens.
        sgn = 1.0 if d_l.x >= 0 else -1.0
        dx = d_l.x
        if abs(dx) < 1e-12:
            dx = 1e-12 * sgn
        m = d_l.y / dx
        m2 = m - (p_l.y / self.f)
        d2_l = Vec2(sgn, m2).normalized()
        return self.pose.dir_local_to_world(d2_l).normalized()


@dataclass(frozen=True)
class ParabolicMirror:
    id: str
    pose: Pose2
    f: float
    aperture: float  # full height

    def intersect(self, ro: Vec2, rd: Vec2) -> Optional[Hit]:
        ro_l = self.pose.world_to_local(ro)
        rd_l = self.pose.dir_world_to_local(rd).normalized()

        # Solve (y0 + t dy)^2 = 4 f (x0 + t dx)
        y0 = ro_l.y
        x0 = ro_l.x
        dy = rd_l.y
        dx = rd_l.x
        A = dy * dy
        B = 2 * y0 * dy - 4 * self.f * dx
        C = y0 * y0 - 4 * self.f * x0

        ts = []
        if abs(A) < 1e-12:
            # Linear B t + C = 0
            if abs(B) < 1e-12:
                return None
            t = -C / B
            ts = [t]
        else:
            disc = B * B - 4 * A * C
            if disc < 0:
                return None
            s = math.sqrt(disc)
            t1 = (-B - s) / (2 * A)
            t2 = (-B + s) / (2 * A)
            ts = [t1, t2]

        t_best = None
        p_best = None
        for t in ts:
            if t <= 1e-9:
                continue
            p_l = Vec2(x0 + t * dx, y0 + t * dy)
            if p_l.x < -1e-9:
                continue
            if abs(p_l.y) > self.aperture / 2:
                continue
            if t_best is None or t < t_best:
                t_best = t
                p_best = p_l

        if t_best is None or p_best is None:
            return None

        # Normal from grad(y^2 - 4 f x)
        n_l = Vec2(-4 * self.f, 2 * p_best.y).normalized()
        p_w = self.pose.local_to_world(p_best)
        n_w = self.pose.dir_local_to_world(n_l).normalized()
        return Hit(t=t_best, p_world=p_w, n_world=n_w, element_id=self.id, element_type="mirror")

    def reflect(self, rd_world: Vec2, n_world: Vec2) -> Vec2:
        d = rd_world.normalized()
        n = n_world.normalized()
        return (d - n * (2.0 * d.dot(n))).normalized()

