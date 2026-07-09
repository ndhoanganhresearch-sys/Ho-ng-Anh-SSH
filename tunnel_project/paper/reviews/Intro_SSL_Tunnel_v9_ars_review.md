# ARS academic-paper-reviewer — Editorial Decision Package (v9)
**Manuscript:** SSL Smart Tunnel Monitoring System — *Introduction only (v9 paragraph-discipline draft)*
**Target journal:** KSCE Journal of Civil Engineering (SCIE)
**Mode:** `full` (5-reviewer panel, parallel/independent) · **Date:** 2026-06-20 · **Round:** 2 (on v9)
**Scope:** Introduction only

---

## EDITORIAL DECISION: **MAJOR REVISION** (favorable end — trending toward Minor once 2 items close)

Clear progress vs v8. One reviewer (Perspective) moved **Major → Minor Revision**. The Devil's Advocate and Methodology reviewer **still raise the same CRITICAL** (synthetic claim/evidence mismatch), so per IRON RULE #4 the decision cannot yet be Accept. But the CRITICAL is now a **framing fix (≈1 sentence)**, not a structural rebuild.

| Reviewer | v8 lean | v9 lean | Δ |
|---|---|---|---|
| EIC | Major | Major (favorable) | scores up |
| Methodology | Major (CRITICAL) | Major (CRITICAL) | narrowed |
| Domain | Major (CRITICAL) | Major (CRITICAL, citation) | same |
| Perspective | Major | **Minor** ↑ | RAG fix landed |
| Devil's Advocate | blocks Accept | blocks Accept | narrowed to 1 sentence |

---

## What v9 RESOLVED (from the v8 roadmap)
- **(E) RAG bolted-on → FIXED.** Perspective: "the v9 repositioning of the RAG/interpretation element (out of the registration paragraph, into gap 3 + the proposal) succeeds: the on-device LLM now reads as demand-pulled, not bolted-on." Perspective lean dropped to Minor.
- **Paragraph discipline → PRAISED by all.** Coherence scores 85–88; "model execution of the topic-sentence chain" (EIC), clean one-to-one gap→contribution mapping.
- **(I) "the standard" → "a standard"** softened; LiDAR-vs-total-station contrast added.
- **Partial (A):** "synthetic" qualifiers now on contributions 2 & 3 — but see below, the *inferential limitation* is still not stated.

## What STILL BLOCKS / REMAINS

| # | Issue | Raised by (v9) | Severity |
|---|---|---|---|
| **A** | **Synthetic claim/evidence mismatch** — "synthetic" is now *labelled* but no sentence says synthetic validation does NOT establish field performance / real-tunnel validation = future work. Numbers read as deployable-system evidence. | DA (C1), Methodology (C-1) | **CRITICAL** (blocks Accept) — **≈1 sentence to fix** |
| **B** | **Zero KSCE JCE / JSIM / lab citations; none ≤2 yr** (newest ref ~2016). Venue requirement + weakens "no pipeline exists" novelty. | Domain (C1), EIC (W2) | **CRITICAL for venue** (known pending) |
| C | Placeholder metrics (0.826/99.99%/0.0005%/100%) stated as results | EIC (W1), all | known pending — replace w/ validated + dataset-qualified |
| D | Novelty reads as **engineering integration, not science**; "no open-source pipeline" = availability claim. Tension with ¶4 (5 commercial packages exist [11]) | EIC (W3), DA (M1+frame-lock), Domain (originality) | MAJOR |
| E | **Denominators / baselines / provenance** missing: N for each metric; baseline recall of SOR [17]; ovality-bias magnitude; source for "5–30%" and "USD 1–3M/day" | Methodology (M1–M4), Domain (m1), DA (m1–m3) | MAJOR |
| F | **Fire opener mismatch** + ref [1] double-used (fires + Directive); Directive is a fire/safety instrument, not a deformation mandate | EIC (W4), Domain (M2+M3), DA (M3) | MAJOR |
| G | **Negative-existence claims** ("not available in open-source tunnel tools") on single cites; acknowledge centerline/Frenet prior art, scope to "to our knowledge" | EIC (W5), Domain (M3), DA (M2) | MAJOR |
| H | **Cross-disciplinary value not connected to scale**: tie IFC4X3 → portfolio/asset-register (network scale); name on-device **data-sovereignty** driver; frame system as **decision-support subordinate to the engineer** (human-in-the-loop), not full automation | Perspective (W1–W3) | MAJOR (additive — strengthens, not blocks) |
| I | "standards-informed" thin; ¶6 "complete, automated" overshoots human-in-loop reality; "level-of-detection" vs "limit of detection" term; geometry-as-proxy-for-structural-condition note; data/code availability for synthetic generator | Perspective (W4), Domain (m2/m4), Methodology (m3) | MINOR |

