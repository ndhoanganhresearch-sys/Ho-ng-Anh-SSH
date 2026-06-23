const PptxGenJS = require("pptxgenjs");

const prs = new PptxGenJS();

// === Design System ===
const colors = {
  navy: "0F2A43",
  teal: "0E7C86",
  mint: "27AE60",
  orange: "F2A516",
  white: "FFFFFF",
  bg_light: "F0F4F8",
  text_dark: "1a1a1a",
  code_bg: "1E2A33",
  code_text: "FFFFFF"
};

const fonts = {
  header: "Cambria",
  body: "Calibri",
  code: "Courier New"
};

// === Slide Templates ===
function titleSlide(title, subtitle) {
  const slide = prs.addSlide();
  slide.background = { color: colors.navy };

  // Gradient overlay (simulated with rectangle)
  slide.addShape(prs.ShapeType.rect, {
    x: 0, y: 0, w: 10, h: 7.5,
    fill: { color: colors.navy, transparency: 0 },
    line: { type: "none" }
  });

  // Accent bar
  slide.addShape(prs.ShapeType.rect, {
    x: 0, y: 2.8, w: 10, h: 0.1,
    fill: { color: colors.mint },
    line: { type: "none" }
  });

  slide.addText(title, {
    x: 0.5, y: 2.2, w: 9, h: 1,
    fontSize: 54, bold: true, color: colors.white,
    font: fonts.header
  });

  slide.addText(subtitle, {
    x: 0.5, y: 3.2, w: 9, h: 1.2,
    fontSize: 20, color: colors.mint,
    font: fonts.body
  });
}

function contentSlide(title) {
  const slide = prs.addSlide();
  slide.background = { color: colors.white };

  // Header bar
  slide.addShape(prs.ShapeType.rect, {
    x: 0, y: 0, w: 10, h: 0.7,
    fill: { color: colors.navy },
    line: { type: "none" }
  });

  slide.addText(title, {
    x: 0.5, y: 0.1, w: 9, h: 0.5,
    fontSize: 32, bold: true, color: colors.white,
    font: fonts.header
  });

  return slide;
}

function addBullet(slide, text, x, y, w, h, indent = 0, color = colors.text_dark) {
  slide.addText("• " + text, {
    x: x + indent * 0.3, y: y, w: w - indent * 0.3, h: h,
    fontSize: 13, color: color,
    font: fonts.body, align: "left", valign: "top"
  });
}

function codeBlock(slide, code, x, y, w, h) {
  slide.addShape(prs.ShapeType.rect, {
    x: x, y: y, w: w, h: h,
    fill: { color: colors.code_bg },
    line: { color: colors.teal, width: 2 }
  });

  slide.addText(code, {
    x: x + 0.1, y: y + 0.08, w: w - 0.2, h: h - 0.16,
    fontSize: 9, color: colors.code_text,
    font: fonts.code, align: "left", valign: "top"
  });
}

// ============================================
// SLIDE 1: Title
// ============================================
titleSlide(
  "TLSynth Raycasting Protocol",
  "Creating synthetic ground truth for tunnel deformation validation"
);

// ============================================
// SLIDE 2: What is This Protocol?
// ============================================
{
  const slide = contentSlide("Purpose & Scope");

  const items = [
    "Create synthetic tunnel point clouds with KNOWN deformation",
    "Validate tunnel_analysis tool accuracy (mm-level precision)",
    "Follow TLSynth paper methodology (§3.1-3.5)",
    "Build confidence through 4 validation scenarios",
    "Ensure reproducibility and documentation"
  ];

  let y = 1.1;
  items.forEach((item, i) => {
    const num = i + 1;
    slide.addShape(prs.ShapeType.ellipse, {
      x: 0.5, y: y + 0.02, w: 0.35, h: 0.35,
      fill: { color: colors.teal },
      line: { type: "none" }
    });

    slide.addText(num.toString(), {
      x: 0.5, y: y, w: 0.35, h: 0.35,
      fontSize: 14, bold: true, color: colors.white,
      font: fonts.header, align: "center", valign: "middle"
    });

    addBullet(slide, item, 1.0, y, 8.5, 0.35);
    y += 0.48;
  });

  slide.addNotes(
    "This protocol creates synthetic ground truth data using raycasting. " +
    "We start with clean tunnel mesh, raycast to get T0 baseline, " +
    "inject deformation, raycast again to get Tn, then validate tool accuracy."
  );
}

