const PptxGenJS = require('pptxgenjs');

const prs = new PptxGenJS();
prs.defineLayout({ name: 'STD', width: 10, height: 7.5 });
prs.layout = 'STD';

const colors = {
  primary: '065A82',    // deep blue
  secondary: '1C7293',  // teal
  accent: '21295C',     // midnight
  light: 'F2F2F2',      // off-white
  text: '212121',       // black
  good: '2E7D32',       // green (pass)
  ice: 'CADCFC'         // ice blue (on dark)
};

// ---- raycast motif helpers ----------------------------------------------
// Draw a single ray as a line between two points (handles pptxgenjs flip).
function addRay(slide, x1, y1, x2, y2, color, w) {
  const dx = x2 - x1, dy = y2 - y1;
  const opts = {
    x: Math.min(x1, x2), y: Math.min(y1, y2),
    w: Math.abs(dx), h: Math.abs(dy),
    line: { color: color, width: w }
  };
  if ((dx > 0 && dy < 0) || (dx < 0 && dy > 0)) opts.flipV = true;
  slide.addShape('line', opts);
}

// Scanner station + fan of rays + tunnel arch, centered at (sx, sy).
function raycastMotif(slide, sx, sy, r, color, lineW, nRays) {
  // tunnel arch (top semicircle)
  slide.addShape('arc', {
    x: sx - r, y: sy - r, w: 2 * r, h: 2 * r,
    angleRange: [180, 360], line: { color: color, width: lineW }
  });
  // fan of rays from the station up to the arch
  const a0 = 18, a1 = 162;
  for (let i = 0; i < nRays; i++) {
    const a = (a0 + (a1 - a0) * i / (nRays - 1)) * Math.PI / 180;
    addRay(slide, sx, sy, sx + r * Math.cos(a), sy - r * Math.sin(a), color, lineW * 0.6);
  }
  // station dot
  const d = r * 0.12;
  slide.addShape('ellipse', { x: sx - d, y: sy - d, w: 2 * d, h: 2 * d, fill: { color: color } });
}

// Small corner emblem repeated on content slides.
function cornerMotif(slide, color) {
  raycastMotif(slide, 9.15, 0.95, 0.34, color, 1.2, 7);
}

// ---- Slide 1: Title ------------------------------------------------------
let s1 = prs.addSlide();
s1.background = { color: colors.primary };
raycastMotif(s1, 5.0, 2.35, 0.95, 'FFFFFF', 1.5, 11);
s1.addText('Raycasting Ground Truth Validation', {
  x: 0.5, y: 2.9, w: 9, h: 1.3,
  fontSize: 46, bold: true, color: 'FFFFFF', align: 'center', fontFace: 'Cambria'
});
s1.addText('Synthetic LiDAR for Tool Step 6 (M3C2) Verification', {
  x: 0.5, y: 4.3, w: 9, h: 0.6,
  fontSize: 26, color: colors.ice, align: 'center', fontFace: 'Calibri'
});
s1.addText('2026-06-29', {
  x: 0.5, y: 6.6, w: 9, h: 0.4,
  fontSize: 13, color: colors.ice, align: 'center', fontFace: 'Calibri'
});

