const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// --- Scene state ---
const scene = {
  sources: [],
  lenses: [],
  mirrors: [],
  settings: { max_bounces: 6, max_distance: 5.0, seed: null },
};

let tool = 'select';
let selected = null; // {type, id}
let rays = [];
let analysis = null;

// View transform (world meters -> screen pixels)
// We render in CSS pixels; the backing store uses devicePixelRatio.
let canvasCss = { w: 1200, h: 700 };
let dpr = Math.max(1, window.devicePixelRatio || 1);

let view = {
  scale: 220, // CSS px per meter
  offsetX: 80,
  offsetY: canvasCss.h / 2,
};

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const wCss = Math.max(300, Math.floor(rect.width));
  const hCss = Math.max(300, Math.floor(rect.height));
  canvasCss = { w: wCss, h: hCss };

  dpr = Math.max(1, window.devicePixelRatio || 1);
  const w = Math.floor(wCss * dpr);
  const h = Math.floor(hCss * dpr);

  // Keep backing store in sync with CSS size; otherwise the browser will stretch the bitmap.
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }

  // Draw in CSS pixels.
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  if (!Number.isFinite(view.offsetY)) view.offsetY = canvasCss.h / 2;
}

window.addEventListener('resize', () => {
  resizeCanvas();
  // keep y center pinned on resize
  view.offsetY = canvasCss.h / 2;
  draw();
});

resizeCanvas();

function eventToCanvasXY(ev) {
  const rect = canvas.getBoundingClientRect();
  // Return CSS pixel coordinates (matches our rendering space)
  const sx = ev.clientX - rect.left;
  const sy = ev.clientY - rect.top;
  return { sx, sy };
}

function worldToScreen(p) {
  return {
    x: view.offsetX + p.x * view.scale,
    y: view.offsetY - p.y * view.scale,
  };
}
function screenToWorld(x, y) {
  return {
    x: (x - view.offsetX) / view.scale,
    y: -(y - view.offsetY) / view.scale,
  };
}

function uid(prefix) {
  return `${prefix}_${Math.random().toString(16).slice(2, 10)}`;
}

// --- UI wiring ---
function bindRangeNumber(rangeEl, numEl, onChange) {
  const sync = (v) => {
    rangeEl.value = v;
    numEl.value = v;
    onChange(Number(v));
  };
  rangeEl.addEventListener('input', () => sync(rangeEl.value));
  numEl.addEventListener('change', () => sync(numEl.value));
}

bindRangeNumber(
  document.getElementById('rayCount'),
  document.getElementById('rayCountNum'),
  (v) => {
    // apply to all sources for MVP
    scene.sources.forEach((s) => (s.ray_count = v));
  }
);
bindRangeNumber(
  document.getElementById('maxBounces'),
  document.getElementById('maxBouncesNum'),
  (v) => {
    scene.settings.max_bounces = v;
  }
);

document.getElementById('toolSelect').onclick = () => (tool = 'select');
document.getElementById('toolSource').onclick = () => (tool = 'add_source');
document.getElementById('toolCollimated').onclick = () => (tool = 'add_collimated');

document.getElementById('addLens').onclick = () => {
  const id = uid('lens');
  scene.lenses.push({
    id,
    type: 'fresnel_thin',
    pos: { x: 0.8, y: 0 },
    theta: 0,
    f: 0.3,
    aperture: 0.25,
    n1: 1.0,
    n2: 1.49,
  });
  select({ type: 'lens', id });
  draw();
};
document.getElementById('addMirror').onclick = () => {
  const id = uid('mirror');
  scene.mirrors.push({
    id,
    type: 'conic',
    pos: { x: 1.2, y: 0 },
    theta: Math.PI,
    // For kappa=-1 (parabola): R = 2f
    R: 0.7,
    kappa: -1.0,
    aperture: 0.6,
  });
  select({ type: 'mirror', id });
  draw();
};

document.getElementById('btnSim').onclick = async () => {
  const res = await fetch('/api/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(scene),
  });
  const data = await res.json();
  rays = data.rays || [];
  analysis = data.analysis || null;
  document.getElementById('analysis').textContent = JSON.stringify(analysis, null, 2);
  draw();
};

