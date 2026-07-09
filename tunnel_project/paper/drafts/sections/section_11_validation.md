## 11. Experimental Validation

The pipeline is validated on synthetic ground-truth datasets, where the true geometry, the true clutter labels, and the true deformation are known exactly. Synthetic data isolates algorithm accuracy from survey error and provides the labelled references that field scans lack. All results below were produced at commit `84c02cc` with the Python 3.12 environment on Windows 11. Validation on field scans is identified as the principal remaining step (Section 11.6).

### 11.1 Datasets

The benchmark suite comprises six Blender-generated tunnel scenes, each isolating one capability: a clean reference, a localised deformation, a noise-and-cable scene with per-point clutter labels, a clearance-intrusion scene, a curved-centerline scene, and an occluded sparse scene. A separate registration benchmark applies a known rigid perturbation (1.2° yaw, 7 cm translation) to be recovered, and a time-series set provides six epochs with prescribed crown settlement, sidewall convergence, and a localised defect for change-detection testing.

### 11.2 Geometric accuracy and denoising

On the clean reference scene the section extraction recovered a median radius of 4.00002 m against the 4.00000 m design value, an error of 0.0005%, and raised no false warnings. On the curved and occluded scenes the median radius stayed within 0.009 m of design (3.991 m and 3.999 m) despite 2.03 m of lateral curvature and 8% point loss, confirming that the Frenet sectioning and coverage guards hold under curvature and occlusion. The denoising cascade, run on the labelled noise-and-cable scene, removed 82.6% of injected clutter while retaining 99.99% of lining points, for a precision of 1.00, recall of 0.83, and F1 of 0.90. The clearance check on the intrusion scene reached 100% precision and 100% recall (1,080 true positives, no false positives, no false negatives), correctly flagging the 870.3 mm maximum intrusion as critical. Table 4 summarises the suite.

**Table 4.** Blender benchmark suite (commit `84c02cc`; all 36 checks pass).

| Case | Scenario | Key result |
|---|---|---|
| 01 | Clean reference | median radius 4.00002 m (error 0.0005%); 0 false warnings |
| 02 | Local deformation | polar max 83.5 mm; 10 sections flagged; heatmap p95 50.9 mm |
| 03 | Noise and cables | recall 0.826, lining retention 0.9999, F1 0.90 |
| 04 | Clearance intrusion | precision 1.00, recall 1.00; max intrusion 870.3 mm |
| 05 | Curved centerline | median radius 3.991 m over 2.03 m lateral span |
| 06 | Occlusion / sparse | median radius 3.999 m despite 8% point loss |

To attribute removal to the responsible stage, the denoising statistics are reported per stage in Table 5. The two scenes exercise complementary clutter types. The labelled noise-and-cable scene contains scattered radial noise but no cable, fixture, or personnel components, so all 877 removals are made by the radial robust-statistics stage and the semantic and wall-protrusion stages correctly remove nothing. A separate synthetic shell carrying cable and fixture clutter exercises the morphological stage directly: there the semantic stage removes 888 of 957 points (252 cable, 636 fixture) at a cable recall of 1.00 and lining retention of 0.99, while the radial stage removes only 69. Each stage therefore acts on the clutter type it targets, and the cascade defaults to the radial stage when no structured clutter is present. A single scene combining all clutter types into one labelled benchmark is identified as future work (Section 11.7).

**Table 5.** Per-stage denoising attribution (points removed by each cascade stage).

| Scene | Morphological (cable/fixture/person) | Radial robust | Wall protrusion | Total removed | Recall | Lining retention |
|---|---|---|---|---|---|---|
| Noise-and-cable (case 03) | 0 | 877 | 0 | 877 | 0.826 | 0.9999 |
| Cable+fixture shell | 888 (252/636/0) | 69 | 0 | 957 | 1.00 (cable) | 0.99 |

### 11.3 Registration

Generalised ICP recovered the synthetic perturbation to sub-millimetre accuracy on the straight 400K-point tunnel: 0.198 mm RMSE in 587 ms, against 31.7 mm and 11,953 ms for the Open3D point-to-plane baseline, a 20-fold speedup at far higher accuracy. On the curved 150K-point dataset GICP remained faster by a factor of 61 (410 ms versus 25,182 ms). The higher residual on the curved set (71.0 mm versus 115.9 mm for the baseline) reflects that the 1.2° single-step perturbation exceeds the convergence basin for that geometry; in normal operation the feature-based GROR coarse alignment of Section 5.3 runs first and supplies an initialisation within the basin. Within the full pipeline, registration of the curved dataset converged to 0.224 mm via the fallback chain. Table 6 reports the comparison; the curved rows are isolated single-step fine-registration runs outside the convergence basin, not the end-to-end result, and the speedup figures should be read against that caveat.

**Table 6.** Registration recovery (1.2° yaw, 7 cm translation; curved rows are out-of-basin single-step runs).

| Dataset | Backend | RMSE (mm) | Time (ms) | Speedup |
|---|---|---|---|---|
| Straight, 400K | small_gicp GICP | 0.198 | 587 | 20.4× |
| Straight, 400K | Open3D point-to-plane | 31.735 | 11,953 | — |
| Curved, 150K | small_gicp GICP | 70.958 | 410 | 61.4× |
| Curved, 150K | Open3D point-to-plane | 115.915 | 25,182 | — |

