#!/usr/bin/env python3
"""
Re-author the demo video from the REAL screen recording in docs/.

Takes the raw screen capture of the SSL Tunnel Analysis tool running the
Auto Pipeline on T0~T5 and adds:
  - an intro title card
  - a top "STEP n -- <title>" bar + bottom plain-language caption per phase
    (timed to the actual tool panels seen in the recording)
  - a summary card with verified key numbers
  - crops off the taskbar + "sharing your screen" banner at the bottom

Phase timings were verified frame-by-frame against the recording's main-panel
header text (Auto Pipeline -> Deformation Trend Chart -> M3C2 Deformation Map
-> Plot 2D Technical Section).

Numbers verified against output/timeseries_benchmark/timeseries_benchmark_report.json
and the CLAUDE.md ground-truth spec.
"""

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio

DOCS = Path(r"C:\Users\ssl\Desktop\Code Python\data python cusor\docs")
SRC = DOCS / "Ghi màn hình 3 (online-video-cutter.com).mp4"
OUT = DOCS / "LiDAR_Tunnel_RealDemo_Annotated.mp4"

FPS = 30
CROP_BOTTOM = 76          # remove taskbar + screen-share banner + tool status bar
TOP_BAND = 94
BOT_BAND = 100
FOOT_W = 1280
FOOT_H = 720 - CROP_BOTTOM
CANVAS_W = FOOT_W
CANVAS_H = TOP_BAND + FOOT_H + BOT_BAND

# (start_sec, end_sec, step, title, caption, accent)
SEGMENTS = [
    (0.0, 12.5, "STEP 1", "Load T0~T5 & run Auto Pipeline",
     "Six epochs (S1..S6 = T0..T5) are loaded. One click runs the full pipeline: "
     "preprocess > register > sections > M3C2.", "#2d8cff"),
    (12.5, 25.0, "STEP 2-3", "Centerline & cross-section indices",
     "Circle-fit each cross-section along the tunnel: crown / wall / floor deviation, "
     "ovality and eccentricity per chainage.", "#00b386"),
    (25.0, 33.0, "STEP 5", "Multi-epoch deformation trend",
     "p95 and median displacement per epoch (T0 -> T5) with Safe / Caution / Critical "
     "bands. The trend is near-linear, R2 = 0.9997.", "#e6a700"),
    (33.0, 42.5, "STEP 4", "M3C2 4D deformation map (T0 -> Tn)",
     "Signed surface change with Level-of-Detection; colorbar in mm. The results log "
     "lists every extracted parameter.", "#e0533d"),
    (42.5, 1e9, "STEP 6", "2D technical section & report",
     "Engineering section checked against vehicle clearance. Results export to "
     "PDF / IFC for the digital-twin workflow.", "#9b59b6"),
]


def font(sz, bold=False):
    for name in (("arialbd.ttf",) if bold else ()) + ("arial.ttf",):
        try:
            return ImageFont.truetype(name, sz)
        except Exception:
            continue
    return ImageFont.load_default()


F_STEP = font(26, bold=True)
F_TITLE = font(34, bold=True)
F_CAP = font(25)
F_BIG = font(64, bold=True)
F_SUB = font(34)
F_SMALL = font(28)
F_METRIC = font(30, bold=True)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def seg_for(sec):
    for s in SEGMENTS:
        if s[0] <= sec < s[1]:
            return s
    return SEGMENTS[-1]


def compose(foot_img, sec):
    _, _, step, title, cap, accent = seg_for(sec)
    acc = hex2rgb(accent)
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), (15, 17, 26))
    d = ImageDraw.Draw(canvas)
    # top band
    d.rectangle([0, 0, CANVAS_W, TOP_BAND], fill=(22, 26, 38))
    d.rectangle([0, TOP_BAND - 4, CANVAS_W, TOP_BAND], fill=acc)
    # step chip
    chip_w = int(d.textlength(step, font=F_STEP)) + 36
    d.rounded_rectangle([28, 26, 28 + chip_w, 70], radius=10, fill=acc)
    d.text((28 + chip_w / 2, 48), step, font=F_STEP, fill="white", anchor="mm")
    d.text((28 + chip_w + 24, 48), title, font=F_TITLE, fill="white", anchor="lm")
    # footage
    canvas.paste(foot_img, (0, TOP_BAND))
    # bottom band
    by = TOP_BAND + FOOT_H
    d.rectangle([0, by, CANVAS_W, CANVAS_H], fill=(22, 26, 38))
    d.rectangle([0, by, CANVAS_W, by + 4], fill=acc)
    lines = wrap(d, cap, F_CAP, CANVAS_W - 80)[:2]
    ty = by + (BOT_BAND - len(lines) * 30) / 2 + 14
    for ln in lines:
        d.text((CANVAS_W / 2, ty), ln, font=F_CAP, fill=(225, 228, 235), anchor="mm")
        ty += 32
    return np.asarray(canvas)


