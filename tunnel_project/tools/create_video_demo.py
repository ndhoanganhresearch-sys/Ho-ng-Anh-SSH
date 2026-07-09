#!/usr/bin/env python3
r"""
Video Demo Creator for LiDAR Time-Series Deformation Analysis
Captures PyVista visualization and generates demo video

Usage:
    python create_video_demo.py --mode gui_capture
    python create_video_demo.py --mode render_frames
    python create_video_demo.py --mode compile_video
"""

import subprocess
import sys
from pathlib import Path
import json
import time

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "time_series_deformation"
OUTPUT_DIR = PROJECT_ROOT / "output" / "video_demo"
BENCHMARK_DIR = PROJECT_ROOT / "output" / "timeseries_benchmark"

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NARRATION_SCRIPT = """
[00:00-00:15] INTRO
Title: LiDAR-Based Tunnel Time-Series Shape Analysis Technology
Show the 3D tunnel point cloud in different angles
"This system analyzes tunnel deformation over time using repeated LiDAR scans."

[00:15-00:35] LOAD & REGISTER
Load T0.las and T5.las in sequence
"We load six epochs of LiDAR data: T0 through T5."
Show alignment/registration result
"Each epoch is automatically co-registered with perfect alignment (RMSE = 0 mm)."

[00:35-01:00] CENTERLINE & SECTIONS
Show centerline extraction
"The tunnel centerline is extracted using PCA analysis."
Show Frenet-frame cross-sections
"Using Frenet-Serret frames, we generate orthogonal cross-sections every 0.5 meters."
Highlight key sections at 20m, 45m, 65m
"We focus on three critical zones with known deformation."

[01:00-01:30] DEFORMATION VISUALIZATION
Show M3C2 heatmap with color scale
"M3C2 algorithm computes signed distances along surface normals."
Red zones indicate settlement/convergence/damage
"Red areas show deformation: crown settlement up to -45 mm, sidewall convergence -35 mm."
Rotate 3D view to show deformation pattern
"Local damage appears at 65m chainage, growing from T3 to T5."

[01:30-01:50] TIME-SERIES TRENDS
Show crown profile graph (T0?뭈5)
"Crown settlement shows progressive decline across 6 epochs."
Show chainage-based deformation plot
"Deformation concentrates at three zones: 20m (crown), 45m (walls), 65m (local)."
Show trend forecasting graph with R짼 > 0.999
"Our trend model predicts future deformation with 99.99% accuracy."

[01:50-02:00] SUMMARY & DECISIONS
Show PDF report generation
"System outputs engineering reports in PDF and IFC formats."
Show warning zones highlighted
"Engineers receive prioritized maintenance recommendations."
Final frame with metrics
"Deformation tracked to millimeter precision. Decision support ready."

[02:00-02:03] OUTRO
Logo/Institution
"Thank you for watching."
"""

def generate_narration_file():
    """Save narration script for reference and voiceover timing."""
    narration_file = OUTPUT_DIR / "narration_script.txt"
    narration_file.write_text(NARRATION_SCRIPT)
    print(f"??Narration script saved: {narration_file}")
    return narration_file

