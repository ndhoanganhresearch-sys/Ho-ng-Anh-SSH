# Phase A: Generate Clean T0 Reference

## Raycast the real curved tunnel to a clean baseline point cloud

**Output:** `data/blender_lidar_t0t5/T0_raycast.txt` (+ `T0_raycast.json`)

**Engine:** `tools/raycast_tunnel_epochs.py` (runs inside Blender)

---

## What this is

A clean (undeformed) LiDAR point cloud raycast from the **real** tunnel mesh in
`tunnel_lidar_scene.blend`. It is the reference epoch for the T0→Tn validation in
Phase C. The same engine produces every epoch, so T0 and any Tn share identical
scanner geometry — there is no "config must match" risk.

The geometry is the actual dataset geometry (verified against `manifest.json`):

| Property | Value |
| --- | --- |
| Tunnel | circular arch, radius ~4.25 m (8.5 m bore), length 80 m |
| Alignment | horizontal curve R = 500 m (NOT a straight cylinder) |
| Chainage | **arc length** along the curved centerline (0–80 m) |
| Crown direction | local +Z in the cross-section frame |
| Scanner | 3 TLS stations at arc-length 10 / 40 / 70 m, tripod z = -1.3 m |
| Ray grid | azimuth 1° × elevation 1° (-25°…90°), max range 60 m |
| Noise | range σ(d) = 0.002 + 0.00006·d m (per manifest) |
| Mesh | `Tunnel_Lining`, 16,100 verts (raycast via BVHTree) |

---

## Run it

Option 1 — Blender CLI:
```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
blender -b data\blender_lidar_t0t5\tunnel_lidar_scene.blend ^
        -P tools\raycast_tunnel_epochs.py -- --epoch T0
```

Option 2 — Blender MCP (Blender already open): run `tools/raycast_tunnel_epochs.py`
with `EPOCH = "T0"`.

**Expected:**
```
RAYCAST TUNNEL EPOCH: T0
  hits: ~112,500
  -> data/blender_lidar_t0t5/T0_raycast.txt
  -> data/blender_lidar_t0t5/T0_raycast.json
  clean .blend restored
```

The on-disk `.blend` is reopened at the end, so nothing is overwritten.

---

## Verify

```powershell
..\.venv\Scripts\python.exe -c "import numpy as np,math; a=np.loadtxt(r'data\blender_lidar_t0t5\T0_raycast.txt'); a=a[a[:,4]==1]; s=500*np.arcsin(np.clip(a[:,1]/500,-1,1)); cx=500*(1-np.cos(s/500)); r=np.hypot(a[:,0]-cx,a[:,2]); print('points',len(a),'radius mean %.3f'%r.mean())"
```

- [ ] ~112k lining points
- [ ] radius mean ≈ 4.25 m (clean, consistent along the curve)
- [ ] `T0_raycast.json` present, `deformation_prescribed` all 0

---

## Next: Phase B

Generate a deformed epoch (T1–T5) with the same engine. See `PHASE_B_GUIDE.md`.
