# Research Gap Feasibility Report
## Tunnel Monitoring SHM System - Publication Strategy

**Date:** 2026-06-24  
**Project:** SSL Smart Tunnel Monitoring System  
**Target:** Q1 Publication (Remote Sensing, Automation in Construction)

---

## Executive Summary

| Gap | Difficulty | Feasibility | Timeline | Q1 Risk | Recommendation |
|-----|-----------|-------------|----------|---------|-----------------|
| #1: Auto-Denoise | ⭐⭐⭐⭐ 8/10 | ⭐⭐⭐ 60% | 3-4 months | Medium | **Secondary** |
| **#2: Frenet-Frame** | ⭐⭐⭐ 6/10 | ⭐⭐⭐⭐⭐ 95% | 2-3 months | Low | **PRIMARY ✅** |
| #3: RAG-LLM | ⭐⭐⭐⭐⭐ 9/10 | ⭐⭐ 40% | 4-6 months | High | **Tertiary** |
| #4: End-to-End | ⭐⭐⭐⭐ 7/10 | ⭐⭐⭐⭐ 80% | 5-6 months | Medium | **Secondary** |

---

## GAP #1: Cascaded Auto-Denoise (PCA + MAD + Cylindrical-Grid)

### Technical Difficulty: **8/10** ⭐⭐⭐⭐

**Why high difficulty:**
- Requires **3 sequential stages** with tuning parameters:
  1. Morphological PCA classification (linearity, sphericity, planarity thresholds)
  2. Radial MAD filtering (k=2.5, MAD-to-sigma conversion)
  3. Cylindrical-grid cable detection (60×180 bins, continuity filtering)
- **Cable geometry is structured** (elongated, high linearity) → easy false positives
- **Tuning is dataset-dependent**: tunnel diameter, cable size, density variation
- **Safety guard** (reject if >30% flagged) adds complexity

### Data Requirements: **CRITICAL** ⚠️

**Need to collect:**
- ✅ Clean reference tunnel scans (WITHOUT cables) - for baseline
- ❌ Cable-annotated scans - **USER MUST MANUALLY LABEL** 20-50 scans
  - 5-10 different tunnel types (circular, oval, rectangular)
  - Various cable runs (dense, sparse, crossing)
  - Different scanner positions (offset, overhead, side)
- ❌ Real "dirty" scans with mixed clutter (personnel, lighting, temporary targets)
- **Data collection effort:** 2-3 weeks of manual labeling

### Validation Complexity: **HIGH** ⚠️

**Metrics needed:**
1. **Precision/Recall** on cable detection (vs. manual ground truth)
2. **Geometry preservation** check:
   - Crown settlement error before/after denoise
   - Ovality error before/after denoise
   - Compare: denoise output vs. original clean scan
3. **Computational cost** (point removal efficiency)
4. **Robustness across tunnels** (different diameters, materials)

**Challenge:** No labeled tunnel dataset publicly available
- Must create synthetic dataset (Blender) OR annotate real scans manually
- Either way: **2-3 weeks work**

### Implementation Timeline: **3-4 months**

```
Week 1-2:   Data collection + labeling
Week 3-4:   Implement 3-stage cascade, tune parameters
Week 5-6:   Validation (metrics, comparisons)
Week 7-8:   Writing, figures, supplementary material
Week 9-12:  Revisions + response to reviewers
```

### Publication Difficulty: **MEDIUM-HIGH** ⚠️

**Pros:**
- ✅ Novel (no papers on unsupervised cable detection for LiDAR tunnels)
- ✅ Practical (solves real problem)

**Cons:**
- ❌ Narrow scope (mostly preprocessing, not core SHM)
- ❌ Hard to compare (no baselines in literature)
- ❌ Parameter tuning looks ad-hoc without theory
- ❌ Reviewers may ask: "Why 3 stages? Why not deep learning?"

**Target journals:**
- Remote Sensing (2nd choice) - Q1/Q2
- Sensors (easier acceptance) - Q2
- Automation in Construction - Q1 (if framed as "automated clutter removal")

### Risk Factors: 🚨

1. **Parameter sensitivity** (60×180 bins, k=2.5, thresholds)
   - Risk: Over-fit to training tunnels
   - Mitigation: Cross-validation on 5+ different tunnel types
   
