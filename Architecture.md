# Architecture

## Overview

The app is split into:

* Python backend (FastAPI) for **ray tracing + analysis**
* Browser frontend (HTML + Canvas) for **interactive editing + visualization**

```
Browser (canvas editor)
  scene JSON  ───────────────►  POST /api/simulate
  rays + analysis ◄──────────  (ray tracing + focus metrics)
```

## Coordinate system and units

* 2D world coordinates in **meters**.
* Right-handed: +x to the right, +y upward.
* Each optical element has a **pose**: position `(x, y)` and rotation `theta` (radians).

## Scene schema (MVP)

Scene JSON contains:

* `sensors[]`: Line segment sensors that detect ray intersections
  * `type="line"`: Line segment at `pos` with rotation `theta` and full `length` (meters)
  * Sensors let all rays pass through (non-blocking) and count intersections
* `sources[]`:
  * `type="point"`: point source at `pos` emitting rays in all directions
  * `type="collimated"`: collimated beam with center `pos`, direction `theta` (radians), and full beam `width`
* `lenses[]`: Fresnel lenses with selectable model:
  * `type="fresnel_thin"`: paraxial thin-lens approximation (`f`, `aperture`)
  * `type="fresnel_facet"`: idealized Snell/facet model (`f`, `aperture`, `n1`, `n2`)
* `mirrors[]`: **conic** mirror segment with `pos`, `theta`, `R` (meters), `kappa`, `aperture` (meters)
* `settings`: `max_bounces`, `max_distance`, `seed`

## Physics models (MVP)

### Reflection (conic mirror)

In mirror-local coordinates, we model the mirror cross-section as the conic:

* `F(x,y) = y^2 - 2 R x + (1 + kappa) x^2 = 0`

This matches the common optical sagitta form for a conic surface (with the vertex at the origin, opening toward `+x`).
Special cases:

* `kappa = -1` → parabola: `y^2 = 2 R x` (equivalent to `y^2 = 4 f x` with `R = 2 f`)
* `kappa = 0` → sphere

Normal from the implicit surface `F(x,y)`:

* `∇F = (dF/dx, dF/dy) = (-2R + 2(1+kappa)x, 2y)`

Reflection for unit direction `d` and unit normal `n`:

* `d' = d - 2 (d·n) n`

### Refraction / focusing (thin lens approximation)

Instead of modeling Fresnel facets explicitly, we use the paraxial thin-lens ray transfer relation.
In lens-local coordinates with lens plane `x = 0`:

* Let ray slope `m = dy/dx`.
* At intersection height `y`, outgoing slope is:

  * `m2 = m - y/f`

This is the standard thin lens relation (ABCD matrices) and is accurate for small angles.

### Refraction (Snell / facet Fresnel model)

For the optional Snell-based Fresnel lens model, we use the **vector** refraction law.
Given a unit incident direction `I`, a unit surface normal `n`, and refractive indices `n1 → n2`:

* `cos(theta1) = -n · I`
* `cos(theta2) = sqrt(1 - (n1/n2)^2 * (1 - cos(theta1)^2))`
* `V = (n1/n2) I + ((n1/n2) cos(theta1) - cos(theta2)) n`

If the expression under the square-root is negative, total internal reflection occurs.

### Focus metric (aberrations)

For conic mirrors with `kappa != -1` (or any aberrated system), rays generally do **not** intersect at a single point.
Instead of only computing a least-squares line intersection, we also scan detector planes along `x` and pick the plane
with minimal spot RMS (circle of least confusion in 2D).

### Intensity / concentration

We estimate the focus point by finding the point in the plane minimizing squared distances to the set of outgoing ray lines (least-squares line intersection).

We report:

* `focus_point (x,y)`
* `spot_rms` (meters): RMS perpendicular distance of rays to the focus point
* optional `profile`: histogram along a user-defined detector (future enhancement)

### Sensor measurements

Sensors are line segments that detect ray intersections without affecting ray direction. For each sensor, we report:

* `ray_count`: Number of rays that passed through the sensor
* `percentage`: Percentage of total emitted rays that hit the sensor

Sensors glow green in the visualization when hit by rays.

## Endpoints

* `GET /` serves the frontend.
* `POST /api/simulate` takes a scene JSON and returns:
  * `rays`: polyline segments for each ray
  * `analysis`: focus point, spot RMS, intensity profile, and sensor measurements
