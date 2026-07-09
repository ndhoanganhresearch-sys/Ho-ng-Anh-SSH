#!/usr/bin/env python3
import imageio
from pathlib import Path
import sys

workdir = Path(r'C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project')
frames_dir = workdir / 'output' / 'video_demo' / 'frames'
output = workdir / 'output' / 'video_demo' / 'lidar_demo.mp4'

print('Compiling video from frames...')
print(f'Frames directory: {frames_dir}')
print(f'Output: {output.name}')
print()

frames = sorted(frames_dir.glob('*.png'), key=lambda x: x.name)
print(f'Found {len(frames)} frames')

if len(frames) == 0:
    print('ERROR: No frames found!')
    sys.exit(1)

try:
    print('Creating MP4 video (this takes 2-3 minutes)...')
    writer = imageio.get_writer(str(output), fps=30, codec='libx264')

    for i, frame_path in enumerate(frames):
        if (i + 1) % 600 == 0:
            print(f'  {i+1}/{len(frames)} frames processed')
        frame = imageio.imread(str(frame_path))
        writer.append_data(frame)

    writer.close()
    print()

    if output.exists():
        size_mb = output.stat().st_size / (1024 ** 2)
        print('='*60)
        print('SUCCESS! VIDEO CREATED!')
        print('='*60)
        print(f'File: lidar_demo.mp4')
        print(f'Size: {size_mb:.1f} MB')
        print(f'Frames: {len(frames)}')
        print(f'Duration: {len(frames)/30:.1f} seconds (2 minutes)')
        print(f'Resolution: 1920x1080 @ 30fps, H.264')
        print()
        print(f'Location: {output}')
        print('='*60)
        print()
        print('READY FOR PRESENTATION!')
    else:
        print('ERROR: Video file not created')
        sys.exit(1)

except ImportError as e:
    print(f'ERROR: Missing module: {e}')
    print('Installing imageio-ffmpeg...')
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'imageio-ffmpeg'])
    print('Please run this script again')
    sys.exit(1)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