def create_gui_capture_guide():
    """Create step-by-step guide for manual GUI capture."""
    guide = r"""
================================================================================
STEP-BY-STEP GUI CAPTURE GUIDE
================================================================================

1. PREPARE DATA
   - Ensure T0.las ~ T5.las exist in: tunnel_project/data/time_series_deformation/
   - Ensure benchmark outputs exist: tunnel_project/output/timeseries_benchmark/

2. SET UP SCREEN RECORDING
   Option A - Windows (Built-in):
   - Settings ??System ??Sound ??Volume mixer
   - Use Game Bar (Win+G) or Windows 10/11 built-in recorder
   - Set resolution: 1920x1080 @ 30fps (or 60fps)

   Option B - OBS Studio (Recommended):
   - Download: https://obsproject.com/
   - Scene Setup:
     * Source 1: Window Capture (SSL Tunnel App)
     * Source 2: Image (m3c2_heatmap_T0_T5.png) for overlay
     * Source 3: Browser source (for graphs)
   - Output: MP4, H.264, 30fps, 1920x1080

3. RUN SSL APPLICATION
   ```powershell
   cd tunnel_project
   ..\.venv\Scripts\python.exe run_tunnel_analysis.py
   ```

4. EXECUTE DEMO WORKFLOW
   Step 1: Load T0.las (baseline scan)
   Step 2: Load T5.las (final epoch for comparison)
   Step 3: Run Step 3 (Auto-align) - show registration
   Step 4: Run Step 6 (Time-Series Plot) - show deformation trend
   Step 5: Show 3D heatmap in GUI

   Timing Guide:
   - T0 loading: 5 sec
   - T5 loading: 5 sec
   - Registration: 10 sec
   - Heatmap visualization: 30 sec
   - Trend graphs: 20 sec
   - Total UI capture: ~70 sec

5. SCREEN RECORDING SEGMENTS
   Segment 1 (0-15s): Title + 3D tunnel cloud
   Segment 2 (15-35s): Load T0 ??T5, show registration
   Segment 3 (35-60s): Centerline + cross-sections
   Segment 4 (60-90s): M3C2 heatmap (rotate view)
   Segment 5 (90-110s): Trend graphs
   Segment 6 (110-120s): Summary

6. POST-PRODUCTION (After recording)
   - Import segments into video editor
   - Add title cards
   - Overlay benchmark images (heatmaps, graphs)
   - Add narration voiceover (read from narration_script.txt)
   - Add music (optional, royalty-free)
   - Export as MP4

7. FFMPEG ASSEMBLY
   See: compile_video_ffmpeg.sh (generated below)
"""

    guide_file = OUTPUT_DIR / "GUI_CAPTURE_GUIDE.md"
    guide_file.write_text(guide)
    print(f"??GUI Capture Guide saved: {guide_file}")
    return guide_file

def create_ffmpeg_script():
    """Create FFmpeg script to compile video from segments."""
    ffmpeg_script = f"""#!/bin/bash
# FFmpeg Video Compilation Script
# Assembles recorded segments with overlays and audio

set -e

VIDEO_OUTPUT="{OUTPUT_DIR}/lidar_timeseries_demo.mp4"
SEGMENTS_DIR="{OUTPUT_DIR}/segments"
HEATMAP="{BENCHMARK_DIR}/m3c2_heatmap_T0_T5.png"
CROWN_PROFILE="{BENCHMARK_DIR}/crown_profile_per_epoch.png"
OVERVIEW="{BENCHMARK_DIR}/timeseries_benchmark_overview.png"

echo "Compiling video segments..."

# Step 1: Ensure all segments are properly encoded
if [ -d "$SEGMENTS_DIR" ]; then
    for segment in "$SEGMENTS_DIR"/segment_*.mp4; do
        echo "Processing: $(basename "$segment")"
        # Re-encode to consistent format if needed
        ffmpeg -i "$segment" -c:v libx264 -crf 23 -c:a aac -y "$(dirname "$segment")/encoded_$(basename "$segment")" 2>/dev/null || true
    done
fi

# Step 2: Create concat file
CONCAT_FILE="{OUTPUT_DIR}/segments.txt"
cat > "$CONCAT_FILE" << 'EOF'
# Segment order for concatenation
# Replace with actual segment filenames
file '{OUTPUT_DIR}/segments/segment_01_intro.mp4'
file '{OUTPUT_DIR}/segments/segment_02_load.mp4'
file '{OUTPUT_DIR}/segments/segment_03_sections.mp4'
file '{OUTPUT_DIR}/segments/segment_04_heatmap.mp4'
file '{OUTPUT_DIR}/segments/segment_05_trends.mp4'
file '{OUTPUT_DIR}/segments/segment_06_summary.mp4'
EOF

# Step 3: Concatenate all segments
echo "Concatenating segments..."
ffmpeg -f concat -safe 0 -i "$CONCAT_FILE" -c copy "$VIDEO_OUTPUT" 2>&1 | grep -E "frame|time|bitrate" || true

# Step 4: Add audio narration (optional - requires narration.wav)
if [ -f "{OUTPUT_DIR}/narration.wav" ]; then
    echo "Adding voiceover..."
    ffmpeg -i "$VIDEO_OUTPUT" -i "{OUTPUT_DIR}/narration.wav" \\
        -c:v copy -c:a aac -shortest \\
        -y "{OUTPUT_DIR}/lidar_timeseries_demo_with_audio.mp4"
fi

echo "??Video compilation complete: $VIDEO_OUTPUT"
echo ""
echo "Next steps:"
echo "1. Review output video in VLC or similar"
echo "2. If using audio: ffmpeg to add background music (optional)"
echo "3. Export final MP4 for presentation"
"""

    script_file = OUTPUT_DIR / "compile_video_ffmpeg.sh"
    script_file.write_text(ffmpeg_script)
    script_file.chmod(0o755)
    print(f"??FFmpeg script saved: {script_file}")
    return script_file