### 11.4 Frenet versus world-frame sectioning

The benefit of Frenet sectioning is isolated by computing ovality both ways on the same scenes. On the curved scene, world-frame slicing overestimated median ovality by 171.5% relative (0.2282% versus 0.0841% in the Frenet frame), overestimated the radius standard deviation by 65.4%, and overestimated eccentricity by 38.5%. On the straight control scene the two methods agreed to within noise (a −2.1% difference). The bias is therefore specific to curvature, as expected: an oblique cut only distorts the section when the axis turns. This confirms the claim that Frenet sectioning removes a systematic ovality bias that axis-aligned slicing introduces in curved tunnels. Table 7 reports the comparison. The magnitude of the bias is a function of curvature, so the single curved scene establishes the direction and approximate scale of the effect, not a universal constant; a curvature sweep is identified as future work in Section 11.7.

**Table 7.** Frenet versus world-frame ovality (one curved scene, one straight control).

| Metric | Frenet | World-frame | Relative bias |
|---|---|---|---|
| Curved: median ovality (%) | 0.0841 | 0.2282 | +171.5% |
| Curved: radius std (m) | 0.00289 | 0.00478 | +65.4% |
| Curved: median eccentricity (mm) | 569.9 | 789.4 | +38.5% |
| Straight (control): ovality (%) | 0.0209 | 0.0204 | −2.1% |

### 11.5 Deformation accuracy against ground truth

The headline use case, accurate deformation measurement, is validated directly against the prescribed time-series ground truth. Each consecutive epoch pair of the six-epoch dataset is driven through the tool's own geometry and parameter layers, and the measured crown settlement, sidewall convergence, and localised-defect magnitude are read at the chainages where the ground truth places them and compared to `incremental_pairs.csv`. Across all fifteen comparisons the mean absolute error is 0.58 mm and the maximum is 2.45 mm (Table 8). Crown settlement and convergence track the prescribed values to within 1 mm. The localised-defect probe shows a residual of about 2 mm before the defect appears (a detection noise floor), and the defect is recovered in the first epoch pair in which it is introduced (T2→T3, measured −13.7 mm against a −15.0 mm prescription), giving a detection latency of one epoch. This establishes mm-level accuracy of the deformation metrics themselves, not only of the static geometry.

**Table 8.** Measured versus prescribed incremental deformation (mm), T0→T5 time-series.

| Increment | Crown meas. | Crown GT | Conv. meas. | Conv. GT | Local meas. | Local GT |
|---|---|---|---|---|---|---|
| T0→T1 | −5.00 | −5.0 | 0.00 | 0.0 | −1.95 | 0.0 |
| T1→T2 | −6.96 | −7.0 | −4.80 | −5.0 | −2.45 | 0.0 |
| T2→T3 | −7.09 | −8.0 | −7.00 | −7.0 | −13.70 | −15.0 |
| T3→T4 | −10.00 | −10.0 | −10.00 | −10.0 | −9.60 | −10.0 |
| T4→T5 | −15.00 | −15.0 | −13.00 | −13.0 | −13.59 | −15.0 |

Mean absolute error 0.58 mm; maximum 2.45 mm.

### 11.6 Change detection, pipeline speed, and output integrity

On the time-series and local-deformation scenes the M3C2 stage resolved the prescribed localised deformation (polar maximum 83.5 mm) and flagged ten sections, with all 18 change-detection checks passing. The complete pipeline processed the 150K-point dataset in 2.56 s end to end, of which denoising was the dominant cost at 1.95 s; centerline and section extraction together took 0.53 s. The output stage produced a valid IFC4X3 model with 40 section proxies and a 3,840-vertex deformation shell, and a valid 117 KB PDF report, confirming that the geometric results transfer into the exchange formats without loss.

### 11.7 Discussion and limitations

The results establish that the pipeline is accurate on geometry (0.0005% radius error), accurate in deformation measurement (0.58 mm mean error against the time-series ground truth), safe in denoising (99.99% lining retention), and correct in clearance detection (100% precision and recall) on controlled data. The per-stage attribution (Table 5) further shows that each denoising stage removes the clutter type it targets, and the Frenet ablation (Table 7) confirms the sectioning contribution removes a curvature-specific ovality bias. Several limitations bound these claims. First, all validation is synthetic; field scans introduce registration error, scanner artefacts, and surface texture that synthetic scenes do not reproduce, so field validation is the necessary next step, and with identity registration the M3C2 Level-of-Detection machinery is not stress-tested. Second, the Frenet bias is characterised at a single curvature; a curvature sweep would establish how the bias scales. Third, the denoising stages are exercised on separate scenes rather than one combined labelled benchmark. Fourth, the RAG assistant is evaluated only architecturally: no retrieval-accuracy figure is reported because a curated question-and-answer reference set does not yet exist, and the generative output remains a draft for engineer review. Fifth, the severity thresholds are informed by KR C-08080 and KDS 27 25 00 but are not yet mapped clause by clause, so the system reports configurable engineering thresholds rather than certified regulatory compliance. The geometric, deformation, and denoising results rest on ground-truth comparison and are unaffected by these gaps; the open-source release, including the datasets and benchmark scripts, will accompany publication to support independent reproduction.
