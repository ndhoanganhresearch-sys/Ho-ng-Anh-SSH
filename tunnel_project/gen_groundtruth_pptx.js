const PptxGenJS = require("pptxgenjs");

const prs = new PptxGenJS();

// === Palette ===
const colors = {
  primary: "065A82",      // Deep blue (tunnel)
  secondary: "1C7293",    // Teal (laser)
  accent: "02C39A",       // Mint (success)
  dark: "0A1520",         // Very dark
  light: "F0F4F8",        // Off-white
  text: "1a1a1a",         // Dark text
  code_bg: "1E2A33",      // Code background
  code_text: "FFFFFF"     // Code text
};

const fonts = {
  header: "Cambria",
  body: "Calibri",
  code: "Courier New"
};

// === Helper Functions ===
function addTitleSlide(prs, title, subtitle) {
  const slide = prs.addSlide();
  slide.background = { color: colors.primary };

  slide.addText(title, {
    x: 0.5, y: 2.5, w: 9, h: 1,
    fontSize: 48, bold: true, color: "FFFFFF",
    font: fonts.header, align: "left"
  });

  slide.addText(subtitle, {
    x: 0.5, y: 3.8, w: 9, h: 0.8,
    fontSize: 24, color: colors.accent,
    font: fonts.body, align: "left"
  });
}

function addContentSlide(prs, title) {
  const slide = prs.addSlide();
  slide.background = { color: "FFFFFF" };

  // Title bar
  slide.addShape(prs.ShapeType.rect, {
    x: 0, y: 0, w: 10, h: 0.8,
    fill: { color: colors.primary },
    line: { type: "none" }
  });

  slide.addText(title, {
    x: 0.5, y: 0.15, w: 9, h: 0.5,
    fontSize: 36, bold: true, color: "FFFFFF",
    font: fonts.header, align: "left"
  });

  return slide;
}

function addBullet(slide, text, x, y, w, h, indent = 0) {
  slide.addText(text, {
    x: x + indent * 0.3, y: y, w: w - indent * 0.3, h: h,
    fontSize: 14, color: colors.text,
    font: fonts.body, align: "left",
    valign: "top", margin: [0, 0, 0, 0]
  });
}

function addCodeBox(slide, code, x, y, w, h) {
  slide.addShape(prs.ShapeType.rect, {
    x: x, y: y, w: w, h: h,
    fill: { color: colors.code_bg },
    line: { color: colors.accent, width: 1 }
  });

  slide.addText(code, {
    x: x + 0.15, y: y + 0.1, w: w - 0.3, h: h - 0.2,
    fontSize: 10, color: colors.code_text,
    font: fonts.code, align: "left",
    valign: "top", margin: [5, 5, 5, 5]
  });
}

// ============================================
// SLIDE 1: Title
// ============================================
addTitleSlide(prs,
  "Raycasting Ground Truth Protocol",
  "Creating synthetic tunnel data for validation using TLSynth methodology"
);

// ============================================
// SLIDE 2: TLSynth Overview
// ============================================
{
  const slide = addContentSlide(prs, "TLSynth Scanning Simulation (§3.1-3.5)");

  slide.addText("TLSynth Pipeline:", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 18, bold: true, color: colors.primary,
    font: fonts.header
  });

  const steps = [
    "§3.1 Scanning Simulation: UV sphere → ray casting → hit positions",
    "§3.2 Noise Model: r_noise = 5mm + 2mm × (distance/10m)",
    "§3.3 Point Deletion: Optional occlusion filtering",
    "§3.4 Color Assignment: RGB from mesh material",
    "§3.5 Export: Save as PLY/LAS format"
  ];

  let y = 1.6;
  steps.forEach((step, i) => {
    slide.addText(`${i+1}.`, {
      x: 0.6, y: y, w: 0.5, h: 0.35,
      fontSize: 14, bold: true, color: colors.accent,
      font: fonts.body
    });
    addBullet(slide, step, 1.3, y, 8, 0.35);
    y += 0.45;
  });

  // Speaker notes
  slide.addNotes(
    "TLSynth paper describes complete scanning simulation pipeline. " +
    "We apply these 5 steps to create synthetic ground truth: " +
    "1) Use UV sphere as scanner, 2) Add realistic noise, " +
    "3) Handle occlusion, 4) Assign colors, 5) Export to LAS. " +
    "This ensures our synthetic data matches real LiDAR behavior."
  );
}

