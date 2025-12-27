from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from app.optics.transform import Pose2
from app.optics.vec2 import Vec2


def refract_dir(d_in: Vec2, n: Vec2, n1: float, n2: float) -> Optional[Vec2]:
    """Refract direction vector across an interface using Snell's law (vector form).

    `d_in` and `n` must be normalized.
    `n` points from medium 1 toward medium 2.

    Returns None on total internal reflection.
    """

    d = d_in.normalized()
    nn = n.normalized()
    eta = float(n1) / float(n2)
    cos1 = -nn.dot(d)
    k = 1.0 - eta * eta * (1.0 - cos1 * cos1)
    if k < 0.0:
        return None
    cos2 = math.sqrt(max(0.0, k))
    t = (d * eta) + (nn * (eta * cos1 - cos2))
    return t.normalized()


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
class FresnelFacetLens:
    """Idealized Fresnel lens using a Snell-law direction change at an infinitely thin interface.

    This is not a full geometric facet model (no thickness / no second surface).
    It picks a local normal so that, for on-axis collimated light, rays at height `y`
    are redirected toward the focal point `(f, 0)` in lens-local coordinates.
    """

    id: str
    pose: Pose2
    f: float
    aperture: float  # full height
    n1: float = 1.0
    n2: float = 1.49

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
        # Normal is height-dependent; returned normal is a placeholder.
        n_w = self.pose.dir_local_to_world(Vec2(1.0, 0.0)).normalized()
        return Hit(t=t, p_world=p_w, n_world=n_w, element_id=self.id, element_type="lens")

    def transmit(self, p_world: Vec2, rd_world: Vec2) -> Vec2:
        p_l = self.pose.world_to_local(p_world)
        d_l = self.pose.dir_world_to_local(rd_world).normalized()

        # Preserve propagation direction sign across lens.
        sgn = 1.0 if d_l.x >= 0 else -1.0

        # Desired outgoing direction: toward focal point in local coords.
        target = Vec2(sgn * self.f, -p_l.y).normalized()

        # Choose a local interface normal that satisfies Snell tangential constraint:
        # (n1 * d_in - n2 * d_out) is parallel to the surface normal.
        n_l = (d_l * float(self.n1) - target * float(self.n2)).normalized()
        if n_l.norm() == 0:
            return self.pose.dir_local_to_world(target).normalized()
        if d_l.dot(n_l) > 0:
            n_l = n_l * -1.0

        d2_l = refract_dir(d_l, n_l, self.n1, self.n2)
        if d2_l is None:
            # Total internal reflection fallback.
            d2_l = (d_l - n_l * (2.0 * d_l.dot(n_l))).normalized()
        return self.pose.dir_local_to_world(d2_l).normalized()


@dataclass(frozen=True)
class ConicMirror:
    id: str
    pose: Pose2
    R: float  # radius of curvature at vertex
    kappa: float  # conic constant
    aperture: float  # full height

    def intersect(self, ro: Vec2, rd: Vec2) -> Optional[Hit]:
        ro_l = self.pose.world_to_local(ro)
        rd_l = self.pose.dir_world_to_local(rd).normalized()

        # Intersect with conic section in mirror-local coordinates.
        # Implicit surface (cross-section):
        #   F(x, y) = y^2 - 2 R x + (1 + kappa) x^2 = 0
        # where the usable branch opens toward +x and has its vertex at (0, 0).
        y0 = ro_l.y
        x0 = ro_l.x
        dy = rd_l.y
        dx = rd_l.x

        k1 = 1.0 + float(self.kappa)
        R = float(self.R)

        A = (dy * dy) + k1 * (dx * dx)
        B = (2.0 * y0 * dy) - (2.0 * R * dx) + (2.0 * k1 * x0 * dx)
        C = (y0 * y0) - (2.0 * R * x0) + k1 * (x0 * x0)

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

        # Normal from grad(F) = (dF/dx, dF/dy)
        # dF/dx = -2R + 2(1+kappa)x
        # dF/dy = 2y
        n_l = Vec2((-2.0 * R) + (2.0 * k1 * p_best.x), 2.0 * p_best.y).normalized()
        p_w = self.pose.local_to_world(p_best)
        n_w = self.pose.dir_local_to_world(n_l).normalized()
        return Hit(t=t_best, p_world=p_w, n_world=n_w, element_id=self.id, element_type="mirror")

    def reflect(self, rd_world: Vec2, n_world: Vec2) -> Vec2:
        d = rd_world.normalized()
        n = n_world.normalized()
        return (d - n * (2.0 * d.dot(n))).normalized()


@dataclass(frozen=True)
class Sensor:
    """A line segment sensor that detects ray intersections without affecting ray direction."""

    id: str
    pose: Pose2
    length: float  # full length of the sensor line

    def intersect(self, ro: Vec2, rd: Vec2) -> Optional[Hit]:
        """Intersect ray with the sensor line segment.

        Sensor is a line segment centered at pose.pos, extending perpendicular
        to the pose direction by length/2 in each direction.
        """
        # Sensor line in local coords: from (-length/2, 0) to (length/2, 0)
        # Ray in local coords
        ro_l = self.pose.world_to_local(ro)
        rd_l = self.pose.dir_world_to_local(rd).normalized()

        # Ray equation: p = ro_l + t * rd_l
        # Line segment: x = 0, y ∈ [-length/2, length/2]
        # We need to find intersection with the line x = 0

        if abs(rd_l.x) < 1e-12:
            # Ray is parallel to the sensor line
            return None

        t = -ro_l.x / rd_l.x
        if t <= 1e-9:
            # Intersection behind ray origin
            return None

        p_l = Vec2(ro_l.x + t * rd_l.x, ro_l.y + t * rd_l.y)

        # Check if intersection point is within sensor length
        half_len = self.length / 2
        if abs(p_l.y) > half_len:
            return None

        p_w = self.pose.local_to_world(p_l)
        # Normal points in +x direction (sensor plane normal)
        n_w = self.pose.dir_local_to_world(Vec2(1.0, 0.0)).normalized()
        return Hit(t=t, p_world=p_w, n_world=n_w, element_id=self.id, element_type="sensor")

