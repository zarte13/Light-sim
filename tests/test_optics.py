import math
import unittest

from app.optics.elements import ConicMirror, FresnelFacetLens, FresnelThinLens
from app.optics.schema import Scene
from app.optics.simulate import simulate_scene
from app.optics.transform import Pose2
from app.optics.vec2 import Vec2


class TestOptics(unittest.TestCase):
    def test_reflection_flat_normal(self):
        m = ConicMirror(
            id="m",
            pose=Pose2(pos=Vec2(0, 0), theta=0.0),
            R=1.0,
            kappa=-1.0,
            aperture=1.0,
        )
        d_in = Vec2(1, 0)
        n = Vec2(1, 0)
        d_out = m.reflect(d_in, n)
        self.assertAlmostEqual(d_out.x, -1.0, places=7)
        self.assertAlmostEqual(d_out.y, 0.0, places=7)

    def test_thin_lens_slope_kick(self):
        lens = FresnelThinLens(id="l", pose=Pose2(pos=Vec2(0, 0), theta=0.0), f=1.0, aperture=1.0)
        p_hit = Vec2(0.0, 0.1)
        d_in = Vec2(1.0, 0.0)
        d_out = lens.transmit(p_hit, d_in)
        # Expect dy/dx about -0.1
        self.assertAlmostEqual(d_out.y / d_out.x, -0.1, places=3)

    def test_fresnel_facet_snell_targets_focus(self):
        lens = FresnelFacetLens(
            id="l",
            pose=Pose2(pos=Vec2(0, 0), theta=0.0),
            f=1.0,
            aperture=1.0,
            n1=1.0,
            n2=1.5,
        )
        p_hit = Vec2(0.0, 0.1)
        d_in = Vec2(1.0, 0.0)
        d_out = lens.transmit(p_hit, d_in)
        self.assertAlmostEqual(d_out.y / d_out.x, -0.1, places=3)

    def test_conic_parabola_intersection_on_axis(self):
        # Parabola corresponds to kappa=-1 and has y^2 = 2 R x.
        mir = ConicMirror(id="m", pose=Pose2(pos=Vec2(0, 0), theta=0.0), R=1.0, kappa=-1.0, aperture=1.0)
        ro = Vec2(1.0, 0.0)
        rd = Vec2(-1.0, 0.0)
        h = mir.intersect(ro, rd)
        self.assertIsNotNone(h)
        self.assertAlmostEqual(h.p_world.x, 0.0, places=7)
        self.assertAlmostEqual(h.p_world.y, 0.0, places=7)

    def test_conic_sphere_intersection_on_axis(self):
        # Sphere corresponds to kappa=0. In cross-section this is a circle of radius R
        # with its vertex at the origin.
        mir = ConicMirror(id="m", pose=Pose2(pos=Vec2(0, 0), theta=0.0), R=1.0, kappa=0.0, aperture=1.0)
        ro = Vec2(1.0, 0.0)
        rd = Vec2(-1.0, 0.0)
        h = mir.intersect(ro, rd)
        self.assertIsNotNone(h)
        self.assertAlmostEqual(h.p_world.x, 0.0, places=7)
        self.assertAlmostEqual(h.p_world.y, 0.0, places=7)

    def test_simulate_two_lenses_does_not_crash(self):
        scene = Scene(
            sources=[{"id": "s", "type": "point", "pos": {"x": 0, "y": 0}, "ray_count": 200}],
            lenses=[
                {"id": "l1", "type": "fresnel_thin", "pos": {"x": 0.8, "y": 0}, "theta": 0, "f": 0.3, "aperture": 0.25},
                {"id": "l2", "type": "fresnel_thin", "pos": {"x": 1.0, "y": 0}, "theta": 0, "f": 0.3, "aperture": 0.25},
            ],
            mirrors=[],
            settings={"max_bounces": 4, "max_distance": 5.0, "seed": 1},
        )
        out = simulate_scene(scene)
        self.assertEqual(len(out["rays"]), 200)

    def test_collimated_source_with_conic_mirror_has_focus(self):
        scene = Scene(
            sources=[
                {
                    "id": "s",
                    "type": "collimated",
                    "pos": {"x": 0, "y": 0},
                    "theta": 0.0,
                    "width": 0.5,
                    "ray_count": 400,
                }
            ],
            lenses=[],
            mirrors=[{"id": "m", "type": "conic", "pos": {"x": 1.2, "y": 0}, "theta": math.pi, "R": 0.7, "kappa": 0.0, "aperture": 0.6}],
            settings={"max_bounces": 1, "max_distance": 5.0, "seed": 1},
        )
        out = simulate_scene(scene)
        self.assertIsNotNone(out["analysis"]["focus"])


if __name__ == "__main__":
    unittest.main()

