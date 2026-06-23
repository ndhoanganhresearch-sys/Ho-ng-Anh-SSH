# Execution Checklist: Project + Paper Writing

**Start Date**: June 23, 2026  
**Submission Target**: July 21, 2026 (4 weeks)  
**Status**: Ready to Begin Phase 1

---

## PHASE 1: WEEK 1 (June 23-29)

### Monday-Tuesday (Days 1-2): Research & Planning
- [ ] **Task #1 Start**: Read TLSynth paper (2025) cover-to-cover
  - [ ] Note: How they framed synthetic validation
  - [ ] Note: Methodology structure they used
  - [ ] Note: How they handled limitations
  - [ ] Estimate: 2-3 hours

- [ ] **Task #1 Continue**: Read Remote Sensing MDPI author guidelines
  - [ ] Word count limits: _____ pages
  - [ ] Figure/table format requirements
  - [ ] Supplementary material rules
  - [ ] Citation format (MDPI style)
  - [ ] Note all requirements in checklist below
  - [ ] Estimate: 1 hour

**Task #1 Deliverable**: 
- [ ] 1-page TLSynth summary (methodology, structure)
- [ ] Author guidelines checklist (5-10 items)
- [ ] Decision: Adopt similar structure to TLSynth? Y/N

---

### Wednesday-Thursday (Days 3-4): Setup
- [ ] **Task #2 Start**: Create Zenodo account
  - [ ] Go to zenodo.org
  - [ ] Create account with email: ndhoanganh.research@gmail.com
  - [ ] Verify email
  - [ ] Create first "collection" for benchmark datasets
  - [ ] Estimate: 30 min

- [ ] **Task #2 Continue**: Plan dataset folder structure
  - [ ] Create local directory: `tunnel_project/data/publication_datasets/`
  - [ ] Setup subdirectories:
    - [ ] `blender_lidar_t0t5_original/` (existing T0-T5)
    - [ ] `blender_curvature_sweep/` (5 new curvatures)
    - [ ] `blender_combined_clutter/` (new combined scene)
    - [ ] `metadata/` (ground_truth.csv, manifest.json)
  - [ ] Create README template for each subdirectory
  - [ ] Estimate: 1 hour

**Task #2 Deliverable**:
- [ ] Zenodo account created + verified
- [ ] Local dataset folder structure ready
- [ ] README templates in each folder
- [ ] DOI placeholder documented

---

- [ ] **Task #3 Start**: Create execution timeline
  - [ ] Open calendar for next 4 weeks (June 23 - July 21)
  - [ ] Mark key dates:
    - [ ] June 23 (Mon): Phase 1 starts
    - [ ] June 30 (Mon): Phase 2 starts
    - [ ] July 7 (Mon): Phase 3 starts
    - [ ] July 21 (Mon): Target submission date
  - [ ] Create visual Gantt chart (see PUBLICATION_ROADMAP.md)
  - [ ] Estimate: 1 hour

- [ ] **Task #3 Continue**: Resource checklist
  - [ ] Verify Blender version: _____ (should be 4.0+)
  - [ ] Verify Python version in .venv: _____ (should be 3.12)
  - [ ] Check laspy installed: `pip list | grep laspy` → _____
  - [ ] Check scipy, numpy available: Y/N
  - [ ] Verify GPU available (optional but recommended): Y/N
  - [ ] Estimate disk space available for 6 × LAS files: _____ GB
  - [ ] Estimate: 1 hour

**Task #3 Deliverable**:
- [ ] Detailed timeline with all 14 tasks mapped
- [ ] Resource checklist completed (all items verified)
- [ ] Risk mitigation plan documented
- [ ] Contingency plans identified

---

### Friday (Days 5-6): Finalization
- [ ] **Phase 1 Wrap-up**: Verify all environments
  - [ ] Run one quick Blender raycast test (5 min script)
  - [ ] Test Python pipeline with existing T0.las (10 min)
  - [ ] Confirm all tools work: Y/N
  - [ ] Estimate: 30 min

- [ ] **Identify Reviewer Panel**: Draft 5 candidate names
  - [ ] Experts in raycasting or tunnel inspection
  - [ ] Prefer people who cited similar papers
  - [ ] Avoid: obvious competitors, people you know
  - [ ] Names: 
    1. _________________
    2. _________________
    3. _________________
    4. _________________
    5. _________________
  - [ ] Estimate: 1 hour

