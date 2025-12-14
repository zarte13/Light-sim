from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Vec2Model(BaseModel):
    x: float
    y: float


class SourceModel(BaseModel):
    id: str
    type: Literal["point", "collimated"] = "point"
    pos: Vec2Model
    power: float = 1.0
    ray_count: int = Field(default=2000, ge=10, le=20000)
    # For collimated sources
    theta: float = Field(default=0.0, description="Direction angle (radians) for collimated sources.")
    width: float = Field(default=0.5, gt=0.0, description="Full beam width (m) for collimated sources.")


class FresnelLensModel(BaseModel):
    id: str
    type: Literal["fresnel_thin", "fresnel_facet"] = "fresnel_thin"
    pos: Vec2Model
    theta: float = 0.0
    f: float = Field(..., gt=0.0, description="Focal length (m)")
    aperture: float = Field(default=0.2, gt=0.0, description="Full aperture height (m)")
    # Only used by Snell/facet model
    n1: float = Field(default=1.0, gt=0.0, description="Refractive index on incident side")
    n2: float = Field(default=1.49, gt=0.0, description="Refractive index inside/exit side")


class ConicMirrorModel(BaseModel):
    id: str
    type: Literal["conic"] = "conic"
    pos: Vec2Model
    theta: float = 0.0
    R: float = Field(..., gt=0.0, description="Radius of curvature at the vertex (m)")
    kappa: float = Field(
        default=-1.0,
        description="Conic constant (kappa). -1=parabola, 0=sphere, <-1=hyperbola, -1..0=ellipse.",
    )
    aperture: float = Field(default=0.5, gt=0.0, description="Full aperture height (m)")


class SettingsModel(BaseModel):
    max_bounces: int = Field(default=6, ge=0, le=50)
    max_distance: float = Field(default=5.0, gt=0.0)
    angular_jitter: float = Field(
        default=0.0,
        ge=0.0,
        le=0.5,
        description="Optional random jitter (radians) added to each emitted ray angle.",
    )
    seed: Optional[int] = None


class Scene(BaseModel):
    sources: List[SourceModel] = Field(default_factory=list)
    lenses: List[FresnelLensModel] = Field(default_factory=list)
    mirrors: List[ConicMirrorModel] = Field(default_factory=list)
    settings: SettingsModel = Field(default_factory=SettingsModel)

