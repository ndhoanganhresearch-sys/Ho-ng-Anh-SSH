"""
Annotate the tunnel cross-section screenshot with explanatory arrows.
Usage: python annotate_section.py <input_image> [output_image]
"""
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from PIL import Image
import numpy as np

input_path  = sys.argv[1] if len(sys.argv) > 1 else "section_screenshot.png"
output_path = sys.argv[2] if len(sys.argv) > 2 else "section_annotated.png"

img = Image.open(input_path)
W, H = img.size

fig, ax = plt.subplots(figsize=(16, 10), dpi=120)
ax.imshow(np.array(img))
ax.axis("off")

# ── helper ────────────────────────────────────────────────────────────────────
def arrow(ax, xy_tip, xy_text, text, color="white",
          fontsize=11, arrowcolor=None, boxcolor=None, ha="left"):
    if arrowcolor is None: arrowcolor = color
    if boxcolor   is None: boxcolor   = "#1E2A33"
    ax.annotate(
        text,
        xy=xy_tip, xycoords="data",
        xytext=xy_text, textcoords="data",
        ha=ha, va="center",
        fontsize=fontsize, color=color, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.35", fc=boxcolor, ec=arrowcolor,
                  alpha=0.88, linewidth=1.5),
        arrowprops=dict(arrowstyle="-|>", color=arrowcolor, lw=1.8,
                        connectionstyle="arc3,rad=0.15"),
    )

# Image is 1309 × 735 px (actual screenshot size)
# Pixel positions tuned to the actual layout.

# 1. Orange dashed circle → reference (T0 / design)
arrow(ax,
      xy_tip  =(818, 218),
      xy_text =(960, 140),
      text    ="Orange dashed circle\n= Reference shape (T0 baseline\nor design diameter)",
      color   ="#F2A516", arrowcolor="#F2A516", boxcolor="#0A2036",
      ha="left", fontsize=10)

# 2. Coloured scan dots — point to left-wall blue cluster
arrow(ax,
      xy_tip  =(466, 312),
      xy_text =(148, 230),
      text    ="Coloured dots = actual scan (Tn)\nBlue=Wall  Orange=Crown  Green=Floor",
      color   ="white", arrowcolor="#1AA0AB", boxcolor="#0A2036",
      ha="left", fontsize=10)

# 3. Gap between dots and circle = deformation
arrow(ax,
      xy_tip  =(448, 388),
      xy_text =(148, 430),
      text    ="Gap (dots vs circle)\n= local deformation\n(drawn ×10 for visibility)",
      color   ="#F2A516", arrowcolor="#F2A516", boxcolor="#0F2A43",
      ha="left", fontsize=10)

# 4. W1 / W2 – width measurements (move label to right to avoid overlap)
arrow(ax,
      xy_tip  =(638, 157),
      xy_text =(750, 50),
      text    ="W1 / W2 = tunnel width\n(left–right at top & bottom)",
      color   ="white", arrowcolor="white", boxcolor="#0A2036",
      ha="left", fontsize=10)

# 5. H1 / H2 / H3 – height measurements (point to H1 label on right)
arrow(ax,
      xy_tip  =(836, 328),
      xy_text =(990, 265),
      text    ="H1 = full height (right side)\nH2 = crown→centre\nH3 = centre→floor",
      color   ="white", arrowcolor="white", boxcolor="#0A2036",
      ha="left", fontsize=10)

# 6. e = eccentricity (point to the purple e=165mm label in centre)
arrow(ax,
      xy_tip  =(648, 330),
      xy_text =(560, 500),
      text    ="e = eccentricity\nOffset of fitted circle centre\nfrom coordinate origin",
      color   ="#A78BFA", arrowcolor="#A78BFA", boxcolor="#0A2036",
      ha="left", fontsize=10)

# 7. crown h label (move down to bottom-right to free up top space)
arrow(ax,
      xy_tip  =(755, 148),
      xy_text =(870, 200),
      text    ="Crown height\nfrom rail / floor level",
      color   ="white", arrowcolor="#9DB3BD", boxcolor="#0A2036",
      ha="left", fontsize=10)

# 8. Visual x10 badge (point to the "Visual x10" box inside chart, move down)
arrow(ax,
      xy_tip  =(500, 96),
      xy_text =(220, 50),
      text    ="Visual ×10: deformations\ndrawn 10× larger than real\n(mm-level shifts made visible)",
      color   ="#27AE60", arrowcolor="#27AE60", boxcolor="#0A2036",
      ha="left", fontsize=10)

# 9. Status bar — arrow pointing DOWN to the bottom info bar
arrow(ax,
      xy_tip  =(655, H - 12),
      xy_text =(655, H - 100),
      text    ="Status bar: R · Oval% · e · Delta vs T0",
      color   ="#0E7C86", arrowcolor="#0E7C86", boxcolor="#0A2036",
      ha="center", fontsize=9.5)

plt.tight_layout(pad=0)
fig.savefig(output_path, dpi=120, bbox_inches="tight", facecolor="#0F2A43")
print(f"Saved → {output_path}")