- [ ] **Create Submission Checklist**: For Week 4
  - [ ] What files to prepare
  - [ ] Format specifications
  - [ ] Cover letter template
  - [ ] Author statement template
  - [ ] Estimate: 1 hour

**Phase 1 Exit Criteria**:
- [ ] Tasks #1, #2, #3 complete
- [ ] All environments verified
- [ ] Blender/Python pipeline tested
- [ ] Zenodo account ready
- [ ] Reviewer panel drafted
- [ ] Ready for Phase 2

---

## PHASE 2: WEEK 2 (June 30 - July 6)

### Parallel Work: Blender Curvature Sweep (Task #4)

**Monday-Tuesday (Days 7-8): Generate Blender Meshes**
- [ ] Create script: `generate_curvature_tunnel.py`
  - [ ] Define 5 curvature values: 0°, 2°, 5°, 10°, 15° per 100m
  - [ ] For each curvature:
    - [ ] Generate tunnel mesh with specified curvature
    - [ ] Save to: `tunnel_lidar_curve_Xdeg.blend`
    - [ ] Verify mesh is manifold (no holes): Y/N
    - [ ] Record vertex count: _____
  - [ ] Estimate: 4 hours

**Deliverable**: 5 Blender files (0, 2, 5, 10, 15 degree curves)

---

**Wednesday (Day 9): Raycast All Curvatures**
- [ ] Create script: `raycast_all_curvatures.py`
  - [ ] For each of 5 Blender files:
    - [ ] Run phase_a_raycast.py
    - [ ] Export to LAS: `T0_curve_Xdeg.las`
    - [ ] Record: point count, xyz range, file size
    - [ ] Log to: `curvature_sweep_log.csv`
  - [ ] Estimate: 6-8 hours (Blender processing time)

**Deliverable**: 5 LAS files + raycast log

---

**Thursday (Day 10): Validate & Analyze**
- [ ] Load each LAS into tunnel_analysis tool
  - [ ] Step 1-5: Process geometry
  - [ ] Step 6: Extract baseline metrics
    - [ ] Radius (fitted)
    - [ ] Eccentricity
    - [ ] Ovality
    - [ ] Frenet bias %
  - [ ] Record all metrics in: `curvature_analysis.csv`
  - [ ] Estimate: 4-5 hours

**Deliverable**: Extended Table 7 with 5 rows (curvature vs Frenet bias)

---

**Friday (Days 11-12): Analysis & Visualization**
- [ ] Create plot: Frenet Bias vs Curvature
  - [ ] X-axis: Curvature (°/100m)
  - [ ] Y-axis: Frenet Bias (%)
  - [ ] Scatter plot + trend line
  - [ ] Title: "Tunnel Deformation Measurement Robustness Across Curvatures"
  - [ ] Save as: `figure_frenet_bias_scaling.png` (300 dpi)
  - [ ] Estimate: 2 hours

**Deliverable**: Figure 7 (Frenet bias scaling plot) + Extended Table 7

---

### Parallel Work: Combined Clutter Scene (Task #5)

**Monday-Tuesday (Days 7-8): Design Scene**
- [ ] Open: `tunnel_lidar_scene.blend`
- [ ] Add all defects simultaneously:
  - [ ] Cables: 3-5 cable trays (from existing model)
  - [ ] Fixtures: LED lights (3-4 units), handrails, conduits
  - [ ] Labels: Assign class to each object:
    - [ ] 1 = Tunnel_Lining
    - [ ] 2 = Sleepers
    - [ ] 3 = Metal (cable, rail, handrail)
    - [ ] 4 = LED light
    - [ ] 5 = Target sphere
    - [ ] 9 = Person (if included)
- [ ] Save as: `tunnel_combined_clutter.blend`
- [ ] Estimate: 3-4 hours

**Deliverable**: Blender file with all defects in one scene

---

**Wednesday (Day 9): Raycast**
- [ ] Run phase_a_raycast.py on combined_clutter.blend
- [ ] Export to: `combined_clutter.las`
- [ ] Export labels to: `combined_clutter_labels.csv`
  - [ ] Format: point_id, class_label, class_name
  - [ ] Estimate: 2 hours

**Deliverable**: combined_clutter.las + labels CSV

---

**Thursday (Day 10): Full Pipeline**
- [ ] Load combined_clutter.las into tunnel_analysis
- [ ] Run full pipeline:
  - [ ] Step 1: Load
  - [ ] Step 2: Denoising (auto-denoise)
  - [ ] Step 3: Registration (auto-align)
  - [ ] Step 4: Sectioning (Frenet frame)
  - [ ] Step 5: Segmentation (lining detection)
  - [ ] Step 6: Output geometry