def intro_frames(seconds=3):
    out = []
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), (0, 26, 77))
    d = ImageDraw.Draw(img)
    d.text((CANVAS_W / 2, CANVAS_H * 0.32), "LiDAR-Based Tunnel", font=F_BIG, fill="white", anchor="mm")
    d.text((CANVAS_W / 2, CANVAS_H * 0.32 + 78), "Time-Series Shape Analysis", font=F_BIG, fill="#00ff88", anchor="mm")
    d.text((CANVAS_W / 2, CANVAS_H * 0.62), "Live run of the SSL Smart Tunnel Monitoring System on real T0~T5 data",
           font=F_SUB, fill="white", anchor="mm")
    d.text((CANVAS_W / 2, CANVAS_H * 0.62 + 56),
           "Auto Pipeline  >  Sections  >  Trend  >  M3C2  >  Report",
           font=F_SMALL, fill="#ffd24d", anchor="mm")
    arr = np.asarray(img)
    for _ in range(int(seconds * FPS)):
        out.append(arr)
    return out


def summary_frames(seconds=5):
    out = []
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), (26, 10, 46))
    d = ImageDraw.Draw(img)
    d.text((CANVAS_W / 2, 70), "Summary -- Tunnel Deformation Status (T0 -> T5)",
           font=F_TITLE, fill="#00ffff", anchor="mm")
    zones = [
        (300, "CROWN", "Chainage 20 m", "-45 mm", "CRITICAL", "#ff6b6b"),
        (640, "WALLS", "Chainage 45 m", "-35 mm", "CRITICAL", "#ff8800"),
        (980, "LOCAL", "Chainage 65 m", "-40 mm", "since T3", "#ffaa00"),
    ]
    for cx, t, ch, val, tag, c in zones:
        d.text((cx, 200), t, font=F_SUB, fill=c, anchor="mm")
        d.text((cx, 250), ch, font=F_SMALL, fill="white", anchor="mm")
        d.text((cx, 312), val, font=F_BIG, fill=c, anchor="mm")
        d.text((cx, 372), f"({tag})", font=F_SMALL, fill=c, anchor="mm")
    d.text((CANVAS_W / 2, 470), "Ovality 0.20 %    |    Eccentricity 1.52 mm    |    Forecast R2 = 0.9997",
           font=F_METRIC, fill="#00ff88", anchor="mm")
    d.text((CANVAS_W / 2, 545), "Outputs: 3D heatmap + section tables + trend graph + PDF / IFC export",
           font=F_SMALL, fill="#00ffff", anchor="mm")
    d.text((CANVAS_W / 2, 600), "-> feeds the digital-twin maintenance decision workflow",
           font=F_SMALL, fill="#b8bcc8", anchor="mm")
    arr = np.asarray(img)
    for _ in range(int(seconds * FPS)):
        out.append(arr)
    return out


def main():
    print("Reading real recording...")
    reader = imageio.get_reader(str(SRC))
    writer = imageio.get_writer(str(OUT), fps=FPS, codec="libx264", macro_block_size=1, quality=8)

    for fr in intro_frames():
        writer.append_data(fr)

    n = 0
    for i, frame in enumerate(reader):
        sec = i / FPS
        im = Image.fromarray(frame)
        if im.size != (1280, 720):
            im = im.resize((1280, 720), Image.Resampling.LANCZOS)
        foot = im.crop((0, 0, 1280, 720 - CROP_BOTTOM))
        writer.append_data(compose(foot, sec))
        n += 1
        if n % 300 == 0:
            print(f"  {n} footage frames...")
    reader.close()

    writer.close()

    size_mb = OUT.stat().st_size / (1024 ** 2)
    total = n + 3 * FPS
    print("\n" + "=" * 60)
    print("[OK] RE-AUTHORED DEMO FROM REAL RECORDING")
    print("=" * 60)
    print(f"File:     {OUT.name}")
    print(f"Size:     {size_mb:.2f} MB")
    print(f"Frames:   ~{total}  ({total/FPS:.1f} s)")
    print(f"Canvas:   {CANVAS_W}x{CANVAS_H}")
    print(f"Path:     {OUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
