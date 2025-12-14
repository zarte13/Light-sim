from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def __add__(self, o: "Vec2") -> "Vec2":
        return Vec2(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "Vec2") -> "Vec2":
        return Vec2(self.x - o.x, self.y - o.y)

    def __mul__(self, s: float) -> "Vec2":
        return Vec2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def dot(self, o: "Vec2") -> float:
        return self.x * o.x + self.y * o.y

    def norm(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vec2":
        n = self.norm()
        if n == 0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / n, self.y / n)

    def perp(self) -> "Vec2":
        return Vec2(-self.y, self.x)


def rotate(v: Vec2, theta: float) -> Vec2:
    c = math.cos(theta)
    s = math.sin(theta)
    return Vec2(c * v.x - s * v.y, s * v.x + c * v.y)

