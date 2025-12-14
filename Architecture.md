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

* `sources[]`: point sources with `pos`, `power` (relative), `ray_count`
* `lenses[]`: thin-lens-equivalent Fresnel with `pos`, `theta`, `f` (meters), `aperture` (meters)
* `mirrors[]`: parabolic mirror segment with `pos`, `theta`, `f` (meters), `aperture` (meters)
* `settings`: `max_bounces`, `max_distance`, `seed`

## Physics models (MVP)

### Reflection (parabolic mirror)

In mirror-local coordinates, the parabola is:

* `y^2 = 4 f x` (opens in +x)

Normal from implicit surface `F(x,y) = y^2 - 4 f x`:

* `∇F = (-4 f, 2 y)`

Reflection for unit direction `d` and unit normal `n`:

* `d' = d - 2 (d·n) n`

### Refraction / focusing (thin lens approximation)

Instead of modeling Fresnel facets explicitly, we use the paraxial thin-lens ray transfer relation.
In lens-local coordinates with lens plane `x = 0`:

* Let ray slope `m = dy/dx`.
* At intersection height `y`, outgoing slope is:

  * `m2 = m - y/f`

This is the standard thin lens relation (ABCD matrices) and is accurate for small angles.

### Intensity / concentration

We estimate the focus point by finding the point in the plane minimizing squared distances to the set of outgoing ray lines (least-squares line intersection).

We report:

* `focus_point (x,y)`
* `spot_rms` (meters): RMS perpendicular distance of rays to the focus point
* optional `profile`: histogram along a user-defined detector (future enhancement)

## Endpoints

* `GET /` serves the frontend.
* `POST /api/simulate` takes a scene JSON and returns:
  * polyline segments for each ray
  * analysis: focus point + spot RMS

