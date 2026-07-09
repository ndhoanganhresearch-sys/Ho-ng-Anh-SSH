## 8. Multi-Epoch Change Detection

Deformation is assessed by comparing a current scan against an earlier reference. The change-detection layer (`timeseries.py`) computes signed surface displacement with M3C2, derives a per-section severity classification (`section_warnings.py`), and assembles spatiotemporal trends across a survey series.

### 8.1 M3C2 distance and Level of Detection

Surface change is measured with the Multiscale Model to Model Cloud Comparison algorithm [14], through the open-source py4dgeo implementation [28]. For each core point, M3C2 estimates a local normal over a search radius of 0.5 m and measures the mean surface position of each epoch within a cylinder of radius 0.5 m oriented along that normal; the signed distance between the two means is the displacement. The algorithm also returns a Level of Detection (LoD), the displacement magnitude below which a change cannot be distinguished from registration and roughness noise at the stated confidence. A displacement is reported as significant only when it exceeds the local LoD:

$$ \text{significant} \iff |d_{\text{M3C2}}| > \text{LoD} \tag{12} $$

Tying significance to a spatially varying LoD avoids a single global threshold, so smooth, well-registered regions resolve smaller changes than rough or sparsely sampled ones.

### 8.2 Section severity classification

For reporting, displacement is summarised per section as changes in width (*dW*), height (*dH*), radius (*dR*), ovality (*dOval*), and eccentricity (*dEcc*) relative to the reference epoch. Each change is mapped to a status of OK, CAUTION, or CRITICAL. The linear metrics use absolute thresholds of 10 mm (CAUTION) and 25 mm (CRITICAL); ovality uses 0.5% and 1.0%. These thresholds are informed by the survey and tolerance provisions of the Korean railway and tunnel standards KR C-08080 and KDS 27 25 00 [3,4]; the exact clause-level correspondence is an acknowledged limitation (Section 11.6) and the thresholds are exposed as configurable parameters rather than asserted as certified compliance values.

Warnings must stay localised to the chainage where deformation occurs, not smear across the whole tunnel. For ovality and eccentricity the classifier therefore adds a local-anomaly test: a section is flagged when its change exceeds the series median by a robust margin,

$$ t_{\text{local}} = \mathrm{median}(\Delta) + \max\big(3\,\hat{\sigma},\; t_{\text{floor}}\big), \qquad \hat{\sigma} = 1.4826\cdot \mathrm{MAD}(\Delta) \tag{13} $$

where Δ is the set of per-section changes and *t*~floor~ a metric-specific floor. The robust margin suppresses a uniform offset from imperfect registration, which would otherwise raise every section at once, while preserving a genuine localised defect that stands out from its neighbours. A clearance violation at any section is classified CRITICAL directly.

### 8.3 Spatiotemporal trends

For a survey series the layer compares every later epoch against the first, the T0→T*n* baseline (`spatiotemporal_series`). Each comparison contributes a per-epoch summary: the median displacement and the 95th percentile of absolute displacement, p95~abs~. The p95~abs~ statistic is reported as the trend value because whole-cloud median displacement stays near zero when deformation is localised, masking a developing defect that the upper percentile reveals. Core points are decimated to a working budget (default 50,000) so that a long series remains tractable. A complementary forecast routine flags the epoch at which an extrapolated trend would cross the caution (10 mm) or critical (25 mm) level, giving early warning before a threshold is reached.

The current implementation compares against the fixed baseline T0; reporting incremental epoch-to-epoch change (T*n*→T*n*₊₁) alongside the baseline trend is identified as future work in Section 12.