// ============================================
// SLIDE 3: Key Concepts
// ============================================
{
  const slide = contentSlide("Key Concepts at a Glance");

  const concepts = [
    { label: "Raycasting", def: "Virtual scanning: sphere shoots rays → hits tunnel → point cloud" },
    { label: "Ground Truth", def: "Exact, known deformation values injected into mesh" },
    { label: "T0", def: "Clean reference baseline (no deformation)" },
    { label: "Tn", def: "Monitoring scan with injected deformation" },
    { label: "Validation", def: "Compare tool output vs known ground truth" }
  ];

  let y = 1.1;
  concepts.forEach(c => {
    // Label box
    slide.addShape(prs.ShapeType.roundRect, {
      x: 0.5, y: y, w: 1.8, h: 0.3,
      fill: { color: colors.mint },
      line: { type: "none" }
    });

    slide.addText(c.label, {
      x: 0.6, y: y + 0.04, w: 1.6, h: 0.22,
      fontSize: 11, bold: true, color: colors.white,
      font: fonts.header
    });

    // Definition
    slide.addText(c.def, {
      x: 2.5, y: y, w: 7, h: 0.35,
      fontSize: 11, color: colors.text_dark,
      font: fonts.body, valign: "middle"
    });

    y += 0.48;
  });

  slide.addNotes(
    "Understand core vocabulary: raycasting simulates laser scanning, " +
    "ground truth is known deformation we inject, T0/Tn are temporal states, " +
    "validation checks if tool measures them correctly."
  );
}

// ============================================
// SLIDE 4: Workflow Overview (ASCII)
// ============================================
{
  const slide = contentSlide("3-Phase Workflow");

  const workflow = `CLEAN MESH → Phase A: Raycast T0 → T0.las
                        ↓
                  Phase B: Inject deformation
                        ↓
                  Phase C: Raycast Tn → Tn.las
                        ↓
                  VALIDATION: Compare vs Ground Truth`;

  codeBlock(slide, workflow, 0.5, 1.1, 9, 1.6);

  // Phase boxes
  const phases = [
    { name: "Phase A", color: colors.navy, x: 0.5, desc: "T0 baseline" },
    { name: "Phase B", color: colors.teal, x: 3.5, desc: "Deformation" },
    { name: "Phase C", color: colors.mint, x: 6.5, desc: "Tn monitored" }
  ];

  phases.forEach(p => {
    slide.addShape(prs.ShapeType.rect, {
      x: p.x, y: 3.0, w: 2.8, h: 0.5,
      fill: { color: p.color },
      line: { type: "none" }
    });

    slide.addText(p.name, {
      x: p.x + 0.1, y: 3.05, w: 1.2, h: 0.2,
      fontSize: 12, bold: true, color: colors.white,
      font: fonts.header
    });

    slide.addText(p.desc, {
      x: p.x + 0.1, y: 3.3, w: 2.6, h: 0.2,
      fontSize: 10, color: colors.white,
      font: fonts.body, italic: true
    });
  });

  // Timeline
  slide.addText("T0 raycast (15min) → Deform mesh (30min) → Tn raycast (15min) → Validate (30min)", {
    x: 0.5, y: 4.2, w: 9, h: 0.3,
    fontSize: 11, bold: true, color: colors.teal,
    font: fonts.header
  });

  slide.addText("Total: ~2 hours", {
    x: 0.5, y: 4.6, w: 9, h: 0.3,
    fontSize: 13, bold: true, color: colors.orange,
    font: fonts.header
  });

  slide.addNotes(
    "Workflow is 3 phases plus validation. Phase A: clean baseline. " +
    "Phase B: inject known deformation into mesh. Phase C: scan deformed mesh. " +
    "Validation: load both into tool, compare measurements. Total ~2 hours."
  );
}