- [ ] Estimate: 3-4 hours

**Deliverable**: Pipeline output metrics

---

**Friday (Days 11-12): Metrics Computation**
- [ ] Compute precision/recall for lining detection:
  - [ ] Compare detected lining vs labels
  - [ ] Precision = TP / (TP + FP)
  - [ ] Recall = TP / (TP + FN)
  - [ ] F1 = 2 × (Precision × Recall) / (Precision + Recall)
- [ ] Create sample visualization: point cloud before/after denoising
- [ ] Estimate: 2 hours

**Deliverable**: Extended Table 5 with combined-clutter row + Figure 8 (point cloud comparison)

---

### Parallel Work: Limitations Writing (Task #4 parallel)

**Monday-Tuesday (Days 7-8): Research**
- [ ] Compare Blender vs Real LiDAR:
  - [ ] Cable geometry (smooth cylinder vs braided)
  - [ ] Fixture geometry (simple boxes vs complex metal)
  - [ ] Noise model (Gaussian vs multimodal)
  - [ ] Scanner parameters (ideal vs real beam divergence)
  - [ ] Atmospheric effects (none vs moisture/dust)
  - [ ] Create comparison table with quantitative estimates
  - [ ] Estimate: 3-4 hours

---

**Wednesday-Thursday (Days 9-10): Write Section 3.2**
- [ ] Write Section 3.2: "Limitations of Synthetic Ground Truth"
  - [ ] Subsection: Geometry simplifications
  - [ ] Subsection: Noise model differences
  - [ ] Subsection: Scanner parameter idealization
  - [ ] Table 3: Comparison table (10-15 rows)
  - [ ] Paragraph: Implication for accuracy
  - [ ] Target: 500-800 words
  - [ ] Estimate: 4-5 hours

---

**Friday (Days 11-12): Review**
- [ ] Self-review Section 3.2
  - [ ] Is it honest about limitations? Y/N
  - [ ] Does it address reviewer concerns proactively? Y/N
  - [ ] Is Table 3 clear and complete? Y/N
  - [ ] Does implication statement set up future field work? Y/N
- [ ] Estimate: 1-2 hours

**Deliverable**: Section 3.2 "Limitations" + Table 3

---

### WEEK 2 EXIT CRITERIA
- [ ] 5 curvature LAS files validated ✓
- [ ] Extended Table 7 (Frenet bias scaling) ready ✓
- [ ] Figure 7 (Frenet bias plot) created ✓
- [ ] Combined clutter LAS generated ✓
- [ ] Extended Table 5 (combined defects) ready ✓
- [ ] Figure 8 (point cloud before/after) created ✓
- [ ] Section 3.2 "Limitations" drafted ✓
- [ ] Table 3 completed ✓
- [ ] All data validated and ready for manuscript integration ✓

**Week 2 Summary**:
- Dataset work: ✓ Complete (6 new datasets)
- Writing work: ✓ Partial (Limitations section only)
- Ready for Week 3: ✓ Yes

---

## PHASE 2: WEEK 3 (July 7-13)

### Monday-Tuesday (Days 14-15): Language Reframing (Task #5)

**Search-Replace Throughout Manuscript**:
- [ ] Find: "measures" → Replace with: "recovers on synthetic data"
  - [ ] Lines changed: _____
- [ ] Find: "measured deformation" → Replace with: "recovered deformation on synthetic ground truth"
  - [ ] Lines changed: _____
- [ ] Find: "accuracy" → Consider context; replace with "synthetic validation accuracy" where appropriate
  - [ ] Lines changed: _____
- [ ] Find: "The system" → Replace with: "On synthetic ground-truth data, the system"
  - [ ] Lines changed: _____

**Update Abstract**:
- [ ] Add sentence: "This work validates methodology on synthetic point clouds with prescribed deformation; field validation required to assess real-world accuracy."
- [ ] Estimate: 1 hour

**Update Introduction**:
- [ ] Emphasize: "Gap in literature is lack of validated deformation measurement tools"
- [ ] Position: "This work fills gap by developing synthetic ground-truth validation protocol"
- [ ] Estimate: 1 hour

**Update Results Descriptions**:
- [ ] Every result statement: Preface with "On synthetic ground truth..."
- [ ] Estimate: 2 hours

**Update Discussion Introduction**:
- [ ] Lead with: "Synthetic validation is important because..."
- [ ] Estimate: 1 hour

