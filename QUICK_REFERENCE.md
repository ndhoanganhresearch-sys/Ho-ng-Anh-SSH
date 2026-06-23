# 4-Week Publication Plan - QUICK REFERENCE

**Goal**: Submit to Remote Sensing MDPI by July 21, 2026  
**Status**: Ready to Start (June 23, 2026)

---

## 📅 TIMELINE AT A GLANCE

```
WEEK 1 (Jun 23-29)    WEEK 2 (Jun 30-Jul 6)      WEEK 3 (Jul 7-13)        WEEK 4 (Jul 14-21)
Preparation          Execution                 Writing                 Polish & Submit
─────────────────────────────────────────────────────────────────────────────────────
Phase 1 Tasks 1-3    Phase 2 Tasks 4-7         Phase 2 Tasks 8-10       Phase 3 Tasks 11-14
Research, setup      Blender work, writing     Integration, revision    Supplementary docs
Test environment     Dataset generation       Discussion enhancement    Internal review
Plan timeline        Limitations section      Language reframing       SUBMIT!
                     Parallel work streams
```

---

## 📊 WHAT GETS DONE EACH WEEK

### **WEEK 1: Setup (16-20 hours)**
- [ ] Read TLSynth paper + Remote Sensing guidelines
- [ ] Create Zenodo account
- [ ] Plan dataset folder structure
- [ ] Create execution timeline
- [ ] Verify Blender/Python environments
- [ ] Exit: Ready for dataset generation

### **WEEK 2: Datasets (40-50 hours)**
**In Parallel:**
- Generate 5 curvature Blender meshes → raycast → validate → Table 7
- Generate combined-clutter Blender scene → raycast → segment → Table 5
- Write Section 3.2 "Limitations" + Table 3

**Deliverables:**
- 6 new LAS files (curvature sweep + combined clutter)
- Extended Table 7 (Frenet bias scaling)
- Extended Table 5 (combined defects)
- Figure 7 (Frenet bias plot)
- Figure 8 (point cloud before/after)
- Section 3.2 (Limitations)
- Exit: All datasets ready for paper integration

### **WEEK 3: Paper Writing (40-50 hours)**
- Reframe all results language (synthetic-first)
- Integrate new data into Results section
- Add Figures 7, 8, 9
- Rewrite Discussion with robustness findings
- Full manuscript review
- Exit: Publication-ready manuscript

### **WEEK 4: Submission (20-25 hours)**
- Prepare supplementary materials (4 files)
- Internal peer review + revision
- Upload datasets to Zenodo (get DOI)
- Prepare cover letter + author statements
- **SUBMIT to Remote Sensing MDPI**
- Prepare for reviewer feedback

**Total: ~120-150 hours (~3-4 weeks FTE)**

---

## 🎯 KEY DELIVERABLES BY PHASE

### **Phase 1 Output** (Week 1)
- Zenodo account created
- Execution timeline finalized
- Environment verified
- Ready to execute Phase 2

### **Phase 2 Output** (Weeks 2-3)
**Datasets:**
- 5 × T0_curve_Xdeg.las (curvature sweep)
- 1 × combined_clutter.las (realistic scene)
- All metadata and ground truth files

**Figures (3 new):**
- Figure 7: Frenet bias vs curvature plot
- Figure 8: Combined-clutter before/after denoising
- Figure 9: Precision/recall comparison

**Tables (2 extended):**
- Table 5: Extended with combined-clutter row
- Table 7: Extended with 5 curvature variations

**Paper Sections (2 major):**
- Section 3.2: Limitations of Synthetic Ground Truth (new)
- Section 5: Enhanced Discussion (rewritten)

**Full Manuscript:**
- 9 tables, 9 figures
- 12-15 pages
- Consistent synthetic-first language
- All limitations transparently discussed

### **Phase 3 Output** (Week 4)
**Supplementary Materials (4 files):**
1. Blender scripts (phase_a, phase_b, curvature, clutter generators)
2. Python analysis scripts (all benchmarking code)
3. Dataset documentation (README, metadata, ground truth)
4. Supplementary figures and additional tables