2. **Cable diversity** (rebar, electrical, lighting chains)
   - Risk: Algorithm works for 1 type, fails on another
   - Mitigation: Diverse dataset representation
   
3. **False negatives on actual damage**
   - Risk: Remove real lining damage (if elongated)
   - Mitigation: Safety guard + manual review

4. **Comparison baseline**
   - Risk: No published method to compare against
   - Mitigation: Compare vs. raw (undenoised) results + commercial software

### Feasibility Score: **60%** ⚠️

**Why not higher:**
- Data annotation bottleneck (2-3 weeks)
- No ground truth baselines to compare
- Risk of reviewers questioning generalization

**Path to success:**
- Start with **synthetic Blender dataset** (1 week) to prototype
- Then collect 20-30 real annotated scans (2 weeks)
- Demonstrate on both synthetic + real

---

## GAP #2: Frenet-Frame Orthogonal Sectioning for Curved Tunnels ✅

### Technical Difficulty: **6/10** ⭐⭐⭐

**Why moderate difficulty:**
- Core math is **established** (differential geometry textbook)
- Implementation is **mechanical**:
  1. Fit cubic B-spline to tunnel centerline (Kasa circle fitting per chunk)
  2. Compute Frenet frame (tangent, normal, binormal)
  3. Slice perpendicular to tangent
- **Main challenge:** Numerical stability at low-curvature sections
- **Parameter:** B-spline knot spacing, slice thickness (ε = 0.55 × median spacing)

### Data Requirements: **MINIMAL** ✅

**Already have:**
- ✅ T0~T5 time-series deformation dataset (6 epochs, curved tunnel)
- ✅ Blender synthetic datasets (box2, lidar with known curvature)
- ✅ Real tunnel scans (if available in lab)

**Need to create:**
- ⏱️ Synthetic "ground truth" geometry (cone, cylinder, spiral tunnel in Blender)
  - Curvature range: 0° (straight) → 45° (tight curve)
  - Known exact cross-sections for validation

**Data collection effort:** 3-5 days (Blender modeling)

### Validation Complexity: **STRAIGHTFORWARD** ✅

**Metrics (quantifiable):**
1. **Ovality error comparison:**
   - World-frame (axis-aligned) → compute ovality
   - Frenet-frame (orthogonal) → compute ovality
   - **Expected: 10-15% reduction in error for curved sections**
   
2. **Section geometry preservation:**
   - Check that Frenet sections are perpendicular to tangent (dot product ≈ 0)
   - Check that centerline passes through section center
   
3. **Deformation metric accuracy:**
   - Compare crown settlement extracted from both methods
   - **Expected: ±2-3 mm agreement for T0~T5**
   
4. **Computational cost:**
   - Runtime: Frenet vs. world-frame (should be similar)

**Advantage:** Ground truth is **geometric** (not subjective)
- Can validate on synthetic data with **known exact geometry**
- No manual labeling needed

### Implementation Timeline: **2-3 months**

```
Week 1:     Review Frenet frame math, implement B-spline fitting
Week 2:     Implement Frenet-frame sectioning, test on synthetic data
Week 3:     Validate on T0~T5 dataset, measure ovality reduction
Week 4:     Create comparison plots (world-frame vs. Frenet-frame)
Week 5:     Write paper (methodology + results + discussion)
Week 6:     Create figures (before/after ovality maps, convergence plots)
Week 7-8:   Revisions
```

**Could be done in 2 months if focused.**

### Publication Difficulty: **EASY** ✅

**Pros:**
- ✅ Clear novelty: "First to apply Frenet-frame to tunnel sectioning"
- ✅ Quantifiable claim: "15% ovality bias → reduced to <2%"
- ✅ Simple method (not complex ML/statistics)
- ✅ Directly applicable to practice
- ✅ Strong figures (before/after comparison highly visual)

**Cons:**
- ❌ Method is "simple" (just differential geometry)
  - Mitigation: Frame it as "novel application" + validate broadly
- ❌ Limited scope (only sectioning, not full SHM)
  - Mitigation: Show impact on downstream (deformation measurement accuracy)