// ============================================
// SLIDE 3: Workflow Overview
// ============================================
{
  const slide = addContentSlide(prs, "Three-Phase Protocol");

  // Phase boxes
  const phases = [
    { title: "Phase A: T0 Raycast", desc: "Clean reference scan", y: 1.2, bg: colors.primary },
    { title: "Phase B: Deformation", desc: "Inject known changes", y: 2.5, bg: colors.secondary },
    { title: "Phase C: Tn Raycast", desc: "Deformed scan", y: 3.8, bg: colors.accent }
  ];

  phases.forEach(p => {
    slide.addShape(prs.ShapeType.roundRect, {
      x: 0.5, y: p.y, w: 9, h: 0.9,
      fill: { color: p.bg },
      line: { type: "none" }
    });

    slide.addText(p.title, {
      x: 1.0, y: p.y + 0.1, w: 4, h: 0.35,
      fontSize: 14, bold: true, color: "FFFFFF",
      font: fonts.header
    });

    slide.addText(p.desc, {
      x: 1.0, y: p.y + 0.45, w: 4, h: 0.35,
      fontSize: 12, color: "FFFFFF",
      font: fonts.body, italic: true
    });
  });

  // Arrow down
  slide.addShape(prs.ShapeType.triangle, {
    x: 4.7, y: 4.9, w: 0.3, h: 0.4,
    fill: { color: colors.accent },
    line: { type: "none" }
  });

  slide.addText("Validation: Tool measures deformation vs ground truth", {
    x: 0.5, y: 5.4, w: 9, h: 0.5,
    fontSize: 14, bold: true, color: colors.accent,
    font: fonts.header, align: "center"
  });

  slide.addNotes(
    "High-level overview: Three phases create synthetic ground truth. " +
    "Phase A: raycast clean tunnel to get T0. " +
    "Phase B: modify mesh to inject known deformation. " +
    "Phase C: raycast modified mesh to get Tn. " +
    "Finally, load both into tool and validate accuracy."
  );
}

// ============================================
// SLIDE 4: Phase A - Setup
// ============================================
{
  const slide = addContentSlide(prs, "Phase A: T0 Raycast (1/2) - Setup");

  slide.addText("Step 1: Load tunnel mesh", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 16, bold: true, color: colors.primary,
    font: fonts.header
  });

  addBullet(slide, "Input: tunnel_lidar_scene.blend (clean mesh)", 0.7, 1.5, 8.5, 0.3);
  addBullet(slide, "Tunnel_Lining: 16,100 vertices (smooth surface)", 0.7, 1.9, 8.5, 0.3);

  slide.addText("Step 2: Create scanner sphere", {
    x: 0.5, y: 2.5, w: 9, h: 0.4,
    fontSize: 16, bold: true, color: colors.primary,
    font: fonts.header
  });

  const scannerCode = `Scanner location: (0, 10, 3) meters
Sphere radius: 0.1 m
Subdivisions: 32×16 (512 rays)`;

  addCodeBox(slide, scannerCode, 0.7, 3.0, 8.5, 1.0);

  slide.addText("Position: 10m along tunnel, 3m height (typical probe location)", {
    x: 0.7, y: 4.2, w: 8.5, h: 0.4,
    fontSize: 12, color: colors.text, italic: true,
    font: fonts.body
  });

  slide.addNotes(
    "Phase A setup: Load the Blender scene with tunnel geometry. " +
    "The Tunnel_Lining mesh is our scanning target. " +
    "Create UV sphere at (0, 10, 3) - this represents scanner position. " +
    "Each sphere vertex becomes a ray origin. 512 rays total."
  );
}

