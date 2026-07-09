#!/usr/bin/env python3
"""Compile video frames into MP4 using imageio"""

import imageio
from pathlib import Path
import sys

frames_dir = Path('tunnel_project/output/video_demo/frames')
output_video = Path('tunnel_project/output/video_demo/lidar_demo.mp4')

print(f"Compiling video from {frames_dir}...")

# Get all PNG files sorted by name
frames = sorted(frames_dir.glob('*.png'), key=lambda x: x.name)
print(f"Found {len(frames)} frames")

if len(frames) == 0:
    print("No frames found!")
    sys.exit(1)

try:
    print("Creating video writer...")
    writer = imageio.get_writer(str(output_video), fps=30, codec='libx264')

    print("Adding frames to video...")
    for i, frame_path in enumerate(frames):
        if i % 300 == 0:
            print(f"  Frame {i}/{len(frames)}")
        try:
            frame = imageio.imread(frame_path)
            writer.append_data(frame)
        except Exception as e:
            print(f"  Error reading {frame_path}: {e}")
            continue

    writer.close()
    print("Video writer closed")

    # Check output
    if output_video.exists():
        size_mb = output_video.stat().st_size / (1024 * 1024)
        duration_sec = len(frames) / 30
        print(f"\n{'='*60}")
        print("VIDEO CREATED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"File: {output_video}")
        print(f"Size: {size_mb:.1f} MB")
        print(f"Frames: {len(frames)}")
        print(f"Duration: {duration_sec:.1f} seconds")
        print(f"Format: MP4, 1920x1080 @ 30fps")
        print(f"\nReady for presentation!")
        print(f"{'='*60}")
    else:
        print("Video file not found after compilation!")
        sys.exit(1)

except ImportError:
    print("imageio not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio"])
    print("Please run the script again")
    sys.exit(1)
except Exception as e:
    print(f"Error during compilation: {e}")
    print(f"Frames directory: {frames_dir}")
    print(f"Try installing FFmpeg: pip install imageio-ffmpeg")
    sys.exit(1)
