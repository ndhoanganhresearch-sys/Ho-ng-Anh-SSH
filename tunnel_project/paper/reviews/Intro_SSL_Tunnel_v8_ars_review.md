# ARS academic-paper-reviewer — Editorial Decision Package
**Manuscript:** SSL Smart Tunnel Monitoring System — *Introduction only (v8 structure draft)*
**Target journal:** KSCE Journal of Civil Engineering (SCIE)
**Mode:** `full` (5-reviewer panel, parallel/independent) · **Date:** 2026-06-18 · **Round:** 1
**Scope:** Introduction only (methodology/results out of scope; reviewers did not penalise their absence)

---

## EDITORIAL DECISION: **MAJOR REVISION**

All five reviewers independently leaned **Major Revision**. The Devil's Advocate and the Methodology reviewer each raised a **CRITICAL** issue (same root cause: synthetic-only validation presented as a "validated system" without in-text caveat). Per ARS IRON RULE #4, a DA CRITICAL finding blocks any Accept; the decision is therefore Major Revision (not Reject — every reviewer judged the issues fixable within the Introduction text without new research, except the citation backfill which is already a planned task).

**Notable positive (consensus):** the Introduction **passes the professor's structural checklist**. All reviewers praised the disciplined one-topic-sentence-per-paragraph rule, citation-free topic sentences, coherent first-sentence story, and canonical 7–8 paragraph order (EIC S1, Methodology S2, Domain ¶, Perspective S1, DA "Observations"). Structure is not the problem; **claim framing, citation coverage, and cross-disciplinary motivation are**.

---

## Reviewer leans & focus scores (0–100, Introduction-only)

| Reviewer | Lean | Originality | Coherence | Writing | Focus dim |
|---|---|---|---|---|---|
| EIC (journal fit) | Major | 68 | 84 | 82 | Lit integration 58 / Significance 66 |
| R1 Methodology | Major (1 CRITICAL) | 78 | 85 | 84 | Rigor 58 / Evidence 52 |
| R2 Domain | Major (1 CRITICAL) | 70 | 80 | 82 | **Lit integration 48** |
| R3 Perspective | Major (no critical) | 78 | 72 | 85 | Significance 74 |
| Devil's Advocate | Blocks Accept (1 CRITICAL) | — | — | — | — |

---

## Consensus matrix (issue → which reviewers raised it → severity)

| # | Issue | Raised by | Severity |
|---|---|---|---|
| **A** | **Synthetic-only validation presented as "validated system" w/o caveat**; near-perfect numbers (99.99%, 100%/100%, 0.0005%) read as field performance | DA (C1), Methodology (W1) — also EIC (W3), Domain (m3) | **CRITICAL** |
| **B** | **Zero KSCE JCE / JSIM / lab citations** — venue-gating (all 19 refs external) | Domain (C1), EIC (W1) | **CRITICAL for venue** (known pending) |
| C | Headline metrics lack denominators / sample size / baseline; 0.0005% ≈ 15 µm is a fitting residual, not measurement accuracy | Methodology (W2), DA (C1) | MAJOR |
| D | Novelty rests on "integration" / "not yet in open-source tools"; method novelty (denoiser, Frenet) not separated from tooling | EIC (W2), DA (M1), Domain (contribution framing) | MAJOR |
| E | RAG bolted-on: introduced in wrong paragraph (¶5), problem→solution inverted; novelty overclaimed; not justified vs rule-based fallback | Perspective (W1), Domain (M3/M4), DA (M2) | MAJOR |
| F | Fire-disaster opening motivates a *deformation* paper weakly; ref [1] double-used (fires + EU Directive) | EIC (W4), Domain (M1), DA (M3) | MAJOR |
| G | "Network scale" motivation dropped after ¶2; IFC4X3 / on-device data-sovereignty value never connected to it | Perspective (W2, W3) | MAJOR |
| H | Unsourced load-bearing motivators: "5–30% non-structural", "USD 1–3M/day" | Methodology (W4), DA (M4) | MAJOR |
| I | Absolute phrasing ("the standard acquisition technology", "most geometric methods"); terrestrial-vs-mobile inconsistency (¶3 vs [8]) | Domain (m1) | MINOR |
| J | Multi-epoch deformation foregrounded but no deformation accuracy number among headline claims (framing vs demonstrated mismatch) | DA (m2) | MINOR |
| K | Remove story-line/pending scaffolding before submission; "SSL" never expanded; confirm KSCE numeric→author-year citation style | EIC, DA (m3), Domain (m4) | MINOR |