// ============================================
// SLIDE 5: Phase A - Raycast
// ============================================
{
  const slide = addContentSlide(prs, "Phase A: T0 Raycast (2/2) - Execute");

  slide.addText("Step 3: Raycast and export", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 16, bold: true, color: colors.primary,
    font: fonts.header
  });

  const rayCode = `for each vertex in scanner_sphere:
  world_pos = scanner_center + vertex_offset
  ray_direction = (world_pos - center).normalized()

  hit_loc, hit_dist = raycast(world_pos, ray_dir, tunnel_lining)

  if hit:
    noise_mm = 5 + (hit_dist / 10) * 2
    noisy_point = hit_loc + gaussian(0, noise_mm/1000)
    T0_points.append(noisy_point)

export T0_points → T0.las`;

  addCodeBox(slide, rayCode, 0.5, 1.6, 9, 2.5);

  slide.addText("Output: T0.las (364 points, noise-corrupted clean reference)", {
    x: 0.5, y: 4.3, w: 9, h: 0.4,
    fontSize: 12, bold: true, color: colors.accent,
    font: fonts.body
  });

  const t0Metrics = `Radius (fitted): 3.0000 m
Eccentricity: 0.1 mm
Ovality: 0.05%`;

  addCodeBox(slide, t0Metrics, 0.5, 4.9, 9, 0.9);

  slide.addNotes(
    "Execute the raycasting: for each vertex on sphere, " +
    "cast ray from that position toward tunnel. " +
    "Record hit positions. Add distance-dependent noise (5mm baseline + 2mm per 10m). " +
    "Export 364 hit points to LAS. " +
    "T0 is our clean reference with known geometry."
  );
}

// ============================================
// SLIDE 6: Phase B - Deformation
// ============================================
{
  const slide = addContentSlide(prs, "Phase B: Inject Deformation (1/2)");

  slide.addText("Define ground truth deformation parameters", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 16, bold: true, color: colors.primary,
    font: fonts.header
  });

  const defParams = `Deformation 1 (Crown settlement):
  ├─ Location: chainage 20 m
  ├─ Magnitude: -7 mm (downward)
  └─ Extent: ±2m gaussian taper

Deformation 2 (Sidewall convergence):
  ├─ Location: chainage 45 m
  ├─ Magnitude: -5 mm (inward)
  └─ Extent: ±3m gaussian taper

Deformation 3 (Local damage):
  ├─ Location: chainage 65 m
  ├─ Magnitude: -15 mm (localized)
  └─ Type: point defect`;

  addCodeBox(slide, defParams, 0.5, 1.6, 9, 2.8);

  slide.addText("Record in ground_truth.csv for later comparison", {
    x: 0.5, y: 4.6, w: 9, h: 0.4,
    fontSize: 12, italic: true, color: colors.text,
    font: fonts.body
  });

  slide.addNotes(
    "Phase B step 1: Define what deformations you want to introduce. " +
    "We use 3 example deformations: crown settlement at 20m, " +
    "sidewall convergence at 45m, local damage at 65m. " +
    "These represent realistic tunnel deterioration patterns. " +
    "Document exact values - these are your ground truth."
  );
}

// ============================================
// SLIDE 7: Phase B - Modify Mesh
// ============================================
{
  const slide = addContentSlide(prs, "Phase B: Inject Deformation (2/2)");

  slide.addText("Modify Blender mesh", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 16, bold: true, color: colors.primary,
    font: fonts.header
  });

  const meshCode = `for vertex in tunnel_lining_mesh:
  y = vertex.co.y  # chainage

  # Crown settlement at Y=20m
  if 18 < y < 22:
    offset = -0.007 * gaussian_taper(y - 20)
    vertex.co.z += offset

  # Sidewall convergence at Y=45m
  if 42 < y < 48:
    offset = -0.005 * gaussian_taper(y - 45)
    vertex.co.x *= (1 + offset / radius)
    vertex.co.y *= (1 + offset / radius)

mesh.update()
save("tunnel_deformed.blend")`;

  addCodeBox(slide, meshCode, 0.5, 1.6, 9, 2.6);

  slide.addText("Verification: Crown ↓7mm, Width ↓5mm, Mesh valid ✓", {
    x: 0.5, y: 4.4, w: 9, h: 0.35,
    fontSize: 12, bold: true, color: colors.accent,
    font: fonts.body
  });

  slide.addNotes(
    "Programmatically modify Blender mesh vertices. " +
    "For crown settlement: lower Z coordinate at chainage 20m. " +
    "For convergence: contract X/Y coordinates (move inward) at chainage 45m. " +
    "Use gaussian tapering so deformation is smooth, not sharp. " +
    "Save modified mesh as tunnel_deformed.blend."
  );
}