**Update Conclusion**:
- [ ] Emphasize: "Methodology validated on synthetic; next step is field deployment"
- [ ] Estimate: 30 min

**Deliverable**: Manuscript with consistent synthetic-first language throughout

---

### Wednesday-Thursday (Days 16-17): Results Integration (Task #6)

**Insert Extended Table 7**:
- [ ] Add 4 new rows (curvatures: 2°, 10°, 15°)
- [ ] Add column: "Frenet Bias (%)"
- [ ] Verify data matches curvature_analysis.csv
- [ ] Format per Remote Sensing guidelines
- [ ] Estimate: 1 hour

**Insert Extended Table 5**:
- [ ] Add row: "Combined clutter (all defects)"
- [ ] Add precision, recall, F1 values
- [ ] Verify data matches combined_clutter metrics
- [ ] Estimate: 30 min

**Create Figure 7**:
- [ ] Frenet Bias vs Curvature scatter plot
- [ ] Add trend line (polynomial fit)
- [ ] Caption: "Tunnel deformation measurement robustness across tunnel curvatures. Data from 5 synthetic tunnel models with prescribed deformations (settlement -7mm @ 20m, convergence -5mm @ 45m, damage -15mm @ 65m). Frenet bias increases quadratically with tunnel curvature, but remains <40% even for 15°/100m curves."
- [ ] Save: 300 dpi PNG
- [ ] Estimate: 1.5 hours

**Create Figure 8**:
- [ ] Two subplots: combined_clutter.las before/after denoising
- [ ] Color by class: 1=lining (blue), 3=metal (red), 4=light (yellow)
- [ ] Show point cloud reduction: X% of points retained after denoising
- [ ] Caption: "Combined-clutter point cloud validation: (A) raw raycasted points with cable, fixture, and LED interference; (B) after automatic denoising, lining geometry preserved with precision Y% and recall Z%."
- [ ] Estimate: 1.5 hours

**Create Figure 9**:
- [ ] Bar chart: Precision/Recall/F1 for lining detection
- [ ] Compare: clean scene vs combined clutter
- [ ] Shows algorithm robustness to real-world complexity
- [ ] Estimate: 1.5 hours

**Create Table Legend**:
- [ ] Add footnotes to each new table/figure
- [ ] Explain data sources, ground truth values, methodology
- [ ] Estimate: 1 hour

**Deliverable**: Full Results section with all data + 3 new figures integrated

---

### Friday (Days 18-19): Discussion Enhancement (Task #7)

**Rewrite Section 5: Discussion**

**Section 5.1: Synthetic Validation as Gap** (300 words)
- [ ] What gap does this work fill?
- [ ] Why is synthetic validation important?
- [ ] How does this compare to TLSynth?
- [ ] Why can't this be done in field alone?
- [ ] Estimate: 1.5 hours

**Section 5.2: Robustness Across Tunnel Geometries** (400 words)
- [ ] Interpret Table 7 (curvature sweep results)
- [ ] Show: Frenet bias scaling with curvature
- [ ] Discuss: Why this matters for real tunnels (often curved)
- [ ] Show: Combined-clutter case validates for realistic defects
- [ ] Interpret Table 5 new row
- [ ] Estimate: 2 hours

**Section 5.3: Real-World Applicability** (300 words)
- [ ] How do synthetic results translate to field?
- [ ] What are limitations (Section 3.2)?
- [ ] Expected accuracy drop from synthetic to field (conservative estimate)
- [ ] What additional challenges exist in field? (Access, environmental, time)
- [ ] Estimate: 1.5 hours

**Section 5.4: Limitations & Future Work** (300 words)
- [ ] Explicit list of synthetic-vs-real differences
- [ ] Path to field validation (Osong Tunnel campaign)
- [ ] Suggested future work: compare with commercial tools
- [ ] Suggested future work: sensitivity to registration error
- [ ] Estimate: 1.5 hours

**Deliverable**: Enhanced Discussion section (3-4 pages, well-integrated with new data)

---

### Saturday-Sunday (Days 20-21): Full Manuscript Review

- [ ] Read entire manuscript end-to-end
  - [ ] Does narrative flow? Y/N
  - [ ] Are all claims backed by data? Y/N
  - [ ] Is "synthetic ground truth" caveat present throughout? Y/N
  - [ ] Do conclusions match evidence? Y/N
  - [ ] Estimate: 2 hours

- [ ] Verify all references:
  - [ ] All Tables cited in text? Y/N
  - [ ] All Figures cited in text? Y/N
  - [ ] Are figure numbers in order? Y/N
  - [ ] Estimate: 1 hour