// ============================================
// SLIDE 5: Phase A Details
// ============================================
{
  const slide = contentSlide("Phase A: Prepare T0 (Clean Reference)");

  const steps = [
    "1. Load tunnel mesh (16,100 vertices, Tunnel_Lining.blend)",
    "2. Create scanner sphere @ position (0, 10, 3)",
    "3. Raycast: fire 512 rays from sphere vertices",
    "4. Add realistic noise: 5mm + 2mm per 10m distance",
    "5. Export: T0.las (364 hit points)",
    "6. Record metadata: radius (3.0m), eccentricity, ovality"
  ];

  let y = 1.1;
  steps.forEach(step => {
    addBullet(slide, step, 0.7, y, 8.5, 0.35);
    y += 0.42;
  });

  // Box: T0 output
  slide.addShape(prs.ShapeType.rect, {
    x: 0.5, y: 4.0, w: 9, h: 0.9,
    fill: { color: colors.bg_light },
    line: { color: colors.navy, width: 1 }
  });

  slide.addText("Output: T0.las", {
    x: 0.7, y: 4.08, w: 4, h: 0.25,
    fontSize: 12, bold: true, color: colors.navy,
    font: fonts.header
  });

  slide.addText("~364 points | Radius: 3.0000m | e: 0.1mm | Clean, no deformation", {
    x: 0.7, y: 4.35, w: 8.6, h: 0.45,
    fontSize: 10, color: colors.text_dark,
    font: fonts.body
  });

  slide.addNotes(
    "Phase A creates the clean baseline. Load Blender tunnel mesh, " +
    "create UV sphere at scanner location, raycast 512 rays, " +
    "add realistic noise, export T0.las. Record metadata for comparison later."
  );
}

// ============================================
// SLIDE 6: Phase B Details
// ============================================
{
  const slide = contentSlide("Phase B: Inject Deformation");

  slide.addText("Define ground truth deformation prescription:", {
    x: 0.5, y: 1.1, w: 9, h: 0.25,
    fontSize: 12, bold: true, color: colors.navy,
    font: fonts.header
  });

  const defCode = `Crown settlement:   -7 mm @ chainage 20m
Sidewall convergence: -5 mm @ chainage 45m
Local damage:        -15 mm @ chainage 65m`;

  codeBlock(slide, defCode, 0.5, 1.5, 9, 1.0);

  slide.addText("Modify tunnel mesh:", {
    x: 0.5, y: 2.7, w: 9, h: 0.25,
    fontSize: 12, bold: true, color: colors.navy,
    font: fonts.header
  });

  const meshCode = `for vertex in mesh:
  if at_chainage(20m): vertex.z -= 7mm  # Crown down
  if at_chainage(45m): vertex.xy *= 0.995  # Convergence
  if at_chainage(65m): vertex.xyz -= 15mm  # Damage`;

  codeBlock(slide, meshCode, 0.5, 3.1, 9, 1.4);

  slide.addText("✓ Validate deformation on mesh ✓ Record ground_truth.csv", {
    x: 0.5, y: 4.7, w: 9, h: 0.3,
    fontSize: 11, bold: true, color: colors.mint,
    font: fonts.body
  });

  slide.addNotes(
    "Phase B injects known deformation into tunnel mesh. " +
    "Define exact amounts and locations (crown, convergence, damage). " +
    "Modify vertices using Blender script or Python. " +
    "Record all ground truth values before proceeding to Phase C."
  );
}

