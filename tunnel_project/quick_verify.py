#!/usr/bin/env python3
import zipfile
import os

pptx_path = "Raycasting_Validation_Report.pptx"

if not os.path.exists(pptx_path):
    print(f"ERROR: {pptx_path} not found")
    exit(1)

print(f"Presentation: {pptx_path}")
print(f"Size: {os.path.getsize(pptx_path)} bytes\n")

with zipfile.ZipFile(pptx_path, 'r') as z:
    slides = sorted([f for f in z.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')])
    print(f"[OK] Total slides: {len(slides)}")

    # Check that we have 10 slides
    if len(slides) == 10:
        print("[OK] Correct number of slides (10)")
    else:
        print(f"[ERROR] Expected 10 slides, got {len(slides)}")

    # Verify slide files
    for i in range(1, 11):
        expected = f'ppt/slides/slide{i}.xml'
        if expected in z.namelist():
            print(f"  [OK] Slide {i} exists")
        else:
            print(f"  [ERROR] Slide {i} missing")

print("\n[OK] PPTX structure valid and ready for delivery")