document.getElementById('btnExport').onclick = () => {
  const blob = new Blob([JSON.stringify({ scene, analysis }, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'light-sim-export.json';
  a.click();
};

document.getElementById('fileImport').addEventListener('change', async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  const txt = await file.text();
  const obj = JSON.parse(txt);
  if (obj.scene) {
    Object.assign(scene, obj.scene);
    analysis = obj.analysis || null;
    document.getElementById('analysis').textContent = analysis ? JSON.stringify(analysis, null, 2) : '';
    selected = null;
    rays = [];
    refreshSelectionUI();
    draw();
  }
});

// --- Selection panel ---
function findSelected() {
  if (!selected) return null;
  if (selected.type === 'source') return scene.sources.find((s) => s.id === selected.id) || null;
  if (selected.type === 'lens') return scene.lenses.find((l) => l.id === selected.id) || null;
  if (selected.type === 'mirror') return scene.mirrors.find((m) => m.id === selected.id) || null;
  return null;
}

function select(sel) {
  selected = sel;
  refreshSelectionUI();
}

function refreshSelectionUI() {
  const none = document.getElementById('selNone');
  const panel = document.getElementById('panel');
  const paramsSource = document.getElementById('paramsSource');
  const paramsLens = document.getElementById('paramsLens');
  const paramsMirror = document.getElementById('paramsMirror');
  const obj = findSelected();
  if (!obj) {
    none.style.display = 'block';
    panel.style.display = 'none';
    return;
  }
  none.style.display = 'none';
  panel.style.display = 'block';
  document.getElementById('selType').textContent = selected.type;
  document.getElementById('selId').textContent = obj.id;

  // pose
  document.getElementById('posX').value = obj.pos.x;
  document.getElementById('posY').value = obj.pos.y;
  document.getElementById('theta').value = obj.theta ?? 0;

  paramsSource.style.display = selected.type === 'source' ? 'block' : 'none';
  paramsLens.style.display = selected.type === 'lens' ? 'block' : 'none';
  paramsMirror.style.display = selected.type === 'mirror' ? 'block' : 'none';

  if (selected.type === 'source') {
    document.getElementById('srcKind').value = obj.type ?? 'point';
    document.getElementById('srcWidth').value = obj.width ?? 0.5;
    document.getElementById('srcWidth').parentElement.style.display = obj.type === 'collimated' ? 'flex' : 'none';
  }
  if (selected.type === 'lens') {
    document.getElementById('lensKind').value = obj.type;
    document.getElementById('lensF').value = obj.f;
    document.getElementById('lensA').value = obj.aperture;
    document.getElementById('lensN1').value = obj.n1 ?? 1.0;
    document.getElementById('lensN2').value = obj.n2 ?? 1.49;
    const showN = obj.type === 'fresnel_facet';
    document.getElementById('lensN1').parentElement.style.display = showN ? 'flex' : 'none';
    document.getElementById('lensN2').parentElement.style.display = showN ? 'flex' : 'none';
  }
  if (selected.type === 'mirror') {
    document.getElementById('mirR').value = obj.R;
    document.getElementById('mirK').value = obj.kappa ?? -1;
    document.getElementById('mirA').value = obj.aperture;
  }
}

function hookField(id, setter) {
  document.getElementById(id).addEventListener('change', (ev) => {
    const obj = findSelected();
    if (!obj) return;
    setter(obj, Number(ev.target.value));
    draw();
  });
}

function hookSelect(id, setter) {
  document.getElementById(id).addEventListener('change', (ev) => {
    const obj = findSelected();
    if (!obj) return;
    setter(obj, ev.target.value);
    refreshSelectionUI();
    draw();
  });
}

hookField('posX', (o, v) => (o.pos.x = v));
hookField('posY', (o, v) => (o.pos.y = v));
hookField('theta', (o, v) => (o.theta = v));

hookSelect('srcKind', (o, v) => {
  o.type = v;
  if (v === 'collimated') {
    if (o.width == null) o.width = 0.5;
    if (o.theta == null) o.theta = 0;
  }
});
hookField('srcWidth', (o, v) => (o.width = v));

hookSelect('lensKind', (o, v) => (o.type = v));
hookField('lensF', (o, v) => (o.f = v));
hookField('lensA', (o, v) => (o.aperture = v));
hookField('lensN1', (o, v) => (o.n1 = v));
hookField('lensN2', (o, v) => (o.n2 = v));
hookField('mirR', (o, v) => (o.R = v));
hookField('mirK', (o, v) => (o.kappa = v));
hookField('mirA', (o, v) => (o.aperture = v));

document.getElementById('btnDelete').onclick = () => {
  if (!selected) return;
  if (selected.type === 'source') scene.sources = scene.sources.filter((s) => s.id !== selected.id);
  if (selected.type === 'lens') scene.lenses = scene.lenses.filter((l) => l.id !== selected.id);
  if (selected.type === 'mirror') scene.mirrors = scene.mirrors.filter((m) => m.id !== selected.id);
  selected = null;
  rays = [];
  analysis = null;
  document.getElementById('analysis').textContent = '';
  refreshSelectionUI();
  draw();
};

// --- Interaction (add/move/pan/zoom) ---
let dragging = false;
let dragMode = null; // 'move' | 'pan'
let dragStart = null;
let dragOrig = null;

function hitTest(world) {
  const r = 0.03; // meters
  const near = (p) => {
    const dx = p.x - world.x;
    const dy = p.y - world.y;
    return dx * dx + dy * dy <= r * r;
  };

  for (const s of scene.sources) if (near(s.pos)) return { type: 'source', id: s.id };
  for (const l of scene.lenses) if (near(l.pos)) return { type: 'lens', id: l.id };
  for (const m of scene.mirrors) if (near(m.pos)) return { type: 'mirror', id: m.id };
  return null;
}

canvas.addEventListener('mousedown', (ev) => {
  resizeCanvas();
  const { sx, sy } = eventToCanvasXY(ev);
  const w = screenToWorld(sx, sy);

  if (ev.button === 2) {
    dragging = true;
    dragMode = 'pan';
    dragStart = { x: sx, y: sy };
    dragOrig = { ...view };
    return;
  }

  if (tool === 'add_source') {
    const id = uid('src');
    const rc = Number(document.getElementById('rayCountNum').value);
    scene.sources.push({ id, type: 'point', pos: { x: w.x, y: w.y }, power: 1.0, ray_count: rc });
    select({ type: 'source', id });
    tool = 'select';
    draw();
    return;
  }

  if (tool === 'add_collimated') {
    const id = uid('src');
    const rc = Number(document.getElementById('rayCountNum').value);
    scene.sources.push({
      id,
      type: 'collimated',
      pos: { x: w.x, y: w.y },
      power: 1.0,
      ray_count: rc,
      theta: 0,
      width: 0.5,
    });
    select({ type: 'source', id });
    tool = 'select';
    draw();
    return;
  }

  const h = hitTest(w);
  if (h) {
    select(h);
    dragging = true;
    dragMode = 'move';
    dragStart = w;
    const obj = findSelected();
    dragOrig = { x: obj.pos.x, y: obj.pos.y };
    draw();
  } else {
    select(null);
    draw();
  }
});

canvas.addEventListener('mousemove', (ev) => {
  resizeCanvas();
  if (!dragging) return;
  const { sx, sy } = eventToCanvasXY(ev);
  const w = screenToWorld(sx, sy);

  if (dragMode === 'pan') {
    view.offsetX = dragOrig.offsetX + (sx - dragStart.x);
    view.offsetY = dragOrig.offsetY + (sy - dragStart.y);
    draw();
    return;
  }
  if (dragMode === 'move') {
    const obj = findSelected();
    if (!obj) return;
    obj.pos.x = dragOrig.x + (w.x - dragStart.x);
    obj.pos.y = dragOrig.y + (w.y - dragStart.y);
    refreshSelectionUI();
    draw();
  }
});

canvas.addEventListener('mouseup', () => {
  dragging = false;
  dragMode = null;
});
canvas.addEventListener('mouseleave', () => {
  dragging = false;
  dragMode = null;
});

canvas.addEventListener('wheel', (ev) => {
  resizeCanvas();
  ev.preventDefault();
  const delta = Math.sign(ev.deltaY);
  const factor = delta > 0 ? 0.9 : 1.1;
  const { sx, sy } = eventToCanvasXY(ev);
  const before = screenToWorld(sx, sy);
  view.scale *= factor;
  // keep cursor world point fixed
  view.offsetX = sx - before.x * view.scale;
  view.offsetY = sy + before.y * view.scale;
  draw();
});

// disable context menu on canvas
canvas.addEventListener('contextmenu', (ev) => ev.preventDefault());

// --- Rendering ---
function drawGrid() {
  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.07)';
  ctx.lineWidth = 1;
  const step = 0.1; // m
  const w0 = screenToWorld(0, canvasCss.h);
  const w1 = screenToWorld(canvasCss.w, 0);
  const xMin = Math.floor(w0.x / step) * step;
  const xMax = Math.ceil(w1.x / step) * step;
  const yMin = Math.floor(w0.y / step) * step;
  const yMax = Math.ceil(w1.y / step) * step;
  for (let x = xMin; x <= xMax; x += step) {
    const a = worldToScreen({ x, y: yMin });
    const b = worldToScreen({ x, y: yMax });
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (let y = yMin; y <= yMax; y += step) {
    const a = worldToScreen({ x: xMin, y });
    const b = worldToScreen({ x: xMax, y });
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  // axes
  ctx.strokeStyle = 'rgba(255,255,255,0.18)';
  const ax0 = worldToScreen({ x: 0, y: yMin });
  const ax1 = worldToScreen({ x: 0, y: yMax });
  ctx.beginPath();
  ctx.moveTo(ax0.x, ax0.y);
  ctx.lineTo(ax1.x, ax1.y);
  ctx.stroke();
  const ay0 = worldToScreen({ x: xMin, y: 0 });
  const ay1 = worldToScreen({ x: xMax, y: 0 });
  ctx.beginPath();
  ctx.moveTo(ay0.x, ay0.y);
  ctx.lineTo(ay1.x, ay1.y);
  ctx.stroke();

  ctx.restore();
}

function drawRays() {
  ctx.save();
  ctx.strokeStyle = 'rgba(255, 255, 120, 0.25)';
  ctx.lineWidth = 1;
  for (const r of rays) {
    const pts = r.points;
    if (!pts || pts.length < 2) continue;
    ctx.beginPath();
    const p0 = worldToScreen({ x: pts[0][0], y: pts[0][1] });
    ctx.moveTo(p0.x, p0.y);
    for (let i = 1; i < pts.length; i++) {
      const p = worldToScreen({ x: pts[i][0], y: pts[i][1] });
      ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  ctx.restore();
}

function drawElementDot(p, color, radiusPx) {
  const s = worldToScreen(p);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(s.x, s.y, radiusPx, 0, Math.PI * 2);
  ctx.fill();
}

function drawLens(l) {
  const c = worldToScreen(l.pos);
  const h = (l.aperture / 2) * view.scale;
  ctx.save();
  ctx.translate(c.x, c.y);
  ctx.rotate(-l.theta);
  ctx.strokeStyle = 'rgba(100, 200, 255, 0.9)';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(0, -h);
  ctx.lineTo(0, h);
  ctx.stroke();
  ctx.restore();
  drawElementDot(l.pos, 'rgba(100,200,255,0.9)', 4);
}

function drawMirror(m) {
  function sagConic(y, R, kappa) {
    // Conic sag in 2D cross-section.
    // Implicit: y^2 - 2R x + (1+kappa) x^2 = 0 (vertex at origin, opens +x)
    const k1 = 1 + kappa;
    if (Math.abs(k1) < 1e-12) {
      // Parabola: y^2 = 2R x
      return (y * y) / (2 * R);
    }
    const disc = R * R - k1 * y * y;
    const s = Math.sqrt(Math.max(0, disc));
    // Pick the near-vertex branch.
    return (R - s) / k1;
  }

  // draw sample points of the conic in local coords
  const c = worldToScreen(m.pos);
  ctx.save();
  ctx.translate(c.x, c.y);
  ctx.rotate(-m.theta);
  ctx.strokeStyle = 'rgba(220, 220, 220, 0.9)';
  ctx.lineWidth = 3;
  ctx.beginPath();
  const r = m.aperture / 2;
  const steps = 80;
  for (let i = 0; i <= steps; i++) {
    const y = -r + (2 * r * i) / steps;
    const x = sagConic(y, m.R, m.kappa ?? -1);
    const sx = x * view.scale;
    const sy = -y * view.scale;
    if (i === 0) ctx.moveTo(sx, sy);
    else ctx.lineTo(sx, sy);
  }
  ctx.stroke();
  ctx.restore();
  drawElementDot(m.pos, 'rgba(220,220,220,0.9)', 4);
}

function drawSources() {
  for (const s of scene.sources) {
    drawElementDot(s.pos, 'rgba(255,140,0,0.95)', 5);
  }
}

function drawFocus() {
  if (!analysis || !analysis.focus) return;
  drawElementDot({ x: analysis.focus[0], y: analysis.focus[1] }, 'rgba(255, 80, 80, 0.95)', 5);
}

function drawSelection() {
  const obj = findSelected();
  if (!obj) return;
  ctx.save();
  ctx.strokeStyle = 'rgba(0,255,140,0.9)';
  ctx.lineWidth = 2;
  const p = worldToScreen(obj.pos);
  ctx.beginPath();
  ctx.arc(p.x, p.y, 10, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function draw() {
  resizeCanvas();
  ctx.clearRect(0, 0, canvasCss.w, canvasCss.h);
  drawGrid();
  drawRays();
  for (const l of scene.lenses) drawLens(l);
  for (const m of scene.mirrors) drawMirror(m);
  drawSources();
  drawFocus();
  drawSelection();
}

// initial
refreshSelectionUI();
draw();

// When layout changes (e.g. analysis panel updates), the canvas CSS size can change without a window resize.
// Observe size changes and keep backing store in sync to prevent stretching.
new ResizeObserver(() => {
  resizeCanvas();
  draw();
}).observe(canvas);

