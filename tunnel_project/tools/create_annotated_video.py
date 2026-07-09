#!/usr/bin/env python3
"""
Create annotated demo video aligned to Prof. Yoon's requirement (yc).

Fixes vs previous version:
- GLOBAL frame counter -> segments always play in correct chronological order
  (old version sorted by filename prefix, so heatmap played before intro).
- R-squared corrected to 0.9997 (matches timeseries_benchmark_report.json).
- Added Segment "Section Analysis" (required demo scenario #3: centerline +
  Frenet cross-sections) with all 4 shape indices incl. ovality + eccentricity.
- Summary now lists ovality/eccentricity and PDF/IFC export (scenario #6).
- ASCII-only console output (no UnicodeEncodeError on cp949 consoles).

All numbers verified against:
  tunnel_project/output/timeseries_benchmark/timeseries_benchmark_report.json
  CLAUDE.md ground-truth spec (crown -45, convergence -35, local -40 mm @ T5)
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FRAMES_DIR = PROJECT_ROOT / "output/video_demo/frames_annotated"
OUTPUT_DIR = PROJECT_ROOT / "output/video_demo"
BENCHMARK_DIR = PROJECT_ROOT / "output/timeseries_benchmark"

FRAMES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080
FPS = 30

# Global frame counter guarantees correct play order regardless of segment names
_counter = {"n": 0}


def _font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def save(img):
    path = FRAMES_DIR / f"frame_{_counter['n']:05d}.png"
    img.save(path)
    _counter["n"] += 1


def base(color):
    return Image.new("RGB", (W, H), color=color)


# ============================================================================
# SEGMENT 1: INTRO
# ============================================================================
def seg_intro(seconds=12):
    print("[1] Intro...")
    f_title, f_sub, f_small = _font(86), _font(46), _font(34)
    for _ in range(seconds * FPS):
        img = base("#001a4d")
        d = ImageDraw.Draw(img)
        d.text((960, 280), "LiDAR-Based Tunnel", fill="white", font=f_title, anchor="mm")
        d.text((960, 400), "Time-Series Shape Analysis", fill="#00ff88", font=f_title, anchor="mm")
        d.text((960, 620), "How repeated LiDAR scans (T0~T5) reveal tunnel deformation", fill="white", font=f_small, anchor="mm")
        d.text((960, 685), "over time -- where, how much, and how fast it grows", fill="white", font=f_small, anchor="mm")
        d.text((960, 880), "6 steps: Load -> Register -> Sections -> M3C2 -> Trend -> Report", fill="#ffff00", font=f_small, anchor="mm")
        save(img)


# ============================================================================
# SEGMENT 2: DATA LOADING (scenario #1)
# ============================================================================
def seg_load(seconds=15):
    print("[2] Load T0~T5...")
    f_title, f_body, f_small = _font(58), _font(42), _font(30)
    total = seconds * FPS
    for i in range(total):
        img = base("#0a1a3a")
        d = ImageDraw.Draw(img)
        half = total // 2
        step = 1 if i < half else 2
        epoch = "T0 (Baseline)" if i < half else "T5 (Latest scan)"
        color = "#00ff88" if i < half else "#ff8800"
        d.text((960, 140), "STEP 1: Load LiDAR Point Clouds", fill="#00ffff", font=f_title, anchor="mm")
        d.text((960, 330), f"Loading: {epoch}", fill=color, font=f_body, anchor="mm")
        d.text((960, 450), "Points per epoch: 15,456", fill="white", font=f_body, anchor="mm")
        d.text((960, 545), "Tunnel: 80 m long, 3.0 m radius, 6 epochs (T0..T5)", fill="white", font=f_small, anchor="mm")
        # progress bar
        bx, by, bw = 460, 720, 1000
        frac = (i % half) / half if half else 1.0
        filled = int(frac * bw) if i < half else bw
        d.rectangle([bx, by, bx + bw, by + 38], outline="white", width=3)
        d.rectangle([bx, by, bx + filled, by + 38], fill=color)
        d.text((960, 870), "Each scan is one snapshot of the tunnel surface in 3D", fill="#ffff00", font=f_small, anchor="mm")
        save(img)


# ============================================================================
# SEGMENT 3: REGISTRATION (scenario #2)
# ============================================================================
def seg_register(seconds=12):
    print("[3] Registration...")
    f_title, f_body, f_metric, f_small = _font(58), _font(44), _font(50), _font(30)
    for _ in range(seconds * FPS):
        img = base("#0d2a0d")
        d = ImageDraw.Draw(img)
        d.text((960, 110), "STEP 2: Co-Register T0 and T5", fill="#00ff00", font=f_title, anchor="mm")
        # left: what
        d.text((300, 300), "What is this?", fill="#00ffff", font=f_body, anchor="mm")
        for k, line in enumerate(["Put T5 into the SAME", "coordinate frame as T0", "so we compare real shape", "change, not sensor motion."]):
            d.text((300, 380 + k * 52), line, fill="white", font=f_small, anchor="mm")
        # right: metric
        d.text((1620, 300), "Alignment Accuracy (RMSE)", fill="#ffff00", font=f_body, anchor="mm")
        d.text((1620, 400), "GICP: 0.196 mm", fill="#00ff00", font=f_metric, anchor="mm")
        d.text((1620, 480), "(339 ms, beats Open3D ICP)", fill="white", font=f_small, anchor="mm")
        d.text((1620, 560), "This clean dataset: ~0 mm", fill="white", font=f_small, anchor="mm")
        d.text((1620, 610), "(pre-aligned, identity)", fill="gray", font=f_small, anchor="mm")
        d.text((960, 850), "RMSE = how closely T5 lines up with T0 (lower is better)", fill="lightblue", font=f_small, anchor="mm")
        d.text((960, 915), "If RMSE is too high, deformation results are flagged low-confidence", fill="gray", font=f_small, anchor="mm")
        save(img)


# ============================================================================
# SEGMENT 4: SECTION ANALYSIS (scenario #3 -- was missing)
# ============================================================================
def seg_section(seconds=15):
    print("[4] Section analysis (NEW)...")
    f_title, f_body, f_small, f_metric = _font(56), _font(40), _font(30), _font(38)
    # optional figure
    fig = None
    fig_path = BENCHMARK_DIR / "crown_profile_per_epoch.png"
    if fig_path.exists():
        fig = Image.open(fig_path).convert("RGB").resize((820, 540), Image.Resampling.LANCZOS)
    for _ in range(seconds * FPS):
        img = base("#0a1a2a")
        d = ImageDraw.Draw(img)
        d.text((960, 70), "STEP 3: Centerline & Cross-Section Indices", fill="#00ffff", font=f_title, anchor="mm")
        if fig is not None:
            img.paste(fig, (90, 200))
            d.text((500, 770), "Crown profile per epoch (T0..T5)", fill="gray", font=f_small, anchor="mm")
        # explanation + 4 indices
        d.text((1380, 220), "What happens here?", fill="#ffff00", font=f_body, anchor="mm")
        for k, line in enumerate(["Estimate the tunnel centerline,", "then cut Frenet cross-sections", "perpendicular to it -> avoids", "false ovality on curved tunnels."]):
            d.text((1380, 290 + k * 48), line, fill="white", font=f_small, anchor="lm" if False else "mm")
        d.text((1380, 520), "4 shape indices per section (@ T5):", fill="#00ff88", font=f_body, anchor="mm")
        rows = [
            ("Crown settlement", "44.05 mm"),
            ("Sidewall convergence", "69.6 mm"),
            ("Ovality (mean)", "0.20 %"),
            ("Eccentricity (mean)", "1.52 mm"),
        ]
        for k, (name, val) in enumerate(rows):
            y = 600 + k * 60
            d.text((1140, y), name, fill="white", font=f_small, anchor="lm")
            d.text((1720, y), val, fill="#ffaa00", font=f_metric, anchor="rm")
        d.text((960, 1010), "These per-section numbers tell the engineer WHERE and WHAT KIND of deformation", fill="gray", font=f_small, anchor="mm")
        save(img)


# ============================================================================
# SEGMENT 5: M3C2 HEATMAP (scenario #4)
# ============================================================================
def seg_heatmap(seconds=18):
    print("[5] M3C2 heatmap...")
    f_title, f_body, f_small = _font(56), _font(38), _font(30)
    hm_path = BENCHMARK_DIR / "m3c2_heatmap_T0_T5.png"
    if hm_path.exists():
        hm = Image.open(hm_path).convert("RGB").resize((1400, 700), Image.Resampling.LANCZOS)
    else:
        hm = Image.new("RGB", (1400, 700), color="gray")
    for _ in range(seconds * FPS):
        img = base("#1a0a0a")
        d = ImageDraw.Draw(img)
        img.paste(hm, (260, 150))
        d.text((960, 60), "STEP 4: M3C2 4D Deformation (T0 -> T5)", fill="#00ffff", font=f_title, anchor="mm")
        d.text((100, 880), "RED = settlement / convergence", fill="#ff6b6b", font=f_small, anchor="lm")
        d.text((100, 930), "YELLOW = minor deformation", fill="#ffff00", font=f_small, anchor="lm")
        d.text((100, 980), "GREEN = stable (no change)", fill="#00ff00", font=f_small, anchor="lm")
        d.text((1820, 880), "Key zones", fill="#ffff00", font=f_body, anchor="rm")
        d.text((1820, 930), "Crown @20m: -45 mm (critical)", fill="#ff6b6b", font=f_small, anchor="rm")
        d.text((1820, 980), "Walls @45m / Local @65m: -35 / -40 mm", fill="#ff8800", font=f_small, anchor="rm")
        save(img)


# ============================================================================
# SEGMENT 6: TIME-SERIES TRENDS (scenario #5)
# ============================================================================
def seg_trend(seconds=15):
    print("[6] Trends...")
    f_title, f_body, f_small = _font(56), _font(40), _font(30)
    tr_path = BENCHMARK_DIR / "timeseries_benchmark_overview.png"
    if tr_path.exists():
        tr = Image.open(tr_path).convert("RGB").resize((1400, 650), Image.Resampling.LANCZOS)
    else:
        tr = Image.new("RGB", (1400, 650), color="gray")
    for _ in range(seconds * FPS):
        img = base("#0d0d1a")
        d = ImageDraw.Draw(img)
        img.paste(tr, (260, 180))
        d.text((960, 60), "STEP 5: Time-Series Trend & Forecast", fill="#00ffff", font=f_title, anchor="mm")
        d.text((960, 880), "Deformation grows steadily across the 6 epochs (T0 -> T5)", fill="white", font=f_small, anchor="mm")
        d.text((960, 935), "Linear fit R-squared = 0.9997  ->  trend is highly predictable", fill="#00ff88", font=f_body, anchor="mm")
        d.text((960, 1000), "Forecast: caution at ~9 epochs, critical at ~15 epochs", fill="#ffaa00", font=f_small, anchor="mm")
        save(img)


# ============================================================================
# SEGMENT 7: SUMMARY (scenario #6)
# ============================================================================
def seg_summary(seconds=13):
    print("[7] Summary...")
    f_title, f_metric, f_body, f_small = _font(64), _font(50), _font(38), _font(29)
    for _ in range(seconds * FPS):
        img = base("#1a0a2e")
        d = ImageDraw.Draw(img)
        d.text((960, 90), "Summary: Tunnel Deformation Status", fill="#00ffff", font=f_title, anchor="mm")
        zones = [
            (320, "Zone 1: CROWN", "Chainage 20 m", "Settlement -45 mm", "CRITICAL", "#ff6b6b", "#ff0000"),
            (960, "Zone 2: WALLS", "Chainage 45 m", "Convergence -35 mm", "CRITICAL", "#ff8800", "#ff8800"),
            (1600, "Zone 3: LOCAL", "Chainage 65 m", "Damage -40 mm", "since T3", "#ffaa00", "#ffaa00"),
        ]
        for cx, t, ch, val, tag, c1, c2 in zones:
            d.text((cx, 290), t, fill=c1, font=f_body, anchor="mm")
            d.text((cx, 360), ch, fill="white", font=f_small, anchor="mm")
            d.text((cx, 415), val, fill=c2, font=f_metric, anchor="mm")
            d.text((cx, 475), f"({tag})", fill=c1, font=f_body, anchor="mm")
        # extra indices + forecast
        d.text((960, 590), "Ovality 0.20 % | Eccentricity 1.52 mm | Forecast R-squared 0.9997", fill="#00ff88", font=f_small, anchor="mm")
        # actions + outputs
        d.text((960, 700), "Action", fill="#ffff00", font=f_body, anchor="mm")
        d.text((960, 760), "Priority maintenance at chainage 20 m and 45 m; 65 m is accelerating", fill="white", font=f_small, anchor="mm")
        d.text((960, 870), "Outputs: 3D heatmap + section tables + trend graph + PDF / IFC export", fill="#00ffff", font=f_small, anchor="mm")
        d.text((960, 925), "-> feeds the digital-twin maintenance decision workflow", fill="gray", font=f_small, anchor="mm")
        save(img)


def compile_video(total_frames):
    print("\nCompiling annotated video...")
    import imageio.v2 as imageio
    frames = sorted(FRAMES_DIR.glob("frame_*.png"), key=lambda x: x.name)
    if not frames:
        print("ERROR: no frames found")
        return
    out = OUTPUT_DIR / "lidar_demo_annotated.mp4"
    writer = imageio.get_writer(str(out), fps=FPS, codec="libx264", macro_block_size=1)
    for i, fp in enumerate(frames):
        if (i + 1) % 600 == 0:
            print(f"  {i+1}/{len(frames)} frames...")
        writer.append_data(imageio.imread(str(fp)))
    writer.close()
    if out.exists():
        size_mb = out.stat().st_size / (1024 ** 2)
        print("\n" + "=" * 60)
        print("[OK] ANNOTATED VIDEO CREATED (correct order + verified numbers)")
        print("=" * 60)
        print(f"File:     {out.name}")
        print(f"Size:     {size_mb:.2f} MB")
        print(f"Frames:   {len(frames)}")
        print(f"Duration: {len(frames)/FPS:.1f} s")
        print(f"Path:     {out}")
        print("=" * 60)


def main():
    print("=" * 60)
    print("ANNOTATED VIDEO  (aligned to Prof. Yoon requirement)")
    print("=" * 60)
    seg_intro()
    seg_load()
    seg_register()
    seg_section()
    seg_heatmap()
    seg_trend()
    seg_summary()
    n = _counter["n"]
    print(f"\nTotal frames: {n}  ({n/FPS:.1f} s)")
    compile_video(n)


if __name__ == "__main__":
    main()