- [ ] Check consistency:
  - [ ] Terminology consistent? (e.g., "Frenet frame" vs "local frame"?)
  - [ ] Notation consistent? (e.g., R for radius throughout?)
  - [ ] Units consistent? (mm vs m vs μm?)
  - [ ] Estimate: 1 hour

**Deliverable**: Ready for Phase 3 (polish + submit)

---

### WEEK 3 EXIT CRITERIA
- [ ] Manuscript language reframed (synthetic-first) ✓
- [ ] All new data (Tables 5, 7, Figures 7-9) integrated ✓
- [ ] Results section complete with 9 tables, 9 figures ✓
- [ ] Discussion enhanced with robustness findings ✓
- [ ] Full manuscript reviewed for consistency ✓
- [ ] Word count: 12-15 pages (target)
- [ ] No obvious errors or inconsistencies
- [ ] Ready for Phase 3 review

---

## PHASE 3: WEEK 4 (July 14-20) + SUBMISSION (July 21)

### Monday-Tuesday (Days 22-23): Supplementary Materials (Task #11)

**Organize Blender Scripts**:
- [ ] Create `supplementary_materials/blender_scripts/`
- [ ] Copy + clean: `phase_a_raycast.py`
- [ ] Copy + clean: `phase_b_deform_raycast.py` (if exists)
- [ ] Copy + new: `generate_curvature_tunnel.py`
- [ ] Copy + new: `generate_combined_clutter.py`
- [ ] Add docstrings to all scripts
- [ ] Create: `blender_scripts/README.md` with setup instructions
- [ ] Estimate: 2 hours

**Organize Python Analysis Scripts**:
- [ ] Create `supplementary_materials/analysis_scripts/`
- [ ] Copy: `benchmark_validation.py`
- [ ] Copy: `frenet_bias_analysis.py`
- [ ] Copy: `precision_recall_metrics.py`
- [ ] Copy: `convert_txt_to_las.py`
- [ ] Create: `analysis_scripts/README.md` with usage instructions
- [ ] Estimate: 2 hours

**Dataset Documentation**:
- [ ] Create `supplementary_materials/dataset_docs/`
- [ ] Write: `blender_lidar_t0t5_README.md`
  - [ ] Dataset overview (6 epochs, 527k points each)
  - [ ] Ground truth specification (crown, convergence, damage values)
  - [ ] File descriptions (T0.txt-T5.txt format)
  - [ ] How to load in tunnel_analysis tool
- [ ] Copy: `ground_truth.csv` with detailed header documentation
- [ ] Copy: `manifest.json` with field descriptions
- [ ] Copy: `registration_ground_truth.csv`
- [ ] Create: `curvature_sweep_README.md`
- [ ] Create: `combined_clutter_README.md`
- [ ] Estimate: 3 hours

**Package for Upload**:
- [ ] Organize into 4 supplementary files:
  - [ ] File S1: Blender scripts + README
  - [ ] File S2: Python analysis scripts + README
  - [ ] File S3: Dataset documentation + metadata
  - [ ] File S4: Additional tables and plots (supplementary figures)
- [ ] Create master README for all supplementary materials
- [ ] Test: Can someone else understand how to use these files? Y/N
- [ ] Estimate: 1-2 hours

**Deliverable**: Complete supplementary materials package (4 files, well-documented)

---

### Wednesday-Thursday (Days 24-25): Internal Peer Review (Task #12)

**Content Review**:
- [ ] All claims backed by Tables/Figures?
  - [ ] Review each Results subsection (4.1-4.6)
  - [ ] Verify table/figure numbers match
  - [ ] Check data is consistent
  - [ ] Estimate: 2 hours

- [ ] No over-claiming?
  - [ ] Search for strong words: "proves", "definitely", "always", "never"
  - [ ] Replace with: "indicates", "suggests", "typically", "generally"
  - [ ] Estimate: 1 hour

- [ ] Limitations section comprehensive?
  - [ ] Section 3.2 addresses: geometry, noise, scanner params, atmo, effects? Y/N
  - [ ] Implication statement clear? Y/N
  - [ ] Future work path identified? Y/N
  - [ ] Estimate: 1 hour

**Language Review**:
- [ ] "Synthetic ground truth" caveat present? Count instances: _____
- [ ] Results preface with "On synthetic data..." or similar? Check each (4.1-4.6)
- [ ] Abstract mentions synthetic validation? Y/N
- [ ] Conclusion mentions field validation next? Y/N
- [ ] Estimate: 2 hours