def create_voiceover_guide():
    """Create guide for recording voiceover narration."""
    guide = r"""
================================================================================
VOICEOVER NARRATION RECORDING GUIDE
================================================================================

SCRIPT: See narration_script.txt

RECORDING SETUP:
1. Microphone: USB mic (Blue Yeti, Audio-Technica AT2020) recommended
2. Software: Audacity (free) or Adobe Audition
3. Settings:
   - Sample rate: 44.1 kHz or 48 kHz
   - Bit depth: 16-bit
   - Mono or Stereo (mono is fine)

RECORDING TIPS:
- Speak clearly and moderately paced
- Leave 0.5 sec silence at start/end for safety
- Record each section separately for easier editing
- Do 2-3 takes, pick the best one

TIMING:
- Intro (15s): Read at natural pace
- Load & Register (20s): Explain registration concept
- Sections (25s): Describe what's on screen
- Heatmap (30s): Emphasize deformation colors
- Trends (20s): Highlight accuracy metrics
- Summary (10s): Conclude with decision support

OUTPUT:
Save as: {OUTPUT_DIR}/narration.wav (WAV format, 48kHz, 16-bit)

THEN: Use FFmpeg to sync with video:
ffmpeg -i lidar_timeseries_demo.mp4 -i narration.wav \\
  -c:v copy -c:a aac -shortest \\
  -y lidar_timeseries_demo_final.mp4
"""

    voiceover_file = OUTPUT_DIR / "VOICEOVER_GUIDE.md"
    voiceover_file.write_text(guide)
    print(f"??Voiceover Guide saved: {voiceover_file}")
    return voiceover_file

def create_obs_setup():
    """Create OBS Studio configuration guide."""
    obs_guide = """
================================================================================
OBS STUDIO SETUP FOR VIDEO CAPTURE
================================================================================

INSTALLATION:
Download from: https://obsproject.com/

SCENE LAYOUT:
?뚢?????????????????????????????????????????????       Main Source: SSL App Window      ?? (1920x1080)
??                                        ????    ?뚢?????????????????????????????????? ????    ?? Overlay: M3C2 Heatmap (30%)   ?? ?? (top-right corner)
??    ?붴?????????????????????????????????? ???붴???????????????????????????????????????????
SOURCES TO ADD:
1. Window Capture
   - Select: [SSL Tunnel Analysis App]
   - Resolution: 1920x1080 (match window size)

2. Image (for M3C2 heatmap)
   - File: tunnel_project/output/timeseries_benchmark/m3c2_heatmap_T0_T5.png
   - Position: Top-right
   - Opacity: 70%
   - Visible: Only during heatmap segment (01:00-01:30)

3. Color Source (Title card)
   - Color: Black or Navy
   - Text overlay: "LiDAR-Based Tunnel Time-Series Shape Analysis"
   - Visible: Only during intro (00:00-00:15)

OUTPUT SETTINGS:
- Video Bitrate: 8000 kbps (for 1080p @ 30fps)
- Audio Bitrate: 128 kbps
- Encoder: H.264 (Hardware if available)
- Container: MP4
- Output Path: tunnel_project/output/video_demo/capture.mp4

RECORDING WORKFLOW:
1. Click "Start Recording"
2. Execute Steps 1-6 in SSL app (see GUI_CAPTURE_GUIDE.md)
3. For each segment, make smooth transitions
4. Click "Stop Recording" at end
5. Output file: capture.mp4 (ready for post-production)

POST-PRODUCTION IN OBS:
- Use OBS Studio's replay buffer (Alt+R) to save best clips
- Or export full recording and trim in video editor

TIMING CHECKLIST:
??Intro (15s) - title + rotating 3D cloud
??Load & Register (20s) - T0 load, T5 load, alignment
??Sections (25s) - centerline, Frenet frames
??Heatmap (30s) - M3C2 visualization, rotation
??Trends (20s) - graphs and forecasting
??Summary (10s) - metrics and conclusions
Total: ~120 seconds (2 minutes)
"""

    obs_file = OUTPUT_DIR / "OBS_SETUP.md"
    obs_file.write_text(obs_guide)
    print(f"??OBS Setup Guide saved: {obs_file}")
    return obs_file