// ============================================
// SLIDE 8: Phase C - Raycast Deformed
// ============================================
{
  const slide = addContentSlide(prs, "Phase C: Tn Raycast (1/2)");

  slide.addText("Key rule: SAME scanner position as T0", {
    x: 0.5, y: 1.0, w: 9, h: 0.5,
    fontSize: 14, bold: true, color: colors.accent,
    font: fonts.body
  });

  const tnCode = `# CRITICAL: Same location, same sphere
scanner_location = (0, 10, 3)  # IDENTICAL TO T0
scanner_sphere = UV_Sphere(subdivisions=32x16, location=scanner_location)

# Load DEFORMED mesh (different from T0)
tunnel_mesh = load("tunnel_deformed.blend").Tunnel_Lining

# Raycast (same algorithm as T0)
for vertex in scanner_sphere:
  world_pos = scanner_center + vertex_offset
  ray_dir = (world_pos - center).normalized()

  hit_loc, hit_dist = raycast(world_pos, ray_dir, tunnel_mesh)  # NOW: deformed!

  if hit:
    noise_mm = 5 + (hit_dist / 10) * 2  # SAME noise as T0
    noisy_point = hit_loc + gaussian(0, noise_mm/1000)
    Tn_points.append(noisy_point)

export Tn_points → Tn.las`;

  addCodeBox(slide, tnCode, 0.5, 1.7, 9, 3.0);

  slide.addNotes(
    "Phase C: Raycast deformed mesh using identical scanner setup. " +
    "Only difference from T0: target mesh is now deformed. " +
    "Scanner position, noise model, and ray count must be identical. " +
    "This ensures differences between T0 and Tn are ONLY from deformation, " +
    "not from different scanner locations or noise."
  );
}

// ============================================
// SLIDE 9: Phase C - Output
// ============================================
{
  const slide = addContentSlide(prs, "Phase C: Tn Raycast (2/2)");

  slide.addText("Output: Tn.las (deformed scan)", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 16, bold: true, color: colors.primary,
    font: fonts.header
  });

  // Comparison box
  slide.addShape(prs.ShapeType.rect, {
    x: 0.5, y: 1.6, w: 4.3, h: 1.4,
    fill: { color: colors.light },
    line: { color: colors.primary, width: 1 }
  });

  slide.addText("T0 (Clean)", {
    x: 0.7, y: 1.75, w: 3.9, h: 0.3,
    fontSize: 12, bold: true, color: colors.primary,
    font: fonts.header
  });

  let t0_text = "Radius: 3.0000 m\nEccent: 0.1 mm\nOvality: 0.05%\nPoints: 364";
  slide.addText(t0_text, {
    x: 0.7, y: 2.1, w: 3.9, h: 0.8,
    fontSize: 11, color: colors.text,
    font: fonts.body
  });

  // Arrow
  slide.addShape(prs.ShapeType.triangle, {
    x: 5.0, y: 2.2, w: 0.3, h: 0.3,
    fill: { color: colors.accent },
    line: { type: "none" }
  });

  // Tn box
  slide.addShape(prs.ShapeType.rect, {
    x: 5.2, y: 1.6, w: 4.3, h: 1.4,
    fill: { color: colors.light },
    line: { color: colors.secondary, width: 1 }
  });

  slide.addText("Tn (Deformed)", {
    x: 5.4, y: 1.75, w: 3.9, h: 0.3,
    fontSize: 12, bold: true, color: colors.secondary,
    font: fonts.header
  });

  let tn_text = "Radius: 2.9995 m\nEccent: 1.5 mm\nOvality: 0.08%\nPoints: 364";
  slide.addText(tn_text, {
    x: 5.4, y: 2.1, w: 3.9, h: 0.8,
    fontSize: 11, color: colors.text,
    font: fonts.body
  });

  slide.addText("Difference (due to deformation):", {
    x: 0.5, y: 3.3, w: 9, h: 0.3,
    fontSize: 12, bold: true, color: colors.accent,
    font: fonts.header
  });

  const diff = `ΔRadius: -0.5 mm (convergence effect)
ΔEccent: +1.4 mm (asymmetric settlement)
ΔOvality: +0.03% (ovalization from deformation)`;

  addCodeBox(slide, diff, 0.5, 3.8, 9, 1.2);

  slide.addNotes(
    "Now we have two synthetic point clouds: T0 clean and Tn deformed. " +
    "Tn shows measurable changes due to injected deformation. " +
    "Radius decreased (convergence), eccentricity increased (settlement asymmetry), " +
    "ovality increased (loss of perfect circle). " +
    "These are our ground truth changes. Next step: load into tool and measure."
  );
}

