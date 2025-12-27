# Light-sim (2D ray optics)

Local Python web app (FastAPI + HTML canvas) to simulate 2D light rays with:

* Click-to-place point light sources (emit rays in all directions)
* Collimated beam sources (parallel rays)
* Movable/rotatable thin-lens-equivalent Fresnel lenses
* Optional Snell/facet Fresnel lens mode (indices `n1`, `n2`)
* Movable/rotatable conic mirrors (parabola/sphere/ellipse/hyperbola via kappa)
* Sliders + numeric inputs for parameters
* Import/export of scene JSON and analysis (focus point + spot metrics)

## Clone

```bash
git clone https://github.com/zarte13/Light-sim.git
cd Light-sim
```

## Run

1. Create venv and install deps:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```
Si vous utiliser powershell, voici la commande pour activé les scripts powershell: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

2. Start server:

```bash
python -m uvicorn app.main:app --reload
```

3. Open:

* http://127.0.0.1:8000

## Notes

* Units: meters internally (UI can display mm/cm).
* Fresnel lens is modeled as an equivalent thin lens (paraxial) via `m2 = m - y/f`.
* Conic mirror is modeled as a true conic segment in its local frame using `R` (vertex radius of curvature) and conic constant `kappa`.

