import math
import unittest

from app.optics.elements import FresnelThinLens, ParabolicMirror
from app.optics.transform import Pose2
from app.optics.vec2 import Vec2


class TestOptics(unittest.TestCase):
    def test_reflection_flat_normal(self):
        m = ParabolicMirror(id="m", pose=Pose2(pos=Vec2(0, 0), theta=0.0), f=0.5, aperture=1.0)
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

    def test_parabola_intersection_on_axis(self):
        mir = ParabolicMirror(id="m", pose=Pose2(pos=Vec2(0, 0), theta=0.0), f=0.5, aperture=1.0)
        ro = Vec2(1.0, 0.0)
        rd = Vec2(-1.0, 0.0)
        h = mir.intersect(ro, rd)
        self.assertIsNotNone(h)
        self.assertAlmostEqual(h.p_world.x, 0.0, places=7)
        self.assertAlmostEqual(h.p_world.y, 0.0, places=7)


if __name__ == "__main__":
    unittest.main()