**Arbitration:** DA + Methodology CRITICAL (A) concerns claim/evidence-CLASS mismatch (deployable real-tunnel claim vs synthetic-only evidence) — editorial-gating, independent of placeholder numbers. Perspective's Minor is not in conflict (it scoped to cross-disciplinary framing, which v9 improved). Consensus = Major Revision; no Accept, no Reject.

---

## REVISION ROADMAP (v9 → v10)

**P0 — closes the two CRITICALs**
1. **(A) One disclosure sentence + scope every claim.** Add to ¶7 (end of contributions preamble): *"All metrics reported here are established on synthetic data with known ground truth; they establish geometric correctness under controlled conditions, and validation on field-acquired tunnel scans is the primary direction for future work."* Keep per-metric "synthetic" qualifiers. → neutralises DA C1 + Methodology C-1.
2. **(B) Add real citations** (known-pending): recent (≤2 yr) **KSCE JCE** + **JSIM** tunnel LiDAR/point-cloud/convergence/deformation + learning-based segmentation papers; **lab** self-citations; cite **Directive 2004/54/EC as its own primary source** (split from [1]); a source (or "authors' observation") for "5–30%". Place all in supporting sentences only.

**P1 — major (this round)**
3. **(D) Reframe novelty as science, not software.** Lead contributions with the two methodological novelties + a *measurement insight* (e.g., quantified ovality-bias of world-frame slicing). State what generalises beyond the tool. Resolve the ¶4-vs-¶6 tension (5 commercial packages [11] vs "no pipeline") by scoping to open-source/integrated + naming what is scientifically new.
4. **(E) Ground the numbers.** Add N/denominators + baselines (SOR recall, bias in mm/%) where metrics first appear; replace "substantially" with the measured delta.
5. **(F) Reframe ¶1 opener** to aging-asset/deformation; demote fire to one clause; anchor ¶2 mandate on the actual structural-survey standards [3,4]+cost [5], not Directive [1].
6. **(G) Scope the negative-existence claims** ("to our knowledge, among open-source tunnel tools…"); acknowledge Frenet/centerline sectioning prior art; state the new part (gravity-anchored + B-spline + adaptive thickness in an open pipeline).
7. **(H) Connect cross-disciplinary value:** 1 sentence IFC4X3 → owner asset-register at network scale; 1 clause naming the on-device data-sovereignty driver; 1 sentence framing the system as decision-support that drafts for, and remains subordinate to, the qualified engineer.

**P2 — minor (polish)**
8. (I) Narrow "standards-informed"; soften ¶6 "complete, automated"; confirm "limit of detection (LoD)" term vs [14]; add one geometry-as-proxy sentence; commit to releasing the synthetic-data generator.

---

## Author-response questions (panel)
1. Strongest *scientific* (not engineering-integration) claim — can ¶7 be re-centred on it?
2. Denominators for each metric; baseline recall of SOR [17]; magnitude of ovality bias removed?
3. Any field/real-tunnel evidence? If not, agree to state synthetic-only as a limitation?
4. Source of "5–30%"? Does any cited standard mandate *structural deformation* (not fire) monitoring?
5. Is SSL meant to replace or draft-for the qualified engineer? (state the stance)
6. Have recent (≤2 yr) competing systems been surveyed to support "no pipeline exists"?

---

*Provenance: synthesis traces only to the five Phase-1 v9 reports; no comment fabricated. DA CRITICAL (C1) persists and gates Accept. v8→v9 progress recorded above.*