**Target journals:**
- Remote Sensing (MDPI, Q1/Q2) - **BEST FIT** ✅
- Measurement (Elsevier, Q1) - **ALSO GOOD**
- Sensors (Q2) - backup

**Why Remote Sensing/Measurement:** They publish "measurement methodology" papers
- Frenet-frame = novel measurement technique for point cloud surveying

### Risk Factors: 🟢 LOW

1. **B-spline fitting quality** (low-curvature tunnels)
   - Risk: Fitting artifacts at straight sections
   - Mitigation: Adaptive knot spacing, guard on arc span >220°
   - **Already in your code!** ✅

2. **Numerical stability** (singular tangent at inflection)
   - Risk: Tangent = 0 at curve transitions
   - Mitigation: Use central differencing, skip singular points
   - **Low risk:** Standard technique

3. **Generalization** (only tested on T0~T5?)
   - Risk: Method works only on your dataset
   - Mitigation: Test on synthetic curves (0°-90° curvature range)
   - **Easy to do:** Blender gives ground truth

### Feasibility Score: **95%** ✅✅✅

**Why so high:**
- Math is proven (not novel algorithm, just application)
- Data already exists (T0~T5 + can create synthetic)
- Validation is straightforward (geometric)
- Low risk (differential geometry is stable)

**Path to success:**
1. ✅ Implement Frenet-frame (already partially done?)
2. ✅ Validate on synthetic + T0~T5
3. ✅ Create comparison figures (world-frame vs. orthogonal)
4. ✅ Write 4000-word paper + submit Remote Sensing

---

## GAP #3: RAG-LLM for Korean Tunnel Safety Standards

### Technical Difficulty: **9/10** ⭐⭐⭐⭐⭐

**Why very high difficulty:**
- **Multi-layer system:**
  1. Knowledge base curation (extract + structure Korean standards)
  2. Embedding model (SentenceTransformer or better)
  3. Vector DB (ChromaDB or Qdrant)
  4. LLM inference (Ollama + Qwen2.5 or GPT)
  5. Prompt engineering (safety-critical context)
  6. Fallback logic (when LLM unavailable)
- **Safety-critical:** Wrong assessment could cause infrastructure failure
- **Domain-specific:** Requires deep knowledge of KR C-08080, KDS 27 25 00
- **Evaluation is subjective:** How to measure "correct" engineering judgment?

### Data Requirements: **VERY CRITICAL** ⚠️⚠️⚠️

**Need to obtain:**
- ❌ Full text of Korean standards (KR C-08080, KDS 27 25 00)
  - Cost: ~$200-500 (purchase from Korean authorities)
  - Time: 1-2 weeks (delivery)
  - **Legal:** Check if can republish excerpts in paper
  
- ❌ Curated knowledge base:
  - Crown settlement thresholds (caution: X mm, critical: Y mm)
  - Convergence limits (per width, per year)
  - Ovality/eccentricity limits
  - Decision trees (which metric triggers which action)
  - **Effort:** 2-3 weeks of manual structuring + Korean expert review
  
- ❌ Ground truth test cases:
  - 20-30 measurement scenarios (real tunnel data)
  - Expected assessment (from human engineer)
  - **Effort:** Coordinate with civil engineer, 2-3 weeks

**Data collection effort:** 4-6 weeks (if standards available)

### Validation Complexity: **VERY HIGH** ⚠️⚠️

**Challenges:**
1. **No objective metric** for "correct assessment"
   - Different engineers might give different recommendations
   - Risk: LLM output looks plausible but is wrong
   
2. **Hallucination risk** (LLM invents thresholds)
   - Must verify every claim is grounded in retrieved standards
   - Mitigation: Rule-based fallback + citation of sources
   
3. **Legal liability** (if wrong assessment is published)
   - Risk: If a tunnel fails, paper could be cited in lawsuit
   - Mitigation: Clear disclaimers, validation by licensed engineer
   
4. **Language ambiguity** (Korean → English translation)
   - Risk: Mistranslation of safety thresholds
   - Mitigation: Bilingual review + expert engineer approval