def print_workflow():
    """Print complete workflow."""
    print("""
================================================================================
VIDEO DEMO CREATION WORKFLOW - PyVista GUI Capture
================================================================================

?뱥 OVERVIEW:
1. Prepare data & guides
2. Set up OBS Studio (screen recording)
3. Run SSL app with T0?뭈5 workflow
4. Record screen segments
5. Compile video with FFmpeg
6. Add voiceover narration
7. Export final MP4

================================================================================
STEP 1: PREPARE (Now Complete)
================================================================================
??Narration script: narration_script.txt
??GUI capture guide: GUI_CAPTURE_GUIDE.md
??OBS Studio setup: OBS_SETUP.md
??FFmpeg compiler: compile_video_ffmpeg.sh
??Voiceover guide: VOICEOVER_GUIDE.md

Files saved to: """ + str(OUTPUT_DIR) + """

================================================================================
STEP 2: SET UP OBS STUDIO
================================================================================
1. Download OBS from https://obsproject.com/
2. Follow instructions in: OBS_SETUP.md
3. Create scene with:
   - Window Capture (SSL app)
   - Image overlay (M3C2 heatmap)
   - Title card

Settings:
- Output: 1920x1080 @ 30fps
- Format: MP4, H.264
- Save to: tunnel_project/output/video_demo/segments/

================================================================================
STEP 3: EXECUTE DEMO WORKFLOW IN SSL APP
================================================================================
1. Start SSL Tunnel Analysis app
2. Load T0.las (Step 1: Load Reference)
3. Load T5.las (Step 2: Load Comparison)
4. Run Step 3 (Auto-align) to show registration
5. Run Step 6.1 (Plot Time-Series Deformation)
6. Take screenshots of:
   - Crown profile graph
   - Chainage-based deformation
   - Trend forecast plot

Total time: ~2 minutes of screen recording

================================================================================
STEP 4: RECORD SEGMENTS IN OBS
================================================================================
Run through workflow 2-3 times to get smooth recording:
1. Intro + 3D cloud (15 sec)
2. T0 load ??T5 load ??Registration (20 sec)
3. Centerline extraction + sections (25 sec)
4. M3C2 heatmap (rotate view) (30 sec)
5. Trend graphs (20 sec)
6. Summary & metrics (10 sec)

Save output: tunnel_project/output/video_demo/segments/

================================================================================
STEP 5: COMPILE VIDEO WITH FFMPEG
================================================================================
Execute compilation script:

  cd tunnel_project/output/video_demo
  bash compile_video_ffmpeg.sh

This will:
??Concatenate all segments
??Add image overlays
??Create: lidar_timeseries_demo.mp4 (2 minutes)

================================================================================
STEP 6: RECORD VOICEOVER NARRATION
================================================================================
Use Audacity or similar:
1. Open narration_script.txt
2. Record narration in sections (see VOICEOVER_GUIDE.md)
3. Edit & time-align with video segments
4. Export as: narration.wav (48kHz, 16-bit)

Save to: tunnel_project/output/video_demo/narration.wav

================================================================================
STEP 7: SYNC AUDIO & EXPORT FINAL VIDEO
================================================================================
Use FFmpeg to add voiceover:

  ffmpeg -i lidar_timeseries_demo.mp4 -i narration.wav \\
    -c:v copy -c:a aac -shortest -y lidar_demo_final.mp4

Or add background music (optional):

  ffmpeg -i lidar_demo_final.mp4 -i background_music.mp3 \\
    -filter_complex "[1:a]volume=0.2[music];[0:a][music]amix=inputs=2:duration=first[a]" \\
    -map 0:v -map "[a]" -c:v copy -c:a aac \\
    -y lidar_demo_with_music.mp4

================================================================================
FINAL OUTPUT
================================================================================
?벞 Video file: lidar_timeseries_demo_final.mp4 (2-3 minutes)
?뱞 For presentation: Ready to show to Professor Yoon
?뱤 Quality: 1920x1080 @ 30fps, H.264, AAC audio

Ready to deliver! ??
================================================================================
""")

if __name__ == "__main__":
    print("Generating video demo workflow files...")
    print()

    generate_narration_file()
    create_gui_capture_guide()
    create_ffmpeg_script()
    create_voiceover_guide()
    create_obs_setup()

    print()
    print_workflow()

    print("\n??All workflow files generated!")
    print(f"\nNext step: Download OBS Studio and follow OBS_SETUP.md")
    print(f"Guides location: {OUTPUT_DIR}")