// ---- Slide 2: Problem ----------------------------------------------------
let s2 = prs.addSlide();
s2.background = { color: colors.light };
cornerMotif(s2, colors.secondary);
s2.addText('Initial State (Phase A/B/C v1)', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 34, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const issues = [
  'Scripts targeted imaginary tunnel (straight, R=3.0m, 1 scanner, -7/-5/-15mm)',
  'Never actually run end-to-end',
  'Config copy-paste risks ("must match byte-for-byte")',
  'Real dataset blender_lidar_t0t5 is curved (R=500m), 3 TLS stations, progressive T1-T5'
];
issues.forEach((issue, i) => {
  s2.addText(issue, {
    x: 0.8, y: 1.5 + i * 0.95, w: 8.6, h: 0.8,
    fontSize: 14, color: colors.text, fontFace: 'Calibri',
    bullet: { code: '2022', indent: 18 }
  });
});

// ---- Slide 3: Solution ---------------------------------------------------
let s3 = prs.addSlide();
s3.background = { color: colors.light };
cornerMotif(s3, colors.secondary);
s3.addText('Realign to Real Geometry', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 34, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const solutions = [
  'Verify .blend via Blender MCP: R=500m curve, radius 4.256m, 3 stations @ arc-len 10/40/70m',
  'Build single engine (raycast_tunnel_epochs.py) for T0 & Tn — same code path, no drift',
  'Deform in local cross-section frame (ground_truth.csv magnitudes: crown -45, side -35, local -40mm @ T5)'
];
solutions.forEach((sol, i) => {
  s3.addText(sol, {
    x: 0.8, y: 1.5 + i * 1.1, w: 8.6, h: 1,
    fontSize: 14, color: colors.text, fontFace: 'Calibri',
    bullet: { code: '2022', indent: 18 }
  });
});

// ---- Slide 4: Architecture ----------------------------------------------
let s4 = prs.addSlide();
s4.background = { color: colors.light };
cornerMotif(s4, colors.secondary);
s4.addText('Single Engine, Two Validators', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 34, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const cols = [
  { x: 0.5, title: 'Engine', items: ['tools/raycast_tunnel_epochs.py', 'Blender bpy + BVHTree', 'T0 clean, Tn deformed', 'Same 3 stations & noise', 'Export T0-T5 .txt/.json'] },
  { x: 3.5, title: 'Validator 1', items: ['phase_c_validate.py', 'Window-mean in frame', 'Checks raycast fidelity', 'Lower bound (bias low)', 'Regenerable'] },
  { x: 6.5, title: 'Validator 2', items: ['crosscheck_tool_step6.py', 'Call Step 6 M3C2 (prod)', 'Independent check', 'Mm-level accuracy', 'FINAL TRUTH'] }
];
cols.forEach(col => {
  s4.addShape('roundRect', {
    x: col.x, y: 1.5, w: 2.8, h: 4.4, rectRadius: 0.08,
    fill: { color: 'FFFFFF' }, line: { color: colors.secondary, width: 1 },
    shadow: { type: 'outer', color: 'BFBFBF', blur: 4, offset: 2, angle: 90, opacity: 0.4 }
  });
  s4.addText(col.title, {
    x: col.x, y: 1.7, w: 2.8, h: 0.4,
    fontSize: 17, bold: true, color: colors.secondary, align: 'center', fontFace: 'Calibri'
  });
  col.items.forEach((item, i) => {
    s4.addText('• ' + item, {
      x: col.x + 0.2, y: 2.4 + i * 0.62, w: 2.45, h: 0.55,
      fontSize: 11, color: colors.text, fontFace: 'Calibri'
    });
  });
});

// ---- Slide 5: Raycast Fidelity table ------------------------------------
let s5 = prs.addSlide();
s5.background = { color: colors.light };
cornerMotif(s5, colors.secondary);
s5.addText('Validator 1: Window-Mean (Raycast Fidelity)', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 24, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const hdr1 = ['Epoch', 'Crown err', 'Side err', 'Local err', 'MAE'].map(t => ({
  text: t, options: { bold: true, color: 'FFFFFF', fill: colors.secondary }
}));
const body1 = [
  ['T1', '0.3', '0.0', '0.0', '0.1mm'],
  ['T2', '0.2', '0.0', '0.0', '0.1mm'],
  ['T3', '0.1', '0.1', '2.2', '0.8mm'],
  ['T4', '1.4', '1.6', '3.6', '2.2mm'],
  ['T5', '1.9', '2.3', '5.5', '3.2mm']
];
const tbl1 = [hdr1].concat(body1.map((r, ri) => r.map(c => ({
  text: c, options: { fill: ri % 2 ? 'FFFFFF' : 'E7EEF2' } }))));
s5.addTable(tbl1, { x: 0.7, y: 1.45, w: 8.6, h: 3.6, colW: [1.3, 1.5, 1.5, 1.5, 1.3], fontSize: 12, fontFace: 'Calibri', valign: 'middle' });
s5.addText('Window-mean is lower bound; narrow features read low', {
  x: 0.7, y: 5.4, w: 8.6, h: 0.4,
  fontSize: 11, color: colors.text, italic: true, fontFace: 'Calibri'
});

// ---- Slide 6: Tool M3C2 table -------------------------------------------
let s6 = prs.addSlide();
s6.background = { color: colors.light };
cornerMotif(s6, colors.good);
s6.addText('Validator 2: Tool M3C2 (py4dgeo) — FINAL TRUTH', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 23, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const hdr2 = ['Epoch', 'Crown err', 'Side err', 'Local err', 'Peak'].map(t => ({
  text: t, options: { bold: true, color: 'FFFFFF', fill: colors.good }
}));
const body2 = [
  ['T1', '1.0', '0.0', '0.0', 'M3C2'],
  ['T2', '0.9', '0.4', '0.0', 'M3C2'],
  ['T3', '0.8', '0.7', '1.0', 'M3C2'],
  ['T4', '1.4', '0.1', '1.3', 'M3C2'],
  ['T5', '1.3', '0.1', '2.4', 'M3C2']
];
const tbl2 = [hdr2].concat(body2.map((r, ri) => r.map(c => ({
  text: c, options: { fill: ri % 2 ? 'FFFFFF' : 'E6EFE7' } }))));
s6.addTable(tbl2, { x: 0.7, y: 1.45, w: 8.6, h: 3.6, colW: [1.3, 1.5, 1.5, 1.5, 1.3], fontSize: 12, fontFace: 'Calibri', valign: 'middle' });
s6.addText('Tool recovers GT ≤ 2.4mm peak — mm-level accurate', {
  x: 0.7, y: 5.4, w: 8.6, h: 0.4,
  fontSize: 11, color: colors.good, bold: true, fontFace: 'Calibri'
});

// ---- Slide 7: Ground truth by epoch -------------------------------------
let s7 = prs.addSlide();
s7.background = { color: colors.light };
cornerMotif(s7, colors.secondary);
s7.addText('Ground Truth by Epoch', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 34, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const epochs = [
  { title: 'Crown Settlement @ 20m', vals: 'T0: 0   T1: -5   T2: -12   T3: -20   T4: -30   T5: -45 mm', peak: 45 },
  { title: 'Sidewall Convergence @ 45m', vals: 'T0: 0   T1: 0   T2: -5   T3: -12   T4: -22   T5: -35 mm', peak: 35 },
  { title: 'Local Damage @ 65m', vals: 'T0: 0   T1: 0   T2: 0   T3: -15   T4: -25   T5: -40 mm', peak: 40 }
];
const series = [[0, 5, 12, 20, 30, 45], [0, 0, 5, 12, 22, 35], [0, 0, 0, 15, 25, 40]];
epochs.forEach((ep, i) => {
  const y = 1.35 + i * 1.65;
  s7.addText(ep.title, {
    x: 0.7, y: y, w: 8.6, h: 0.4,
    fontSize: 15, bold: true, color: colors.secondary, fontFace: 'Calibri'
  });
  s7.addText(ep.vals, {
    x: 0.9, y: y + 0.45, w: 8.4, h: 0.4,
    fontSize: 13, color: colors.text, fontFace: 'Calibri'
  });
  // mini progression bars (T0..T5)
  series[i].forEach((v, k) => {
    const bx = 0.95 + k * 0.62;
    const bh = 0.08 + (v / 45) * 0.55;
    s7.addShape('rect', {
      x: bx, y: y + 1.45 - bh, w: 0.42, h: bh,
      fill: { color: v >= ep.peak ? colors.primary : colors.secondary }
    });
  });
});

// ---- Slide 8: Technical validation --------------------------------------
let s8 = prs.addSlide();
s8.background = { color: colors.light };
cornerMotif(s8, colors.secondary);
s8.addText('Technical Validation', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 34, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const qa = [
  'Geometry verified via Blender MCP inspection (R=500, radius 4.25m, curve centerline)',
  'Path robustness: scripts resolve via __file__ (run from any cwd)',
  'Full series T0-T5 generated (112k-112.5k points/epoch, ~4.2MB each)',
  'Two independent validators (window-mean + tool M3C2)',
  '25MB regenerable point clouds gitignored; metadata/CSV tracked'
];
qa.forEach((q, i) => {
  const y = 1.45 + i * 0.85;
  s8.addShape('ellipse', { x: 0.8, y: y, w: 0.36, h: 0.36, fill: { color: colors.good } });
  s8.addText('✓', { x: 0.8, y: y, w: 0.36, h: 0.36, fontSize: 16, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle', fontFace: 'Calibri' });
  s8.addText(q, {
    x: 1.35, y: y - 0.05, w: 8.1, h: 0.5,
    fontSize: 13, color: colors.text, valign: 'middle', fontFace: 'Calibri'
  });
});

// ---- Slide 9: Conclusions (dark) ----------------------------------------
let s9 = prs.addSlide();
s9.background = { color: colors.accent };
raycastMotif(s9, 9.1, 1.0, 0.4, colors.ice, 1.3, 7);
s9.addText('Conclusions', {
  x: 0.5, y: 0.5, w: 8.3, h: 0.7,
  fontSize: 38, bold: true, color: 'FFFFFF', fontFace: 'Cambria'
});
const conclusions = [
  'Tool Step 6 (py4dgeo M3C2) is mm-level accurate on curved tunnel geometry',
  'Raycasting ground truth validates the measurement pipeline end-to-end',
  'Single engine architecture eliminates config-drift risk',
  'Ready for next phase: higher ray density (0.5°) or real-world validation'
];
conclusions.forEach((c, i) => {
  const y = 1.9 + i * 1.05;
  s9.addShape('ellipse', { x: 0.8, y: y + 0.04, w: 0.18, h: 0.18, fill: { color: colors.ice } });
  s9.addText(c, {
    x: 1.25, y: y - 0.12, w: 8.0, h: 0.7,
    fontSize: 16, color: 'EAF0FA', valign: 'middle', fontFace: 'Calibri'
  });
});

// ---- Slide 10: Delivery summary -----------------------------------------
let s10 = prs.addSlide();
s10.background = { color: colors.light };
cornerMotif(s10, colors.secondary);
s10.addText('Delivery Summary', {
  x: 0.5, y: 0.4, w: 8.3, h: 0.6,
  fontSize: 34, bold: true, color: colors.primary, fontFace: 'Cambria'
});
const phases = [
  { x: 0.7, label: 'Phase A', desc: 'Clean T0\n(engine verified)' },
  { x: 3.5, label: 'Phase B', desc: 'Deformed T1-T5\n(series generated)' },
  { x: 6.3, label: 'Phase C', desc: 'Validation\n(2 validators, PASS)' }
];
phases.forEach(p => {
  s10.addShape('roundRect', {
    x: p.x, y: 1.7, w: 2.4, h: 1.9, rectRadius: 0.08,
    fill: { color: colors.secondary }, line: { color: colors.primary, width: 1 }
  });
  s10.addText(p.label, {
    x: p.x, y: 1.95, w: 2.4, h: 0.5,
    fontSize: 18, bold: true, color: 'FFFFFF', align: 'center', fontFace: 'Cambria'
  });
  s10.addText(p.desc, {
    x: p.x + 0.1, y: 2.5, w: 2.2, h: 0.9,
    fontSize: 12, color: colors.ice, align: 'center', fontFace: 'Calibri'
  });
});
// arrows between phases
[3.12, 5.92].forEach(ax => {
  s10.addShape('rightArrow', {
    x: ax, y: 2.42, w: 0.36, h: 0.45, fill: { color: colors.primary }, line: { color: colors.primary, width: 1 }
  });
});
s10.addText('Scripts: 3 main (engine, 2 validators) + plotter + cross-check     |     Data: T0-T5 JSON, validation CSV, series plot', {
  x: 0.7, y: 4.5, w: 8.6, h: 0.8,
  fontSize: 12, color: colors.text, align: 'center', fontFace: 'Calibri'
});

prs.writeFile({ fileName: 'C:/Users/ssl/Desktop/Code Python/data python cusor/tunnel_project/Raycasting_Validation_Report_v2.pptx' });
console.log('Presentation created successfully!');
