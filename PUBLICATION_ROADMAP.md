# Publication Roadmap: Raycasting Validation + Remote Sensing Paper

**Goal**: Submit to Remote Sensing MDPI by End of Week 4  
**Target**: Q1 Journal acceptance (75-85% probability)  
**Total Timeline**: 4 weeks (28 days)

---

## PHASE 1: PREPARATION (Week 1)

### Week 1 - Daily Schedule

**Monday (Day 1-2): Research & Planning**
- [ ] Task #1: Read TLSynth paper fully + Remote Sensing guidelines
- [ ] Task #2: Setup Zenodo account + plan dataset structure
- [ ] Task #3: Create execution timeline + resource checklist
- [ ] Decision: Confirm curvature sweep plan (5 variations)
- [ ] Decision: Confirm combined-clutter scene complexity

**Wednesday (Day 3-4): Setup & Preparation**
- [ ] Blender environment check: version, plugins, GPU availability
- [ ] Python environment check: laspy, scipy, numpy versions in .venv
- [ ] Git: Create branch `feature/remote-sensing-publication`
- [ ] Folder setup: Create `data/publication_datasets/` directory
- [ ] Test: Run one quick Blender raycast to verify pipeline works

**Friday (Day 5): Timeline Finalization**
- [ ] Confirm computational resources (CPU time for 5 curvatures)
- [ ] Identify reviewer panel candidates (5 names)
- [ ] Draft cover letter template
- [ ] Create submission checklist

### Phase 1 Dependencies
```
Task #1 ──┐
Task #2 ──┼──→ Task #3 ──→ Ready for Phase 2
Task #3 ──┘
```

**Exit Criteria for Phase 1:**
- ✅ All 3 tasks completed
- ✅ Blender/Python environment verified
- ✅ Computational resources confirmed
- ✅ Timeline approved

---

## PHASE 2: EXECUTION (Weeks 2-3)

### Week 2 - Dataset Generation (7 Days)

**Parallel Work Streams:**