// ============================================
// SLIDE 7: Phase C Details
// ============================================
{
  const slide = contentSlide("Phase C: Raycast Deformed Tunnel");

  slide.addText("CRITICAL: Use IDENTICAL scanner setup from Phase A", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 12, bold: true, color: colors.orange,
    font: fonts.header
  });

  const rayCode = `# Same scanner location & sphere subdivision
scanner_location = (0, 10, 3)  # MUST match T0
scanner_sphere = UV_Sphere(subdivisions=32x16)  # MUST match T0

# Load DEFORMED mesh (different from Phase A)
tunnel_mesh = load("tunnel_deformed.blend")

# Raycast with same noise model
for vertex in scanner_sphere:
  hit = raycast(vertex, tunnel_mesh)
  noise = 5 + (distance / 10) * 2  # Same noise as T0
  Tn_points.append(hit + gaussian_noise)

export Tn.las`;

  codeBlock(slide, rayCode, 0.5, 1.5, 9, 2.5);

  slide.addShape(prs.ShapeType.rect, {
    x: 0.5, y: 4.2, w: 9, h: 0.8,
    fill: { color: colors.mint },
    line: { type: "none" }
  });

  slide.addText("Output: Tn.las | Same point count as T0 | Deformation measurable", {
    x: 0.7, y: 4.35, w: 8.6, h: 0.5,
    fontSize: 11, bold: true, color: colors.white,
    font: fonts.header, valign: "middle"
  });

  slide.addNotes(
    "Phase C raycasts the deformed mesh using identical scanner setup. " +
    "Only difference: target mesh changed to deformed version. " +
    "Same scanner location, same ray count, same noise = differences are ONLY from deformation."
  );
}

// ============================================
// SLIDE 8: Validation Process
// ============================================
{
  const slide = contentSlide("Validation: Compare Measurements");

  // Step-by-step
  const steps = [
    "1. Load T0.las into tunnel_analysis tool → get baseline metrics",
    "2. Load Tn.las into tool → measure deformation",
    "3. Tool reports: crown_settle, convergence, local_damage (mm)",
    "4. Compare tool output vs ground_truth.csv",
    "5. Calculate error: |measured - prescribed|",
    "6. Assert: error < ±1mm → PASS ✓"
  ];

  let y = 1.1;
  steps.forEach(step => {
    addBullet(slide, step, 0.7, y, 8.5, 0.35);
    y += 0.42;
  });

  // Success/fail boxes
  slide.addShape(prs.ShapeType.rect, {
    x: 0.5, y: 4.0, w: 4.4, h: 0.7,
    fill: { color: colors.mint },
    line: { type: "none" }
  });

  slide.addText("✓ PASS: error < ±1mm\nTool is VALIDATED", {
    x: 0.65, y: 4.1, w: 4.1, h: 0.5,
    fontSize: 11, bold: true, color: colors.white,
    font: fonts.body, align: "center"
  });

  slide.addShape(prs.ShapeType.rect, {
    x: 5.1, y: 4.0, w: 4.4, h: 0.7,
    fill: { color: colors.orange },
    line: { type: "none" }
  });

  slide.addText("✗ FAIL: error > ±5mm\nDebug registration/noise", {
    x: 5.25, y: 4.1, w: 4.1, h: 0.5,
    fontSize: 11, bold: true, color: colors.white,
    font: fonts.body, align: "center"
  });

  slide.addNotes(
    "Load both scans into tool, measure deformation, compare vs ground truth. " +
    "If error is small, tool is accurate. If large, debug the pipeline: " +
    "check registration, noise level, fitting algorithm."
  );
}