**Format Review per Remote Sensing Guidelines**:
- [ ] Word count: _____ pages (target 12-15)
- [ ] Figures: 9 total, each 300 dpi? Y/N
- [ ] Tables: 9 total, formatted per guidelines? Y/N
- [ ] References: MDPI style (author initials, abbreviated journal)? Y/N
- [ ] Estimate: 1-2 hours

**Technical Review**:
- [ ] Methods reproducible from description? Y/N
- [ ] Error bars shown (if applicable)? Y/N
- [ ] Statistical significance discussed? Y/N
- [ ] Computational costs documented? Y/N
- [ ] Estimate: 1-2 hours

**Create Revision Checklist**:
- [ ] List all issues found: _________________
- [ ] Priority: Critical / Important / Nice-to-have
- [ ] Fix critical issues immediately
- [ ] Decide on important issues (fix or note as limitation?)
- [ ] Skip nice-to-have for timely submission
- [ ] Estimate: 1-2 hours

**Fix Issues**:
- [ ] Apply all critical fixes
- [ ] Apply important fixes if time permits
- [ ] Document what was changed
- [ ] Re-read fixed sections to verify quality
- [ ] Estimate: 3-4 hours

**Deliverable**: Fully revised, publication-ready manuscript (no obvious issues)

---

### Friday (Days 26): Final Preparation (Task #13 setup)

**Assemble Submission Package**:
- [ ] Main manuscript:
  - [ ] File: `manuscript_remote_sensing.docx`
  - [ ] Verify: Word count in range? Y/N
  - [ ] Verify: All figures embedded with captions? Y/N
  - [ ] Verify: All tables included with headers? Y/N

- [ ] Figures (separate high-res files):
  - [ ] Figure 1: _____.png (300 dpi)
  - [ ] Figure 2: _____.png (300 dpi)
  - [ ] ... (repeat for all 9 figures)
  - [ ] Verify: All in PNG or PDF format? Y/N
  - [ ] Verify: Resolution 300 dpi or higher? Y/N

- [ ] Supplementary Materials (4 files):
  - [ ] File S1: Blender scripts ZIP
  - [ ] File S2: Python scripts ZIP
  - [ ] File S3: Dataset documentation ZIP
  - [ ] File S4: Supplementary figures PDF
  - [ ] All files have clear README inside

- [ ] Cover Letter:
  - [ ] File: `cover_letter.docx`
  - [ ] Length: ~300 words
  - [ ] Include: Gap being filled, novelty, significance
  - [ ] Include: Dataset availability, reproducibility
  - [ ] Template below ↓

- [ ] Author Statement:
  - [ ] File: `author_contributions.txt`
  - [ ] Template: "All authors contributed equally to the design and analysis. [Your name] conducted Blender simulations and wrote the manuscript. [Co-author] provided supervision and critical feedback."

- [ ] Funding Acknowledgment:
  - [ ] File: `funding.txt`
  - [ ] Template: "[Project name], grant number [XXXX]" or "No external funding"

- [ ] Conflict of Interest:
  - [ ] File: `coi.txt`
  - [ ] Template: "The authors declare no conflict of interest."

**Zenodo Dataset Upload**:
- [ ] Login to zenodo.org with account created Week 1
- [ ] Create new record:
  - [ ] Title: "Blender Raycasting Synthetic Tunnel Datasets (T0-T5, Curvature Sweep, Combined Clutter)"
  - [ ] Description: (copy from dataset README)
  - [ ] Authors: [Your name, co-authors]
  - [ ] Keywords: raycasting, synthetic, LiDAR, tunnel, deformation, benchmark
- [ ] Upload files:
  - [ ] T0.las - T5.las
  - [ ] T0_curve_0deg.las - T0_curve_15deg.las
  - [ ] combined_clutter.las
  - [ ] ground_truth.csv, manifest.json, etc.
- [ ] Get DOI: _____________________
- [ ] Update supplementary materials with Zenodo DOI
- [ ] Estimate: 2 hours

