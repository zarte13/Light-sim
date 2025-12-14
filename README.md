# Light-sim (2D ray optics)

Local Python web app (FastAPI + HTML canvas) to simulate 2D light rays with:

* Click-to-place point light sources (emit rays in all directions)
* Movable/rotatable thin-lens-equivalent Fresnel lenses
* Movable/rotatable parabolic mirrors
* Sliders + numeric inputs for parameters
* Import/export of scene JSON and analysis (focus point + spot metrics)

## Run

1. Create venv and install deps:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Start server:

```bash
python -m uvicorn app.main:app --reload
```

3. Open:

* http://127.0.0.1:8000

## Notes

* Units: meters internally (UI can display mm/cm).
* Fresnel lens is modeled as an equivalent thin lens (paraxial) via `m2 = m - y/f`.
* Parabolic mirror is modeled as a true parabola segment in its local frame.