// ============================================
// SLIDE 9: Validation Scenarios
// ============================================
{
  const slide = contentSlide("Build Confidence: 4 Test Scenarios");

  const scenarios = [
    { num: "A", name: "No Deformation", detail: "T0 → T0. Expect: 0mm error." },
    { num: "B", name: "Single Metric", detail: "Crown-only, convergence-only, damage-only." },
    { num: "C", name: "Combined", detail: "All 3 deformations (realistic, stressful)." },
    { num: "D", name: "Offset Scanner", detail: "Different scanner location. Still measurable." }
  ];

  let y = 1.1;
  scenarios.forEach(s => {
    // Scenario box
    slide.addShape(prs.ShapeType.rect, {
      x: 0.5, y: y, w: 9, h: 0.55,
      fill: { color: colors.bg_light },
      line: { color: colors.teal, width: 1 }
    });

    // Letter circle
    slide.addShape(prs.ShapeType.ellipse, {
      x: 0.65, y: y + 0.1, w: 0.35, h: 0.35,
      fill: { color: colors.teal },
      line: { type: "none" }
    });

    slide.addText(s.num, {
      x: 0.65, y: y + 0.1, w: 0.35, h: 0.35,
      fontSize: 12, bold: true, color: colors.white,
      font: fonts.header, align: "center", valign: "middle"
    });

    // Name & detail
    slide.addText(s.name, {
      x: 1.15, y: y + 0.05, w: 7.8, h: 0.2,
      fontSize: 11, bold: true, color: colors.navy,
      font: fonts.header
    });

    slide.addText(s.detail, {
      x: 1.15, y: y + 0.28, w: 7.8, h: 0.2,
      fontSize: 10, color: colors.text_dark,
      font: fonts.body, italic: true
    });

    y += 0.7;
  });

  slide.addText("Record all results → validation_results.csv", {
    x: 0.5, y: 4.5, w: 9, h: 0.3,
    fontSize: 11, bold: true, color: colors.mint,
    font: fonts.header
  });

  slide.addNotes(
    "Test protocol with 4 scenarios to build robustness. Scenario A: noise floor. " +
    "Scenario B: isolated measurements. Scenario C: realistic stress test. " +
    "Scenario D: generalization. Pass all 4 = confident validation."
  );
}

// ============================================
// SLIDE 10: Timeline & Checklist
// ============================================
{
  const slide = contentSlide("Implementation Timeline");

  const tasks = [
    { task: "T0 raycast", time: "15 min" },
    { task: "Deform mesh (B1-B3)", time: "30 min" },
    { task: "Tn raycast", time: "15 min" },
    { task: "Load & validate tool", time: "30 min" },
    { task: "Error analysis", time: "10 min" },
    { task: "Repeat scenarios B,C,D", time: "60 min (optional)" }
  ];

  // Table header
  slide.addShape(prs.ShapeType.rect, {
    x: 1.0, y: 1.1, w: 8, h: 0.35,
    fill: { color: colors.navy },
    line: { type: "none" }
  });

  slide.addText("Task", {
    x: 1.2, y: 1.15, w: 5, h: 0.25,
    fontSize: 11, bold: true, color: colors.white,
    font: fonts.header
  });

  slide.addText("Duration", {
    x: 6.5, y: 1.15, w: 2.3, h: 0.25,
    fontSize: 11, bold: true, color: colors.white,
    font: fonts.header
  });

  // Table rows
  let y = 1.5;
  tasks.forEach((t, i) => {
    const bg = i % 2 === 0 ? colors.bg_light : colors.white;
    slide.addShape(prs.ShapeType.rect, {
      x: 1.0, y: y, w: 8, h: 0.35,
      fill: { color: bg },
      line: { type: "none" }
    });

    slide.addText(t.task, {
      x: 1.2, y: y + 0.05, w: 5, h: 0.25,
      fontSize: 10, color: colors.text_dark,
      font: fonts.body
    });

    slide.addText(t.time, {
      x: 6.5, y: y + 0.05, w: 2.3, h: 0.25,
      fontSize: 10, color: colors.text_dark,
      font: fonts.body, align: "right"
    });

    y += 0.35;
  });

  // Total
  slide.addShape(prs.ShapeType.rect, {
    x: 1.0, y: y, w: 8, h: 0.4,
    fill: { color: colors.orange },
    line: { type: "none" }
  });

  slide.addText("TOTAL", {
    x: 1.2, y: y + 0.05, w: 5, h: 0.3,
    fontSize: 11, bold: true, color: colors.white,
    font: fonts.header
  });

  slide.addText("~2 hours (Scenarios A only)", {
    x: 6.5, y: y + 0.05, w: 2.3, h: 0.3,
    fontSize: 11, bold: true, color: colors.white,
    font: fonts.header, align: "right"
  });

  slide.addNotes(
    "Timeline to complete full protocol: ~2 hours for Scenario A baseline validation. " +
    "Optional: repeat with scenarios B/C/D for additional robustness testing."
  );
}