**Metrics:**
- Precision of retrieved standards (relevant? complete?)
- Faithfulness (does LLM cite retrieved chunks correctly?)
- Correctness (does assessment match licensed engineer's judgment?)

### Implementation Timeline: **4-6 months** ⏱️

```
Week 1-2:   Obtain Korean standards (purchase, translate if needed)
Week 3-4:   Build knowledge base (extract, structure, validate)
Week 5-6:   Implement RAG pipeline (ChromaDB, embeddings)
Week 7-8:   Fine-tune prompts, test on 20 scenarios
Week 9-10:  Validation with domain expert (civil engineer)
Week 11-12: Writing + legal review (disclaimer)
Week 13-16: Revisions (likely high bar)
```

**Could extend to 6-8 months if iterating with expert.**

### Publication Difficulty: **VERY DIFFICULT** ⚠️⚠️⚠️

**Pros:**
- ✅ Novel (no published RAG for Korean tunnel standards)
- ✅ Practical (direct industry application)

**Cons:**
- ❌ **Narrow scope** (only Korean standards = regional)
  - Reviewers: "Why only Korea? Why not generalizable method?"
  - Mitigation: Frame as "case study for safety standard integration"
  
- ❌ **Evaluation is weak** (no ground truth)
  - Reviewers: "How do we know the assessment is correct?"
  - Mitigation: Domain expert validation (but subjective)
  
- ❌ **Safety liability** concern
  - Reviewers/journal: Concerned about liability if wrong assessment cited
  - Mitigation: Strong disclaimers, validation protocol
  
- ❌ **Hard to reproduce** (Korean standards not freely available)
  - Reviewers: Can't verify, can't adapt to other standards
  - Mitigation: Provide anonymized standards excerpt + protocol
  
- ❌ **Outpaced by faster LLM evolution**
  - Risk: GPT-5 changes everything in 6 months
  - Mitigation: Focus on "integration pattern" not specific LLM

**Target journals:**
- Automation in Construction (Q1) - **Possible but hard**
- Computers & Geotechnics (Q1) - **Unlikely** (too AI-heavy)
- Remote Sensing - **Not a fit** (not about sensing)
- Computer-Aided Civil Engineering (Q1) - **Possible**

**Realistic acceptance rate: 20-30%** (high rejection probability)

### Risk Factors: 🔴 HIGH

1. **Standards acquisition** (cost, legal)
   - Risk: Can't get standards in time, legal restrictions
   - Mitigation: Start early, contact Korean authorities
   
2. **Expert validation bottleneck**
   - Risk: Can't find qualified engineer to validate
   - Mitigation: Network with Korean railway company (DB Cargo, Korail)
   
3. **Hallucination failures** (LLM makes up thresholds)
   - Risk: Paper published, then found to be wrong
   - Mitigation: Rigorous automated checks + human review
   
4. **Reproducibility** (can't share standards)
   - Risk: Reviewers can't verify, don't trust
   - Mitigation: Open-source protocol for other standards
   
5. **Rapid obsolescence** (LLM tech moves fast)
   - Risk: By publication time, method is outdated
   - Mitigation: Focus on problem (integration) not solution (specific LLM)

### Feasibility Score: **40%** 🔴

**Why so low:**
- Standards acquisition is bottleneck (cost, timing, legal)
- Validation is fundamentally weak (subjective)
- Safety liability concern scares journals
- Narrow scope (Korea-only) limits appeal
- High risk of rejection

**Path to success (if attempting):**
1. Partner with Korean railway authority (legal access + domain expert)
2. Create **synthetic test cases** (parametric scenarios) first
3. Validate with expert before writing paper
4. Frame as "pattern for safety standard integration" (more general)
5. Target Computer-Aided Civil Engineering (more accepting of AI)

---

## GAP #4: Integrated End-to-End Pipeline

### Technical Difficulty: **7/10** ⭐⭐⭐⭐

**Why moderate-high difficulty:**
- **Many components to integrate:**
  1. Denoise (Gap #1)
  2. Auto-align/registration (already done)
  3. Frenet-frame sectioning (Gap #2)
  4. Deformation parameter extraction (already done)
  5. M3C2 change detection (already done)
  6. IFC4X3 BIM export (mostly done)
  7. PDF report generation (already done)
  8. RAG-LLM assessment (Gap #3) - **optional**
  
- **Integration complexity:** Data flows between modules, error propagation
- **Performance optimization:** 100M+ point clouds must run in <5 mins
- **Robustness:** Must handle edge cases (empty sections, sparse data)

### Data Requirements: **MODERATE** ✅

**Already have:**
- ✅ T0~T5 time-series deformation dataset
- ✅ Blender synthetic datasets (multiple tunnel types)
- ✅ Real tunnel scans (from lab)
- ✅ IFC output schema

**Need to create:**
- ⏱️ Test suite (5-10 diverse tunnel scenarios)
  - Straight, curved, oval, damaged, sparse
  - Realistic expectations for each scenario
  
- ⏱️ Benchmark scenarios (same scans for reproducible results)

**Data collection effort:** 1-2 weeks (mostly already done)

### Validation Complexity: **MODERATE-HIGH** ⚠️

**Metrics needed:**
1. **End-to-end accuracy:**
   - Crown settlement measured → vs. ground truth (from T0~T5 manifest)
   - Convergence measured → vs. ground truth
   - **Expected:** ±2-3 mm agreement
   
2. **Processing time:**
   - Denoise: X seconds for Y million points
   - Sectioning: X seconds for Z sections
   - Full pipeline: <5 minutes for 50M points (requirement)
   
3. **Robustness:**
   - How many tunnels does it work on? (target: >90%)
   - Failure modes (empty sections, misalignment, etc.)
   
4. **Output quality:**
   - PDF reports: visually correct, readable?
   - IFC models: valid BIM structure, topologically sound?
   - CSV/Excel: correct metrics, no data loss?

**Advantage:** Already have most components
- Just need to ensure they work together end-to-end

### Implementation Timeline: **5-6 months** ⏱️

```
Month 1:    Integrate denoise + sectioning + deformation extraction
Month 2:    Ensure data flows correctly, debug integration issues
Month 3:    Performance optimization (parallel processing, caching)
Month 4:    Validation on 10+ diverse scenarios
Month 5:    Writing paper (system overview + results + case studies)
Month 6:    Supplementary material (code, datasets, reproducibility)
```

**Could be done in 4-5 months if denoise + RAG are skipped.**

### Publication Difficulty: **MEDIUM** ⚠️

**Pros:**
- ✅ **Comprehensive** (full system, not just 1 method)
- ✅ **Practical** (production-ready, deployed in industry)
- ✅ **Complete pipeline** (unusual in academia)
- ✅ **Multiple contributions** (denoise + sectioning + assessment)

**Cons:**
- ❌ **Broad but shallow** (4 components, none deeply novel)
  - Reviewers: "Which is the main contribution? Feels like engineering, not research"
  - Mitigation: Highlight the integration challenges
  
- ❌ **Each component has prior art**
  - Denoise: similar to others (just not for cables)
  - Sectioning: Frenet-frame (our novelty, but simple)
  - Deformation: standard (not novel)
  - RAG: new (if included) but in Gap #3
  - Mitigation: Frame as "first integrated system meeting standards"
  
- ❌ **Large scope = hard to review**
  - Reviewers need to understand: denoise + geometry + deformation + output
  - Mitigation: Clear separation of sections, focus on **integration novelty**

**Target journals:**
- Automation in Construction (Q1) - **BEST FIT** ✅
  - Accepts system papers, not just methods
  - Values practical applicability
- Computer-Aided Civil and Infrastructure Engineering (Q1) - **ALSO GOOD**
- Remote Sensing (Q1/Q2) - **Possible** (if emphasize Point Cloud aspect)

**Realistic acceptance rate: 60-70%** (decent chance)

### Risk Factors: 🟡 MEDIUM

1. **Integration bugs** (components don't play well together)
   - Risk: Data format mismatches, performance bottlenecks
   - Mitigation: Modular testing, integration tests
   - **Low risk if careful:** You already have most components
   
2. **Denoise module (if included) is unpredictable**
   - Risk: Works on some tunnels, not others
   - Mitigation: Make denoise optional, show before/after
   
3. **IFC4X3 BIM validation** (is the output actually valid?)
   - Risk: BIM software can't open, rejects structure
   - Mitigation: Test with multiple BIM viewers (FZKViewer, Solibri)
   
4. **Performance on large clouds** (100M+ points)
   - Risk: Takes 30 min instead of 5 min
   - Mitigation: Parallel processing, GPU acceleration, decimation

5. **Scope creep** during revision
   - Risk: Reviewers ask: "Why no AI assessment? Why no thermal imaging?"
   - Mitigation: Clear scope statement, defer nice-to-haves to "future work"

### Feasibility Score: **80%** ✅

**Why moderately high:**
- Most components already exist (low implementation risk)
- Integration is mechanical (not algorithmic challenge)
- Validation is straightforward (metrics are clear)
- Target journals accept system papers

**Path to success:**
1. ✅ Integrate components (2 months)
2. ✅ Validate on diverse dataset (1 month)
3. ✅ Write as "system paper" (focus on integration + workflow)
4. ✅ Target Automation in Construction (better fit than Remote Sensing)
5. ✅ Emphasize: "First production-grade system for Korean standards"

---

## Summary Recommendation: Publication Strategy

### 🎯 **RECOMMENDED PATH FOR Q1 SUCCESS:**

#### **Phase 1 (Months 1-3): Primary Paper - Gap #2**
- **Paper:** "Frenet-Frame-Based Orthogonal Sectioning for Accurate Tunnel Geometry Measurement from LiDAR Point Clouds"
- **Target:** Remote Sensing (MDPI, Q1/Q2)
- **Feasibility:** 95%
- **Timeline:** 2-3 months
- **Why:** Easiest to publish, clearest novelty, quantifiable claim

#### **Phase 2 (Months 4-6): Secondary Paper - Gap #1 OR Gap #4**
- **Option A (Gap #1):** "Unsupervised Cascaded Denoising for Structured Clutter Removal in Underground Tunnel LiDAR Scans"
  - Target: Sensors or Remote Sensing (Q2)
  - Feasibility: 60%
  - Risk: High (parameter tuning, evaluation)
  
- **Option B (Gap #4):** "End-to-End Automated Tunnel Structural Health Monitoring System: Integration and Validation"
  - Target: Automation in Construction (Q1)
  - Feasibility: 80%
  - Risk: Medium (broad scope, but most components exist)

**Recommendation: Choose Option B (Gap #4)** for higher Q1 probability

#### **Phase 3 (If time allows): Gap #3**
- **Skip for now.** Risk too high, timeline too long
- **Defer to future work after successful publications**

### Timeline Summary

```
Month 1-3:   Write Paper 1 (Gap #2) → Submit Remote Sensing
Month 4-6:   Write Paper 2 (Gap #4) → Submit Automation in Construction
Month 7-9:   Revisions for Paper 1 + 2
Month 10+:   Consider Gap #3 or Gap #1 as follow-up
```

### Quality vs. Quantity

- **2 papers in Q1 journals > 1 paper in Q1 + 1 paper in Q2/Q3**
- **Focus on publication quality, not on covering all gaps**
- **Each paper should have crystal-clear novelty**

---

## Risk Matrix

| Gap | Tech Risk | Data Risk | Validation Risk | Publication Risk | Overall Risk |
|-----|-----------|-----------|-----------------|------------------|--------------|
| #1 | Medium | **HIGH** | Medium | Medium | **HIGH** 🔴 |
| **#2** | Low | **Low** | **Low** | **Low** | **LOW** 🟢 |
| #3 | Medium | **CRITICAL** | **HIGH** | **HIGH** | **CRITICAL** 🔴🔴 |
| #4 | Medium | Medium | Medium | Medium | **MEDIUM** 🟡 |

---

## Final Recommendation

**To achieve Q1 publication with maximum success probability:**

1. **Publish Gap #2 first** (Feb-April 2026)
   - **Timeline:** Start now, submit Remote Sensing in 3 months
   - **Expected:** Acceptance in 6-9 months (publication Jan 2027)
   
2. **Publish Gap #4 second** (May-July 2026)
   - **Timeline:** Parallel with Gap #2 revision
   - **Expected:** Acceptance in 8-12 months (publication Aug-Oct 2027)
   
3. **Skip Gap #3 for now** (too risky for first papers)
   - **Revisit after** Gap #2 + #4 are published (builds credibility)
   
4. **Gap #1 remains open** (use as stepping stone later)
   - **Or:** Integrate into Gap #4 as "optional preprocessing"

---

**Est. Q1 papers published by EOY 2027: 2 papers** ✅
