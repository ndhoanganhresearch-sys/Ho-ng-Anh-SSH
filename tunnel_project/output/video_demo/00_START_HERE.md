# Video Demo Creation - Start Here

## Quick Start: 3 Steps

### Step 1: Download OBS Studio
- Go to https://obsproject.com/
- Download and install (free)
- Launch OBS Studio

### Step 2: Follow Setup Guide
- Open `OBS_SETUP.md` (generated below)
- Create scene with SSL app window capture
- Verify recording settings: 1920x1080 @ 30fps

### Step 3: Record Demo Workflow
- Open SSL Tunnel Analysis app
- Run workflow: Load T0.las → Load T5.las → Step 6 analysis
- Record 2-3 minutes of smooth screen capture
- Save output as MP4

---

## Generated Workflow Files

The following files have been generated to guide you:

### 1. **narration_script.txt**
   - Complete voiceover script (2-3 minutes)
   - Timing breakdown for each segment
   - Read this while recording to stay on schedule

### 2. **OBS_SETUP.md** (IMPORTANT)
   - Step-by-step OBS Studio configuration
   - Scene layout and source setup
   - Recording settings and output format
   - **Start here after downloading OBS**

### 3. **GUI_CAPTURE_GUIDE.md**
   - Detailed walkthrough of SSL app workflow
   - What to do at each step
   - Screen recording timing guide
   - Follow this while recording

### 4. **VOICEOVER_GUIDE.md**
   - How to record narration (after video capture)
   - Recommended software (Audacity - free)
   - Recording tips and timing
   - FFmpeg command to sync audio

### 5. **compile_video_ffmpeg.sh**
   - Automated video compilation script
   - Concatenates segments
   - Adds overlays and audio
   - Run after all recording is done

---

## Timeline Overview

```
[00:00-00:15] Intro - Title & 3D tunnel cloud
[00:15-00:35] Load Data - T0, T5, registration
[00:35-01:00] Geometry - Centerline, cross-sections
[01:00-01:30] Deformation - M3C2 heatmap visualization
[01:30-01:50] Trends - Crown profile, chainage plots, forecast
[01:50-02:00] Summary - Metrics and decisions
```

Total: **2 minutes** (120 seconds)

---

## Workflow Checklist

- [ ] Download OBS Studio
- [ ] Read OBS_SETUP.md
- [ ] Configure OBS scene
- [ ] Test recording settings
- [ ] Open SSL Tunnel Analysis app
- [ ] Load T0.las (Step 1)
- [ ] Load T5.las (Step 2)
- [ ] Run Step 3 (alignment)
- [ ] Run Step 6 (time-series plot)
- [ ] Record 2-3 minutes of screen
- [ ] Save MP4 output
- [ ] Record voiceover narration (Audacity)
- [ ] Save voiceover as WAV
- [ ] Run FFmpeg to compile final video
- [ ] Review final MP4
- [ ] Deliver to Professor Yoon

---

## Quick Reference: Data Location

**Point Cloud Data:**
- `tunnel_project/data/time_series_deformation/T0.las` ~ `T5.las`

**Ground Truth:**
- `tunnel_project/data/time_series_deformation/ground_truth.csv`

**Benchmark Outputs:**
- `tunnel_project/output/timeseries_benchmark/`
  - `m3c2_heatmap_T0_T5.png`
  - `crown_profile_per_epoch.png`
  - `timeseries_benchmark_overview.png`

**Video Output:**
- `tunnel_project/output/video_demo/`

---

## Next Steps

1. **Download OBS Studio** (https://obsproject.com/)
2. **Read:** OBS_SETUP.md
3. **Configure:** Create recording scene
4. **Execute:** Follow GUI_CAPTURE_GUIDE.md
5. **Record:** 2-minute screen capture
6. **Post-Produce:** Add voiceover using VOICEOVER_GUIDE.md
7. **Compile:** Run compile_video_ffmpeg.sh
8. **Deliver:** Final MP4 to Professor Yoon

---

## Support & Tips

**OBS Recording Tips:**
- Start recording before launching SSL app
- Use "Replay Buffer" (Alt+R) to save best takes
- Disable system sounds if needed
- Test audio levels before full recording

**Video Quality:**
- 1920x1080 @ 30fps = clear and sharp
- File size: ~200-300 MB for 2-minute video
- Format: MP4 (compatible with all devices)

**Common Issues:**
- OBS window capture blank? → Check window focus/focus priority setting
- Audio sync off? → Ensure consistent frame rate (30fps)
- Heatmap not visible? → Add as image overlay in OBS scene

---

**Questions?** Check the specific guide files (OBS_SETUP.md, GUI_CAPTURE_GUIDE.md, etc.)

Good luck with your video! 🎬