**Disagreement / arbitration:** Perspective found *no* CRITICAL (cross-disciplinary issues all fixable); DA + Methodology found CRITICAL on validation framing. Arbitration: the DA/Methodology CRITICAL stands because it concerns the **foundation of the "validated" claim**, which is editorial-gating; Perspective's view is not in conflict (it simply scoped to cross-disciplinary framing). No reviewer recommended Accept or Reject — clean consensus on Major Revision.

---

## REVISION ROADMAP (prioritized — usable as `academic-paper` revision input)

**P0 — must fix (gates the decision)**
1. **(A) Temper the validation framing.** At every first mention, state metrics are on *synthetic ground-truth data*; add one sentence in ¶7/contributions preamble that real-tunnel field validation is future work. Reframe each metric so the synthetic basis is the subject. Relabel "0.0005%" as a geometric fitting residual (≈15 µm at r≈3 m), not measurement accuracy. *(DA C1, Meth W1/W2, EIC W3)*
2. **(B) Add the required citations** (the deferred task — now confirmed venue-gating): recent (≤2 yr) **KSCE JCE** + **JSIM** tunnel LiDAR/point-cloud/convergence/deformation papers, plus **lab** self-citations, **only in supporting sentences**. Add one explicit KSCE-JCE-fit positioning sentence. *(Domain C1, EIC W1)*

**P1 — major (strongly recommended this round)**
3. **(D) Separate method novelty from integration.** Lead the purpose paragraph + contributions with the two genuine methodological novelties (unsupervised cascaded denoiser; gravity-anchored Frenet sectioning); frame open-source/IFC4X3 as the *vehicle*. Reframe Frenet novelty as *quantified bias reduction vs world-frame slicing on tunnel geometry*, not "not yet in OSS tools." *(EIC W2, DA M1)*
4. **(E) Fix the RAG framing.** Move RAG out of ¶5; develop it as Limitation 3 in ¶6 leading with the demand-pull burden (manual M3C2 triage doesn't scale to a network — tie to ¶2 scale). Scope the novelty ("to our knowledge … open-source on-device"); justify RAG vs the rule-based fallback. *(Perspective W1, Domain M3/M4, DA M2)*
5. **(F) Reframe the opener.** Lead ¶1 with aging-asset structural/geometric deterioration; demote or cut the fire framing; carry the deformation-monitoring mandate on the survey-interval standards [3,4]+cost [5], not the fire/Directive [1]. Untangle [1]'s double use. *(EIC W4, Domain M1, DA M3)*
6. **(G) Close the scale↔interoperability loop.** Add 1–2 sentences (¶7) connecting network-scale monitoring → open IFC4X3 multi-epoch deformation persisting against the as-built model → asset-owner workflow; name the on-device **data-sovereignty / residency** driver for critical-infrastructure scan data. *(Perspective W2, W3)*
7. **(C/H) Ground the numbers.** Add denominators/sample sizes/baselines to headline metrics; attribute or relabel "5–30%" and "USD 1–3M/day". *(Meth W2/W4, DA M4)*

**P2 — minor (polish before submission)**
8. (I) Soften absolutes; acknowledge mobile/handheld LiDAR (consistency with [8]).
9. (J) Either add a multi-epoch deformation accuracy figure or stop foregrounding it as a headline capability.
10. (K) Remove scaffolding blocks; expand "SSL"; confirm/convert citation style to KSCE JCE (likely author–year).

---

## Author-response questions (from the panel)
1. Why KSCE JCE specifically vs a tunnelling/automation/geomatics venue?
2. Which contributions are *new methods* vs integration of established techniques (GICP/M3C2/RAG)?
3. Are all headline metrics synthetic-only? Denominators for 99.99% / 100%/100%?
4. Curvature regime of the single "reference geometry" behind 0.0005%; over how many curvatures is the Frenet bias-reduction shown?
5. Is "no system applies RAG to tunnel summaries" literal or scoped to open-source/on-device? What search supports it?
6. Is [1] one source for both the fires and the Directive — and is the Directive the right citation for a *deformation* mandate?

---

*Provenance: synthesis traces only to the five Phase-1 reports above; no comment fabricated. DA CRITICAL (C1) recorded and gates Accept. Individual reviewer reports retained in session transcript.*