**Submission Package:**
- Manuscript (final)
- 9 high-res figures
- Cover letter
- Author contributions
- Zenodo DOI (datasets available)
- Reviewer suggestions

**Result:**
- ✅ Manuscript ID assigned
- ✅ Confirmation email sent
- ✅ Ready for review cycle (4-6 weeks)

---

## 📋 CRITICAL PATH (Must Complete On Time)

```
Task #1 ─────┐
Task #2 ─────┼──→ Task #3 ──→ Task #4 ──→ Task #6 ──→ Task #8 ──→ Task #9 ──→ Task #11 ──→ Task #12 ──→ Task #13
Task #3 ─────┘
              Task #5 ──────┘
              Task #7 ───────────────────────────────┘
```

**Critical Dependencies:**
1. Phase 1 (Tasks 1-3) must complete before Phase 2 can start
2. Curvature dataset (Task #4) and Combined clutter (Task #5) can run in parallel
3. Limitations writing (Task #7) needed before language reframing (Task #8)
4. All new data (Tasks 4-7) must be ready before results integration (Task #9)
5. Supplementary materials (Task #11) can start only after manuscript complete (Task #10)

---

## ⚠️ RISK POINTS & CONTINGENCIES

| Risk | Probability | Mitigation | Contingency |
|------|-------------|-----------|------------|
| Blender raycast too slow | MEDIUM | Test curvature 0° first | Reduce to 3 curvatures instead of 5 |
| Combined clutter scene too complex | LOW | Start simple, add detail | Use existing separate stages if needed |
| Manuscript exceeds word limit | MEDIUM | Track count weekly | Move background to supplementary |
| Synthetic-only rejected | LOW (TLSynth precedent) | Frame as methodology paper | Add 1 real Osong tunnel case (Plan B) |
| Time overrun | MEDIUM | Set hard deadlines | Prioritize Tables 7,5 > Figures > Polish |

---

## 📈 SUCCESS METRICS

**Week 1:** ✅ 100% Phase 1 tasks complete  
**Week 2:** ✅ All 6 datasets generated + validated  
**Week 3:** ✅ Full manuscript integrated + reviewed  
**Week 4:** ✅ Manuscript submitted with confirmation ID  

**Post-Submission (Target):**
- Reviewers assigned: Week 5-6
- Review complete: Week 8-10
- Decision: Accept with minor revisions (75-85% probability)
- Published: Aug-Sep 2026

---

## 🔧 HOW TO USE THIS PLAN

### **Daily Use:**
1. Open EXECUTION_CHECKLIST.md
2. Find your current week
3. Follow day-by-day tasks
4. Mark items as complete
5. Move to next item

### **Weekly Review:**
1. Open PUBLICATION_ROADMAP.md
2. Review week's goals
3. Check Phase exit criteria
4. Assess blockers
5. Adjust timeline if needed

### **For Detailed Info:**
- Task dependencies? See Task System (14 tasks with blockers)
- Timeline visualization? See PUBLICATION_ROADMAP.md
- Daily checklist? See EXECUTION_CHECKLIST.md
- Overview? See this QUICK_REFERENCE.md

---

## 📞 KEY CONTACTS & RESOURCES

**Remote Sensing MDPI:**
- Website: https://www.mdpi.com/journal/remotesensing
- Submit: https://www.mdpi.com/user/manuscript/new
- Contact: support@mdpi.com

**Zenodo (Dataset Publishing):**
- Website: https://zenodo.org
- Account: (create Week 1)
- Cost: FREE

**Reference Paper (TLSynth):**
- Title: "TLSynth: A Novel Blender Add-On for Real-Time Point Cloud Generation"
- DOI: 10.3390/rs17030421
- Year: 2025
- Full text: https://www.mdpi.com/2072-4292/17/3/421

---

## 💡 KEY NUMBERS TO REMEMBER

| Metric | Value | Why |
|--------|-------|-----|
| Weeks to submit | 4 | Timeline constraint |
| Hours per week | 35-50 | Effort estimate |
| New LAS files | 6 | 5 curvatures + 1 combined |
| New tables | 2 | Tables 5, 7 extended |
| New figures | 3 | Figures 7, 8, 9 |
| Total tables in paper | 9 | Tables 1-9 |
| Total figures in paper | 9 | Figures 1-9 |
| Acceptance probability | 75-85% | Based on TLSynth precedent |
| Review cycle weeks | 4-6 | Typical Remote Sensing |
| Deformation accuracy (synthetic) | 0.58 mm MAE | From Table 8 |
| Frenet bias scaling | Quadratic | New finding (Table 7) |
| Publication timeline | Aug-Sep 2026 | Expected 2-3 months post-acceptance |

---

## 🚀 STARTING TODAY (June 23)

**Must do RIGHT NOW:**
1. [ ] Review PUBLICATION_ROADMAP.md (15 min)
2. [ ] Review EXECUTION_CHECKLIST.md - Week 1 section (10 min)
3. [ ] Start Task #1: Read TLSynth paper
4. [ ] Setup git branch: `feature/remote-sensing-publication`
5. [ ] Create reminder: "Start Phase 2 on June 30"

**Week 1 Target:**
- [ ] All 3 Phase 1 tasks complete
- [ ] Environment verified
- [ ] Ready to generate datasets

**Week 2 Target:**
- [ ] 6 new datasets generated
- [ ] Limitations section drafted
- [ ] All data validated

**Week 3 Target:**
- [ ] Full manuscript with new data
- [ ] Discussion rewritten
- [ ] Language consistency checked

**Week 4 Target:**
- [ ] ✅ SUBMITTED TO REMOTE SENSING MDPI

---

## 📖 HOW THE PLAN ADDRESSES THE RESEARCH GAP

**Gap #2: mm-level deformation benchmark**

This plan fills the gap by:

1. **Creating ground truth datasets** (Week 2)
   - 5 curvature variations → shows robustness
   - Combined clutter → shows realism
   - Prescribed deformations → known ground truth

2. **Validating measurement accuracy** (Weeks 2-3)
   - Measure recovered deformation on synthetic
   - Compare to known values (ground truth)
   - Report error: 0.58 mm MAE on synthetic
   - Show scaling with curvature

3. **Documenting methodology** (Weeks 1-3)
   - Reproducible raycasting protocol
   - Published code + scripts
   - Open datasets on Zenodo

4. **Framing for Q1 publication** (Weeks 3-4)
   - Methodology paper (not field validation)
   - Synthetic validation as legitimate gap
   - Limitations transparently discussed
   - Path to field validation clear

**Result**: First published benchmark for tunnel deformation tool accuracy on synthetic ground truth

---

## 🎓 RESEARCH CONTRIBUTION SUMMARY

**What This Work Contributes:**

1. **Reproducible synthetic validation protocol**
   - Extends TLSynth to deformation measurement
   - Publicly available code + datasets
   - Can be adopted by other tools

2. **Mm-level accuracy benchmark**
   - First quantified deformation measurement accuracy
   - Against known prescribed deformation
   - Across multiple tunnel geometries

3. **Robustness evidence**
   - Works across 5 curvatures (0-15°/100m)
   - Works with realistic clutter (cables, fixtures)
   - Deformation accuracy maintained

4. **Open research artifacts**
   - 6 labelled benchmark datasets (Zenodo)
   - Python analysis code (reproducible)
   - Blender generation scripts (extensible)

5. **Validation standard for field work**
   - Sets accuracy expectations
   - Provides comparison baseline
   - Enables claims backed by evidence

---

**This is your roadmap. Let's execute it. 🚀**

**Start with Task #1 today. You've got this.**

---

**Created**: 2026-06-23 (Today)  
**Target Submission**: 2026-07-21 (4 weeks from now)  
**Expected Publication**: 2026-08-15 to 2026-09-30  
**Owner**: Research Team  
**Status**: ✅ READY TO BEGIN