**Stream A: Curvature Sensitivity (Task #4)**
```
Monday-Tuesday:   Generate 5 Blender tunnel meshes (0°, 2°, 5°, 10°, 15° per 100m)
Wednesday:        Raycast each mesh (5 × phase_a_raycast.py runs)
Thursday:         Verify + validate each LAS file
Friday:           Compute Frenet bias for each
Weekend (Sat-Sun): Analysis + Table 7 generation
```
**Deliverable**: 5 LAS files + extended Table 7 + Frenet bias plot

**Stream B: Combined Clutter (Task #5)**
```
Monday-Tuesday:   Design combined-clutter Blender scene (all fixtures)
Wednesday:        Raycast once
Thursday:         Run full pipeline (denoise → segment → section)
Friday:           Measure precision/recall for lining detection
```
**Deliverable**: combined_clutter.las + extended Table 5 + precision/recall metrics

**Stream C: Paper Writing - Limitations (Task #4 parallel)**
```
Monday-Tuesday:   Research Blender vs Real LiDAR differences
Wednesday-Thu:    Write Section 3.2 + Table 3
Friday:           Review and iterate
```
**Deliverable**: Section 3.2 "Limitations of Synthetic Ground Truth"

### Week 2 Dependencies
```
Curvature generation (Blender) ──→ Raycast ──→ Validate ──→ Compute metrics
Combined clutter (Blender) ──────→ Raycast ──→ Pipeline ──→ Precision/recall
Limitations writing ────────────→ Review ──→ Finalize
```

**Exit Criteria for Week 2:**
- ✅ 5 curvature LAS files validated
- ✅ Combined clutter LAS validated
- ✅ Section 3.2 drafted
- ✅ Extended Table 7 + Table 5 ready

---

### Week 3 - Paper Writing & Integration (7 Days)

**Monday-Tuesday: Language Reframing (Task #5)**
- [ ] Systematic search-replace throughout manuscript
- [ ] Update Abstract: add "synthetic ground truth" caveat
- [ ] Update Introduction: position synthetic validation as gap
- [ ] Update all Results statements: "recovers" not "measures"
- [ ] Update Discussion: lead with synthetic limitations
- [ ] Update Conclusion: emphasize "methodology validated; field next"

**Deliverable**: Manuscript with consistent synthetic-first language

**Wednesday-Thursday: Results Integration (Task #6)**
- [ ] Insert extended Table 7 (curvature sweep data)
- [ ] Insert extended Table 5 (combined-clutter results)
- [ ] Create Figure 7: Frenet Bias vs Curvature plot
- [ ] Create Figure 8: Combined-clutter point cloud before/after
- [ ] Create Figure 9: Precision/recall comparison chart
- [ ] Update all figure captions

**Deliverable**: Complete Results section with all new data + figures

**Friday: Discussion Enhancement (Task #7)**
- [ ] Rewrite Section 5.1: Synthetic validation as gap
- [ ] Write Section 5.2: Robustness across geometries
- [ ] Write Section 5.3: Real-world applicability
- [ ] Write Section 5.4: Limitations and future work
- [ ] Connect robustness findings to practical tunneling challenges

**Deliverable**: Enhanced Discussion section (3-4 pages)

**Weekend (Sat-Sun): Synthesis & Review**
- [ ] Read full manuscript end-to-end
- [ ] Check consistency across all sections
- [ ] Verify all Tables and Figures are referenced
- [ ] Identify any remaining issues

### Week 3 Dependencies
```
Language reframing ──→ Results integration ──→ Discussion ──→ Full manuscript review
```

**Exit Criteria for Week 3:**
- ✅ Full manuscript drafted with all new data
- ✅ All 9 tables integrated (Tables 1-9, with 5, 7 extended)
- ✅ All 9 figures integrated (Figures 1-9, with 3 new)
- ✅ Consistent synthetic-first language throughout
- ✅ Discussion emphasizes gap and robustness

---

## PHASE 3: SUBMISSION (Week 4)

### Week 4 - Polish & Submit (7 Days)

**Monday-Tuesday: Supplementary Materials (Task #11)**
- [ ] Organize Blender scripts (phase_a, phase_b, new curvature/clutter)
- [ ] Organize Python analysis scripts (all benchmarking code)
- [ ] Create dataset documentation (README, manifest, ground_truth CSV)
- [ ] Prepare 4 supplementary files with clear README
- [ ] Test: Can someone else reproduce your work from supplementary materials?

**Deliverable**: Complete supplementary materials package

**Wednesday-Thursday: Internal Peer Review (Task #12)**
- [ ] Content review: all claims backed by data?
- [ ] Language review: "synthetic ground truth" caveat everywhere?
- [ ] Format review: comply with Remote Sensing guidelines?
- [ ] Technical review: reproducible methodology?
- [ ] Mark-up manuscript: track all changes
- [ ] Fix all issues found

**Deliverable**: Fully revised, publication-ready manuscript

**Friday: Final Preparation (Task #13 setup)**
- [ ] Assemble all submission files:
  - Main manuscript (.docx)
  - 9 high-res figures (PNG/PDF)
  - 9 tables (in manuscript)
  - 4 supplementary files
  - Graphical abstract (optional)
- [ ] Prepare Cover Letter (300 words)
- [ ] Prepare Author Statement, Funding, CoI Declaration
- [ ] Create Zenodo account (if not done in Week 1)
- [ ] Upload to Zenodo (get DOI)
- [ ] Update supplementary materials with Zenodo DOI

**Deliverable**: Complete submission package ready to upload

**Weekend (Sat-Sun): Submit! (Task #13)**
- [ ] Login to Remote Sensing MDPI portal
- [ ] Fill submission form carefully
- [ ] Upload all files
- [ ] Provide conflict of interest statement
- [ ] Submit manuscript
- [ ] Receive confirmation email + Manuscript ID
- [ ] Record submission ID in project log

**Post-Submission (Task #14):**
- [ ] Prepare anticipated reviewer responses (draft)
- [ ] Create revision strategy document
- [ ] Set reminder: Check email for "Reviewer assigned" notification
- [ ] Estimated review time: 4-6 weeks

---

## PARALLEL WORK STREAMS VISUALIZATION

```
WEEK 1               WEEK 2                      WEEK 3                WEEK 4
(Prep)              (Execution)                 (Writing)             (Submit)
─────────────────────────────────────────────────────────────────────────────

Phase 1.1-1.3       Phase 2.1  Curvature       Phase 2.6  Results     Phase 3.1  Supp.
(Planning)  ──────→ (Blender)  generation ──→ integration  ──────────→ Materials ──→
                      │                                                    │
                      ├──→ Phase 2.4  ──────────────────────────────────┤
                      │    Limitations writing  ────→ Phase 2.5 ──────┤
                      │                           Language reframe ──┤
                    Phase 2.2  Combined                              │
                    (Blender)  clutter    ──→ Phase 2.7 ──────────┤
                                            Discussion writing     │
                                                                  Phase 3.2
                                                                  Internal
                                                    ───────────→ Review ──→
                                                                          Phase 3.3
                                                                          Submit to
                                                                          Remote
                                                                          Sensing
```

---

## RESOURCE ALLOCATION

### Computational Resources
- **Blender**: ~2 hours per curvature (5 curvatures = 10 hours total)
- **Python Processing**: ~4 hours (analysis, metric computation)
- **Rendering/Validation**: ~3 hours
- **Total Compute Time**: ~17 hours (spread across Week 2-3)

### Human Effort
- **Week 1**: 16-20 hours (planning, setup, research)
- **Week 2**: 40-50 hours (Blender work + writing)
- **Week 3**: 40-50 hours (paper writing + integration)
- **Week 4**: 20-25 hours (supplementary materials + polish + submit)
- **Total**: 116-145 hours (~3.3-4.1 full-time weeks)

### Tools & Access Needed
- ✅ Blender 4.x (installed)
- ✅ Python 3.12 + .venv (ready)
- ✅ Laspy library (for LAS handling)
- ✅ Remote Sensing MDPI account (create Week 1)
- ✅ Zenodo account (create Week 1)
- ⚠️ GPU preferred (faster Blender raycast) - optional but recommended

---

## RISK MANAGEMENT

### Risk 1: Blender Raycast Performance
**Probability**: MEDIUM  
**Impact**: Could delay curvature sweep  
**Mitigation**:
- Test one curvature first (Monday Week 2)
- If slow, consider reducing sphere subdivisions temporarily
- Can parallelize across multiple Blender instances if needed

**Contingency**: If Blender is too slow, generate 3 curvatures (0°, 5°, 10°) instead of 5

---

### Risk 2: Combined-Clutter Scene Design
**Probability**: LOW  
**Impact**: Could delay Table 5 update  
**Mitigation**:
- Reuse existing fixtures from current T0-T5 Blender file
- Don't over-engineer; keep it realistic but simple
- Have working version by Wednesday Week 2

**Contingency**: Use current separate-stage results if combined scene doesn't work

---

### Risk 3: Manuscript Word Count
**Probability**: MEDIUM  
**Impact**: May exceed Remote Sensing limits  
**Mitigation**:
- Track word count weekly (target 12-15 pages)
- Be concise in limitations section
- Move detailed derivations to supplementary materials

**Contingency**: If over limit, can move some background to supplementary

---

### Risk 4: Reviewer Rejection of Synthetic-Only
**Probability**: LOW (given TLSynth precedent)  
**Impact**: Could require major revision  
**Mitigation**:
- Frame paper as "methodology validation" not "field deployment"
- Emphasize robustness across 5 curvatures + combined clutter
- Section 3.2 explicitly addresses limitations
- Discussion positions field work as next step

**Contingency**: If rejected, have "Plan B" to add 1 real Osong tunnel case

---

### Risk 5: Time Overrun
**Probability**: MEDIUM  
**Impact**: Could delay submission  
**Mitigation**:
- Set hard deadlines for each phase (no slipping)
- Pre-define "minimum viable" for each deliverable
- Prioritize: Tables 7, 5 > 3 new figures > perfect polish

**Contingency**: Can submit with 2 new figures (not 3) if needed

---

## SUCCESS CRITERIA

### Phase 1 (Week 1)
- ✅ All planning tasks complete
- ✅ Environment verified
- ✅ Computational resources confirmed

### Phase 2 (Weeks 2-3)
- ✅ 5 curvature datasets generated + validated
- ✅ Combined-clutter dataset generated + validated
- ✅ Limitations section drafted
- ✅ Full manuscript with new data integrated
- ✅ Discussion enhanced with robustness findings
- ✅ Word count 12-15 pages

### Phase 3 (Week 4)
- ✅ Supplementary materials complete
- ✅ Internal review passed (no major issues)
- ✅ All figures/tables formatted per guidelines
- ✅ Manuscript submitted to Remote Sensing MDPI
- ✅ Confirmation email received with Manuscript ID

### Post-Submission (Weeks 5-10)
- ⏳ Reviewers assigned (typically 2-3 weeks)
- ⏳ Review comments received (4-6 weeks)
- ⏳ Prepare revision response (if needed)
- ⏳ Resubmit if major revision required

---

## EXPECTED OUTCOMES

### Best Case (75-85% probability)
- ✅ Manuscript accepted by Week 10-12
- ✅ Published in Remote Sensing MDPI
- ✅ DOI: 10.3390/rs18XXXXXX
- ✅ Open-source datasets available on Zenodo
- ✅ Can cite in future field papers

### Good Case (10-15% probability)
- ⚠️ Minor revisions requested
- ⚠️ Revised manuscript accepted by Week 14-16
- ⚠️ Published same as best case, slightly delayed

### Worst Case (5-10% probability)
- ❌ Major revisions required
- ❌ Need to add real tunnel case (Osong)
- ❌ Timeline extends to 3 months
- ❌ Can be mitigated by having Plan B ready

---

## NEXT STEPS (DO THIS NOW)

1. **TODAY**: 
   - [ ] Review this roadmap, confirm timeline
   - [ ] Start Task #1: Read TLSynth paper
   - [ ] Setup git branch

2. **TOMORROW**:
   - [ ] Complete Task #2: Zenodo setup
   - [ ] Complete Task #3: Timeline finalization
   - [ ] Verify Blender/Python environments

3. **END OF WEEK 1**:
   - [ ] All Phase 1 tasks done
   - [ ] Ready to start Blender curvature generation

---

## CONTACT & SUPPORT

**Questions during execution?**
- Check this roadmap for risk mitigation strategies
- Reference "Expected Outcomes" section for probability context
- If blocked, move to contingency plan

**Success Metric**: Submit to Remote Sensing MDPI by **End of Week 4 (June 23 + 28 days = July 21, 2026)**

---

**Created**: 2026-06-23  
**Status**: Ready for Phase 1 execution  
**Owner**: Research team  
**Last Updated**: 2026-06-23
