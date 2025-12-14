from __future__ import annotations

from dataclasses import dataclass
from app.optics.vec2 import Vec2, rotate


@dataclass(frozen=True)
class Pose2:
    pos: Vec2
    theta: float  # radians

    def world_to_local(self, p: Vec2) -> Vec2:
        return rotate(p - self.pos, -self.theta)

    def local_to_world(self, p: Vec2) -> Vec2:
        return rotate(p, self.theta) + self.pos

    def dir_world_to_local(self, d: Vec2) -> Vec2:
        return rotate(d, -self.theta)

    def dir_local_to_world(self, d: Vec2) -> Vec2:
        return rotate(d, self.theta)