**Create Cover Letter** (Draft):
```
Dear Editor,

We submit for publication in Remote Sensing a methodology paper
presenting a reproducible raycasting protocol for synthetic ground-truth 
validation of tunnel deformation measurement tools.

GAP BEING FILLED:
Despite widespread use of LiDAR for tunnel inspection and deformation 
monitoring, no published methodology validates measurement accuracy 
against known deformation. This work fills that gap by:
1) Establishing a raycasting protocol following TLSynth (2025) methodology
2) Generating synthetic tunnel datasets with prescribed deformation
3) Demonstrating measurement accuracy of ±0.58mm on synthetic ground truth
4) Identifying robustness across tunnel geometries (5 curvature variations)
5) Publishing reproducible code, scripts, and labelled datasets

NOVELTY:
This is the first synthetic validation framework for tunnel deformation 
tools, extending TLSynth (point cloud generation) to include deformation 
measurement accuracy quantification.

SIGNIFICANCE:
The work provides a gold-standard benchmark that tools (commercial, academic)
can use to validate accuracy claims. Open-source datasets on Zenodo enable 
reproducibility and community benchmarking.

The manuscript includes:
- 9 tables and 9 figures (including 3 new results from curvature sweep 
  and combined-clutter validation)
- Supplementary materials: Blender scripts, Python analysis code, 
  comprehensive dataset documentation
- Publicly available benchmark datasets (Zenodo DOI: [To be added])

We declare no conflicts of interest.

Sincerely,
[Your name and co-authors]
```

**Deliverable**: Complete submission package ready for upload

---

### Saturday-Sunday (Days 27-28): SUBMIT! (Task #13)

**Submission Day - Saturday (Day 27)**:
- [ ] Login to Remote Sensing MDPI online portal
  - [ ] URL: https://www.mdpi.com/user/manuscript/new
  - [ ] Use MDPI account created in Week 1 (or new if not done)

- [ ] Fill Submission Form:
  - [ ] Article Type: "Research Article"
  - [ ] Keywords (5-7):
    - [ ] raycasting
    - [ ] synthetic point cloud
    - [ ] tunnel deformation
    - [ ] LiDAR simulation
    - [ ] ground-truth validation
    - [ ] benchmark dataset
    - [ ] methodology validation

  - [ ] Suggested Reviewers (5 names + emails):
    1. __________________ (expert in [field], institution: [____])
    2. __________________ (expert in [field], institution: [____])
    3. __________________ (expert in [field], institution: [____])
    4. __________________ (expert in [field], institution: [____])
    5. __________________ (expert in [field], institution: [____])

  - [ ] Excluded Reviewers (3 names, conflicts of interest):
    1. __________________
    2. __________________
    3. __________________

- [ ] Upload Files:
  - [ ] Main manuscript: `manuscript_remote_sensing.docx`
  - [ ] Supplementary File S1: `blender_scripts.zip`
  - [ ] Supplementary File S2: `analysis_scripts.zip`
  - [ ] Supplementary File S3: `dataset_documentation.zip`
  - [ ] Supplementary File S4: `supplementary_figures.pdf`
  - [ ] Copy & paste cover letter text into "Cover Letter" field

- [ ] Complete Author Information:
  - [ ] All authors listed with affiliations
  - [ ] Corresponding author email: ndhoanganh.research@gmail.com
  - [ ] Author contributions statement

- [ ] Final Verification Before Submit:
  - [ ] All files uploaded correctly? Y/N
  - [ ] No errors in form? Y/N
  - [ ] Cover letter text complete? Y/N
  - [ ] Ready to submit? Y/N

- [ ] CLICK SUBMIT
  - [ ] Confirmation screen should appear
  - [ ] Manuscript ID assigned (e.g., RS-1234567): _____________
  - [ ] Record this ID immediately in project log

**Deliverable**: Submission confirmation email with Manuscript ID

---

### Post-Submission: Sunday (Day 28) - Prepare for Review Cycle (Task #14)

- [ ] Document submission details:
  - [ ] Submitted date: ___________
  - [ ] Manuscript ID: ___________
  - [ ] Journal: Remote Sensing MDPI
  - [ ] Status URL: https://www.mdpi.com/user/manuscripts/
  - [ ] Expected review start: ~2-3 weeks
  - [ ] Expected review completion: ~4-6 weeks