// ============================================
// SLIDE 11: Key Metrics
// ============================================
{
  const slide = contentSlide("Validation Metrics & Expected Accuracy");

  slide.addText("mm-Level Accuracy Target:", {
    x: 0.5, y: 1.1, w: 9, h: 0.3,
    fontSize: 13, bold: true, color: colors.navy,
    font: fonts.header
  });

  const metrics = [
    "Crown settlement: |measured - prescribed| < 1.0 mm",
    "Sidewall convergence: |measured - prescribed| < 1.0 mm",
    "Local damage: |measured - prescribed| < 2.0 mm",
    "Mean Absolute Error (MAE): < 0.6 mm (baseline from SSL T0→T5)",
    "Max error across all metrics: < 2.5 mm"
  ];

  let y = 1.6;
  metrics.forEach(m => {
    addBullet(slide, m, 0.7, y, 8.5, 0.35);
    y += 0.45;
  });

  slide.addShape(prs.ShapeType.rect, {
    x: 0.5, y: 4.2, w: 9, h: 1.0,
    fill: { color: colors.mint },
    line: { type: "none" }
  });

  slide.addText("✓ SUCCESS: If protocol achieves < ±1mm error", {
    x: 0.7, y: 4.3, w: 8.6, h: 0.35,
    fontSize: 12, bold: true, color: colors.white,
    font: fonts.header
  });

  slide.addText("Tool is validated for mm-level deformation measurement", {
    x: 0.7, y: 4.68, w: 8.6, h: 0.35,
    fontSize: 11, color: colors.white,
    font: fonts.body
  });

  slide.addNotes(
    "Accuracy target: mm-level precision. Crown and convergence < 1mm each. " +
    "Damage < 2mm. Overall MAE < 0.6mm (historical baseline). " +
    "Success = error < ±1mm for all metrics."
  );
}

// ============================================
// SLIDE 12: Summary & Next Steps
// ============================================
{
  const slide = contentSlide("Summary: What We Build");

  slide.addText("Deliverables:", {
    x: 0.5, y: 1.0, w: 9, h: 0.3,
    fontSize: 13, bold: true, color: colors.navy,
    font: fonts.header
  });

  const delivers = [
    "T0.las: Clean reference point cloud (364 points, no deformation)",
    "Tn.las: Deformed monitoring scan (known -7mm crown, -5mm convergence)",
    "ground_truth.csv: Prescribed deformation values",
    "validation_results.csv: Tool measurements vs ground truth",
    "Validation report: Error analysis and confidence metrics"
  ];

  let y = 1.5;
  delivers.forEach(d => {
    addBullet(slide, d, 0.7, y, 8.5, 0.35);
    y += 0.45;
  });

  slide.addText("Outcome: mm-level accuracy validation of tunnel_analysis tool", {
    x: 0.5, y: 4.0, w: 9, h: 0.4,
    fontSize: 12, bold: true, color: colors.mint,
    font: fonts.header
  });

  slide.addText("Based on TLSynth paper methodology + 2 hours of work", {
    x: 0.5, y: 4.6, w: 9, h: 0.3,
    fontSize: 11, italic: true, color: colors.text_dark,
    font: fonts.body
  });

  slide.addNotes(
    "Final deliverables: T0.las, Tn.las, metadata, validation report. " +
    "Outcome: tool validation at mm-level accuracy. " +
    "Ready to deploy for field tunnel monitoring."
  );
}

// ============================================
// Save
// ============================================
const path = require("path");
const fs = require("fs");

try {
  prs.writeFile("TLSynth_GroundTruth_v2.pptx");
  const outputPath = path.join(__dirname, "TLSynth_GroundTruth_v2.pptx");
  if (fs.existsSync(outputPath)) {
    const size = fs.statSync(outputPath).size;
    console.log(`✓ Created: TLSynth_GroundTruth_v2.pptx (${(size/1024).toFixed(1)} KB)`);
  }
} catch (e) {
  console.error("✗ Error:", e.message);
}