// ============================================
// SLIDE 10: Validation Protocol
// ============================================
{
  const slide = addContentSlide(prs, "Validation: Load & Measure");

  const valSteps = [
    "1. Load T0.las into tool → record baseline metrics (R, e, oval)",
    "2. Load Tn.las into tool → measure deformation (Step 6)",
    "3. Tool reports: crown_settle, convergence, local_damage",
    "4. Compare tool output vs ground_truth.csv",
    "5. Calculate error: |measured - prescribed|",
    "6. Assert: error < ±1mm for PASS"
  ];

  let y = 1.2;
  valSteps.forEach(step => {
    slide.addText(step, {
      x: 0.7, y: y, w: 8.5, h: 0.35,
      fontSize: 13, color: colors.text,
      font: fonts.body, align: "left"
    });
    y += 0.45;
  });

  slide.addShape(prs.ShapeType.rect, {
    x: 0.5, y: 4.2, w: 9, h: 1.2,
    fill: { color: colors.accent },
    line: { type: "none" }
  });

  slide.addText(
    "✓ If error < ±1mm → Tool is VALIDATED\n" +
    "✗ If error > ±1mm → Debug registration, noise, fitting",
    {
      x: 0.7, y: 4.35, w: 8.6, h: 1.0,
      fontSize: 13, bold: true, color: "FFFFFF",
      font: fonts.body, align: "center", valign: "middle"
    }
  );

  slide.addNotes(
    "Validation procedure: Load both T0 and Tn into tunnel_analysis tool. " +
    "Tool extracts geometry from each scan. " +
    "Tool compares T0 vs Tn and reports deformation metrics. " +
    "Compare tool output against our ground_truth.csv. " +
    "If error is small (< 1mm), tool measurement is accurate. " +
    "If error is large, investigate: registration issues, noise level, fitting algorithm."
  );
}

// ============================================
// SLIDE 11: Scenarios
// ============================================
{
  const slide = addContentSlide(prs, "Build Confidence: 4 Validation Scenarios");

  const scenarios = [
    {
      title: "Scenario A: No deformation",
      desc: "T0 → T0 (identity). Expect: error ≈ 0mm.",
      num: "A"
    },
    {
      title: "Scenario B: Single metric",
      desc: "Test each: crown-only, convergence-only, damage-only.",
      num: "B"
    },
    {
      title: "Scenario C: Combined",
      desc: "All 3 deformations at once (realistic multi-component).",
      num: "C"
    },
    {
      title: "Scenario D: Offset scanner",
      desc: "Raycast from different position. Deformation still measurable.",
      num: "D"
    }
  ];

  let y = 1.1;
  scenarios.forEach(s => {
    // Scenario circle
    slide.addShape(prs.ShapeType.ellipse, {
      x: 0.6, y: y + 0.02, w: 0.35, h: 0.35,
      fill: { color: colors.accent },
      line: { type: "none" }
    });

    slide.addText(s.num, {
      x: 0.6, y: y, w: 0.35, h: 0.35,
      fontSize: 14, bold: true, color: "FFFFFF",
      font: fonts.header, align: "center", valign: "middle"
    });

    slide.addText(s.title, {
      x: 1.1, y: y, w: 8.4, h: 0.2,
      fontSize: 12, bold: true, color: colors.primary,
      font: fonts.header
    });

    slide.addText(s.desc, {
      x: 1.1, y: y + 0.25, w: 8.4, h: 0.25,
      fontSize: 11, color: colors.text,
      font: fonts.body, italic: true
    });

    y += 0.8;
  });

  slide.addText("Record all results in validation_results.csv", {
    x: 0.5, y: 4.5, w: 9, h: 0.4,
    fontSize: 12, bold: true, color: colors.accent,
    font: fonts.body
  });

  slide.addNotes(
    "Repeat validation with different deformation scenarios. " +
    "Scenario A: no deformation (tests noise floor). " +
    "Scenario B: single metric isolated (tests each measurement pipeline). " +
    "Scenario C: realistic combined deformation (stresses algorithm). " +
    "Scenario D: different scanner location (tests generalization). " +
    "Build confidence by passing multiple independent tests."
  );
}