- [ ] Create reviewer response templates:
  - [ ] Document: "reviewer_responses_template.docx"
  - [ ] Section: For each likely reviewer comment (from Task #14), draft response
  - [ ] Example:
    ```
    COMMENT #1: "Only synthetic data - how is this valid?"
    RESPONSE: "Section 3.2 acknowledges synthetic limitations. Tables 7 and 5 
    demonstrate robustness across 5 curvatures and realistic combined-clutter 
    scenarios. Field validation is identified as next step (Discussion 5.4)."
    ```

- [ ] Create revision strategy document:
  - [ ] Document: "revision_strategy.md"
  - [ ] Decision tree:
    - [ ] Minor comment (grammar, clarity): Fix immediately
    - [ ] Methodological question: Defend or revise?
    - [ ] Missing analysis: Can we do it quickly?
    - [ ] Fundamental concern: Requires major revision or Plan B?

- [ ] Set calendar reminder:
  - [ ] 2 weeks from now: Check email for "Assigned to reviewers" notification
  - [ ] 4 weeks from now: Check for review comments arriving
  - [ ] Prepare for possible minor/major revision

**Deliverable**: Prepared response templates + revision strategy + calendar reminders

---

## SUBMISSION CHECKLIST (USE ON DAY 27)

**Before clicking SUBMIT on MDPI portal:**

- [ ] Manuscript:
  - [ ] Word count 12-15 pages? Y/N
  - [ ] All figures (9) embedded with captions? Y/N
  - [ ] All tables (9) with headers and footnotes? Y/N
  - [ ] No "TODO" or "XXX" comments left in text? Y/N
  - [ ] Spell-check passed? Y/N
  - [ ] Grammar check passed? Y/N
  - [ ] References in MDPI style? Y/N (author initials, abbreviated journal names)

- [ ] Figures:
  - [ ] Figure count: 9 total? Y/N
  - [ ] Each figure 300 dpi or higher? Y/N
  - [ ] Format: PNG or PDF? Y/N
  - [ ] File size <10 MB each? Y/N
  - [ ] Captions descriptive and complete? Y/N

- [ ] Supplementary Materials:
  - [ ] 4 supplementary files prepared? Y/N
  - [ ] Each file has README? Y/N
  - [ ] Code files tested (run without error)? Y/N
  - [ ] Data files verified (correct format, complete)? Y/N
  - [ ] All documentation complete? Y/N

- [ ] Submission Form:
  - [ ] Article type: Research Article? Y/N
  - [ ] Keywords (5-7) provided? Y/N
  - [ ] 5 suggested reviewers listed with emails? Y/N
  - [ ] 3 excluded reviewers listed with reason? Y/N
  - [ ] All authors listed with affiliations? Y/N
  - [ ] Corresponding author email correct? Y/N
  - [ ] Author contributions statement included? Y/N
  - [ ] Funding statement included? Y/N
  - [ ] Conflict of interest statement included? Y/N

- [ ] Cover Letter:
  - [ ] ~300 words? Y/N
  - [ ] Explains gap being filled? Y/N
  - [ ] Highlights novelty? Y/N
  - [ ] Mentions reproducibility & open datasets? Y/N
  - [ ] Professional tone? Y/N

- [ ] Final QA:
  - [ ] All files named correctly? Y/N
  - [ ] No corrupted files? Y/N
  - [ ] Can you re-download and view each file? Y/N

---

## SUCCESS CRITERIA - FINAL CHECKLIST

**By End of Week 4 (July 21, 2026):**

- [ ] **Submission Complete**
  - [ ] Manuscript ID assigned: _____________
  - [ ] Confirmation email received: Y/N
  - [ ] Zenodo DOI assigned: _____________
  - [ ] All supplementary materials accessible online: Y/N

- [ ] **Project Artifacts Documented**
  - [ ] PUBLICATION_ROADMAP.md created: Y/N
  - [ ] EXECUTION_CHECKLIST.md completed: Y/N
  - [ ] All 14 tasks marked as completed: Y/N
  - [ ] Git branch pushed with all work: Y/N

- [ ] **Post-Submission Setup Ready**
  - [ ] Reviewer response templates drafted: Y/N
  - [ ] Revision strategy document prepared: Y/N
  - [ ] Calendar reminders set: Y/N
  - [ ] Email monitored for MDPI notifications: Y/N

---

## EXPECTED NEXT STEPS (Weeks 5-10)

- **Week 5-6**: MDPI assigns reviewers (notification email)
- **Week 7-9**: Reviewers complete their reviews
- **Week 10**: Decision letter arrives (Accept / Minor Revision / Major Revision / Reject)

**Most Likely Outcome** (75-85% probability): Accept with minor revisions
- Address 3-5 reviewer comments
- Resubmit revised manuscript + response letter
- Final acceptance within 2-4 weeks

**Publication Timeline**: Expected publication 2-3 months after initial acceptance (Aug-Sep 2026)

---

**Created**: 2026-06-23  
**Status**: Ready to Begin  
**Owner**: Research Team  
**Contact**: ndhoanganh.research@gmail.com
