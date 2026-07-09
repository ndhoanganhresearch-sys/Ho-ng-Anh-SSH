#!/usr/bin/env python3
import zipfile
import xml.etree.ElementTree as ET
import os

pptx_path = "Raycasting_Validation_Report.pptx"

if not os.path.exists(pptx_path):
    print(f"ERROR: {pptx_path} not found")
    exit(1)

print(f"Presentation: {pptx_path}")
print(f"Size: {os.path.getsize(pptx_path)} bytes")
print("\n" + "=" * 70)

try:
    with zipfile.ZipFile(pptx_path, 'r') as z:
        # List slide files
        slides = sorted([f for f in z.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')])
        print(f"\nTotal slides: {len(slides)}")
        print("\nSlide content summary:")

        for i, slide_file in enumerate(slides, 1):
            with z.open(slide_file) as f:
                root = ET.fromstring(f.read())
                # Extract all text from the slide
                ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
                texts = []
                for t in root.findall('.//a:t', ns):
                    if t.text:
                        texts.append(t.text)

                # Show first 150 chars of content
                content = ' '.join(texts)
                preview = content[:150] + ('...' if len(content) > 150 else '')
                print(f"\nSlide {i}: {preview}")

        print("\n" + "=" * 70)
        print("✓ PPTX file valid and readable")

except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