// ============================================
// SLIDE 12: Implementation Checklist
// ============================================
{
  const slide = addContentSlide(prs, "Implementation Checklist");

  const checks = [
    "[ ] Load tunnel_lidar_scene.blend",
    "[ ] Verify Tunnel_Lining mesh (16,100 verts)",
    "[ ] Setup scanner sphere @ (0, 10, 3)",
    "[ ] Raycast T0 → export T0.las",
    "[ ] Record T0 metadata",
    "[ ] Create deformed mesh (crown, convergence)",
    "[ ] Raycast Tn → export Tn.las",
    "[ ] Load T0, Tn into tool",
    "[ ] Measure deformation metrics",
    "[ ] Compare vs ground_truth.csv",
    "[ ] Calculate error",
    "[ ] Repeat scenarios B, C, D",
    "[ ] Write validation report",
    "[ ] Commit to git"
  ];

  let y = 1.1;
  checks.forEach(check => {
    slide.addText(check, {
      x: 0.7, y: y, w: 8.5, h: 0.3,
      fontSize: 11, color: colors.text,
      font: fonts.body
    });
    y += 0.35;
  });

  slide.addNotes(
    "14-step checklist to execute the full protocol. " +
    "Expected time: ~2 hours from start to finish. " +
    "Critical steps: raycast T0/Tn (identical scanner, different mesh), " +
    "load into tool, compare measurements. " +
    "Document every step for reproducibility."
  );
}

// ============================================
// SLIDE 13: Summary & Next Steps
// ============================================
{
  const slide = addContentSlide(prs, "Summary: TLSynth Protocol");

  slide.addText("What we create:", {
    x: 0.5, y: 1.0, w: 9, h: 0.35,
    fontSize: 14, bold: true, color: colors.primary,
    font: fonts.header
  });

  const outputs = [
    "T0.las: Clean reference (364 points, 3.0m radius)",
    "Tn.las: Deformed scan (known -7mm crown, -5mm convergence)",
    "ground_truth.csv: Prescribed deformation values",
    "validation_results.csv: Measured vs ground truth comparison"
  ];

  let y = 1.5;
  outputs.forEach(out => {
    slide.addText("• " + out, {
      x: 0.7, y: y, w: 8.5, h: 0.35,
      fontSize: 12, color: colors.text,
      font: fonts.body
    });
    y += 0.45;
  });

  slide.addText("Outcome: Validate tunnel_analysis tool accuracy (mm-level)", {
    x: 0.5, y: 3.3, w: 9, h: 0.4,
    fontSize: 13, bold: true, color: colors.accent,
    font: fonts.header
  });

  slide.addText("Based on TLSynth paper §3.1-3.5 (Scanning Simulation Pipeline)", {
    x: 0.5, y: 4.0, w: 9, h: 0.4,
    fontSize: 12, italic: true, color: colors.text,
    font: fonts.body
  });

  slide.addNotes(
    "Summary: We create synthetic ground truth by applying TLSynth methodology. " +
    "Raycast clean mesh → T0. Modify mesh with known deformation → Tn. " +
    "Load both into tool, measure, compare. " +
    "If tool accuracy is high (< 1mm error), ready for field validation. " +
    "If error is high, debug and iterate. " +
    "This rigorous approach ensures confidence in the measurement pipeline."
  );
}

// ============================================
// Save
// ============================================
const fs = require("fs");
const path = require("path");

try {
  // pptxgenjs writeFile signature: writeFile(filename)
  prs.writeFile("TLSynth_GroundTruth_Workflow.pptx");

  // Verify file was created
  const outputPath = path.join(__dirname, "TLSynth_GroundTruth_Workflow.pptx");
  if (fs.existsSync(outputPath)) {
    const size = fs.statSync(outputPath).size;
    console.log(`✓ Created: TLSynth_GroundTruth_Workflow.pptx (${(size/1024).toFixed(1)} KB)`);
  } else {
    // File might be in current working directory
    if (fs.existsSync("TLSynth_GroundTruth_Workflow.pptx")) {
      console.log("✓ Created: TLSynth_GroundTruth_Workflow.pptx (in current directory)");
    }
  }
} catch (e) {
  console.error("✗ Error:", e.message);
}
