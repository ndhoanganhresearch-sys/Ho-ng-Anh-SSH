# Writing Rules — SSL Smart Tunnel Monitoring System Paper

Rules derived from: (1) 7 journal papers from Hyungchul Yoon's lab (CACAIE, AiC, MSSP, AEI, IEEE Sensors, Scientific Reports), (2) ARS writing quality checklist, (3) decisions validated in Introduction v5.

Target journals: Computer-Aided Civil and Infrastructure Engineering, Automation in Construction, Advanced Engineering Informatics.

---

## 1. Narrative Structure (from lab papers)

### 1.1 Literature as story, not catalogue
- WRONG: "A did X [1]. B did Y [2]. C did Z [3]."
- RIGHT: Weave citations into a narrative arc. One paragraph covers one thread of work. Multiple references appear within a single flowing sentence when they share a conclusion.
- Example from v5: "Jung et al. [8] extracted ovality metrics... Gikas [9] extended this approach... Ye et al. [10] combined 3D semantic segmentation..."

### 1.2 Gaps emerge from the literature
- Never state a gap in a standalone paragraph ("However, there is a gap in...").
- Instead, let the gap surface as the natural conclusion of the literature narrative.
- Pattern: describe what exists → note what it assumes → show the assumption fails.
- Example: "Yet these methods assume clean input data. In practice, raw tunnel scans contain 5–30% non-structural points..."

### 1.3 Hook with specifics, not generalities
- Open with a concrete incident: name, location, year, consequence (casualties, cost, closure duration).
- WRONG: "Tunnel safety is an important issue worldwide."
- RIGHT: "The catastrophic fire in the Frejus road tunnel (France, 2005) killed 2 people and closed the tunnel for three years."
- First paragraph: maximum 3 sentences.

### 1.4 Bridge sentences between paragraphs
- End each paragraph with a sentence that points to the next paragraph's topic.
- Example: "These imperatives drive the need for advances across three fronts: data quality, geometric analysis, and engineering interpretation."

### 1.5 "This study proposes" — decisive, not tentative
- Use "This study proposes..." or "This paper presents..." exactly once to introduce the system.
- The system-description paragraph is SHORT (5–7 sentences). List capabilities without proving them — that's what the contributions do.

### 1.6 Contributions in active voice with numbers
- Use "We develop...", "We introduce...", "We integrate...", "We release...".
- Every contribution includes at least one quantitative result.
- WRONG: "A denoising method is proposed that improves cleaning performance."
- RIGHT: "We develop a three-stage cascaded auto-denoising algorithm... achieving a noise recall of 0.826 while retaining 99.99% of tunnel lining points."

---

## 2. Paragraph Rhythm

### 2.1 Length variation is mandatory
- Alternate short (2–3 sentences) and long (8–12 sentences) paragraphs.
- After a long literature-review paragraph, follow with a short gap/transition paragraph.
- Never have 3+ consecutive paragraphs of similar length.

### 2.2 Introduction paragraph template
| Position | Role | Length |
|----------|------|--------|
| P1 | Hook (incidents + consequences) | Short (3 sentences) |
| P2 | Regulatory motivation + bridge | Medium (5–6 sentences) |
| P3 | Literature thread 1 → Gap 1 emerges | Long (8–12 sentences) |
| P4 | Literature thread 2 → Gap 2 emerges | Short (3–4 sentences) |
| P5 | Literature thread 3 → Gap 3 emerges | Long (8–10 sentences) |
| P6 | Proposed system | Short–Medium (5–7 sentences) |
| P7 | Contributions (numbered) | Medium (4 items) |
| P8 | Paper organisation | Short (2–3 sentences) |

### 2.3 For other sections
- Methods: procedural paragraphs can be uniform length, but break with a short summary sentence before transitioning to next subsection.
- Results: short paragraph for key finding, longer for detailed interpretation.
- Discussion: highest variation — short for emphasis, long for interpretation.

---

## 3. Sentence-Level Rules

### 3.1 Burstiness
- No 5+ consecutive sentences in the same word-count band (e.g., all 20–25 words).
- Insert a short punch sentence (under 10 words) to break monotony.
- Example: "The pattern is consistent: each tool solves one piece of the inspection puzzle."

### 3.2 Maximum sentence length
- Hard limit: 45 words per sentence.
- If a sentence exceeds 45 words, split it. Period is always an option.

### 3.3 No run-on compound sentences
- Maximum 2 clauses joined by "and" / commas in a single sentence.
- If describing a system with 4+ components, use a list or split into 2 sentences.

---

## 4. Banned & Flagged Terms

### 4.1 Never use (replace immediately)
| Banned | Replace with |
|--------|-------------|
| delve | examine, investigate, analyze |
| leverage | use, employ, apply |
| robust (non-statistical) | reliable, rigorous, tighter |
| comprehensive | thorough, extensive, detailed |
| cutting-edge | recent, advanced, state-of-the-art |
| groundbreaking | novel, original, pioneering |
| showcase | demonstrate, illustrate |
| streamline | simplify, optimize |
| actionable | (remove — just state the action) |
| holistic | integrated, whole-system |
| paradigm (except "paradigm shift" in philosophy of science) | framework, model, approach |

### 4.2 Use with caution (once per paper max)
| Term | OK context |
|------|-----------|
| novel | Only if genuinely first-of-its-kind |
| crucial | Only for safety-critical contexts |
| pivotal | Avoid entirely — prefer "key" or "central" |
| nuanced | Only with specific qualifier |

### 4.3 Exception
"Robust" in statistical sense ("robust estimator", "robust regression") is standard and exempt.

---

## 5. Punctuation Rules

### 5.1 Em dash (—)
- Limit: 3 per entire paper. Recommend 0–1.
- Replace with commas, parentheses, or a new sentence.

### 5.2 Semicolons
- Limit: 2 per 1000 words.
- Reserve for closely related parallel structures only.

### 5.3 Colon-list sequences
- Never have 2+ consecutive paragraphs that each open with "X: (1)...(2)...(3)..."
- Integrate list items into prose when possible.

---

## 6. Terminology Consistency

### 6.1 Fixed terms — do not cycle synonyms
| Concept | Fixed term | Do NOT alternate with |
|---------|-----------|----------------------|
| The system | SSL Smart Tunnel Monitoring System, or "the proposed system" | "the tool", "the framework", "the platform" |
| Point cloud cleaning | denoising | filtering, cleaning, preprocessing |
| Cross-section cutting | extraction | slicing, sectioning |
| Reference frame | Frenet frame | moving frame, local frame |
| Circle fitting | Kasa circle fitting | circle regression, least-squares circle |
| Ellipse fitting | Fitzgibbon ellipse fitting | direct ellipse fit |
| Multi-epoch comparison | M3C2 change detection | cloud-to-cloud distance |
| AI module | RAG assistant | AI engine, chatbot, LLM module |
| Design standard | KR C-08080, KDS 27 25 00 | "the Korean standard" (too vague) |

### 6.2 Abbreviation protocol
- Define on first use: "structural health monitoring (SHM)".
- After definition, use only the abbreviation.
- Never re-define in the same section.

---

## 7. Technical Writing Conventions

### 7.1 Numbers and units
- Use numerals for all measurements: "0.05 m", not "five centimeters".
- SI units with space: "4.0 m", "0.826", "99.99%".
- Ranges with en dash: "5–30%", not "5 to 30%".

### 7.2 Variable names
- Italicise single-letter variables: *k*, *λ*, *ε*, *δ*.
- Do not italicise multi-letter abbreviations: MAD, PCA, ICP.
- Subscripts in roman: *δ*_v (crown settlement), *δ*_h (lateral convergence).

### 7.3 Algorithm parameters in text
- Present with context: "radial MAD filtering (*k* = 2.5, conversion factor 1.4826)".
- Always state what the parameter controls, not just its value.

### 7.4 Citations
- Numbered style: [1], [2,3], [4–7].
- When citing within narrative: "Jung et al. [8] extracted..." (author + number).
- When citing as evidence: "...as demonstrated in previous studies [6,7]" (number only).

---

## 8. Section-Specific Guidelines

### 8.1 Abstract
- Single paragraph, 200–300 words.
- Structure: problem → method → key results → significance.
- Include 3–5 quantitative results.
- No citations, no abbreviations without definition.

### 8.2 Introduction
- Follow P1–P8 template from Section 2.2 above.
- End with paper organisation paragraph.
- Citations: 15–25 references.

### 8.3 Related Work / Literature Review
- Organise by theme, not chronologically.
- Each subsection ends with what remains unsolved.
- Summary table comparing existing methods is encouraged.

### 8.4 Methodology
- Passive voice acceptable: "The point cloud was filtered using..."
- Active voice for design decisions: "We set *k* = 20 based on..."
- Every equation gets a number and is referenced in text.
- Flowchart/diagram for pipeline overview.

### 8.5 Results
- Lead each subsection with the key finding, then show evidence.
- "The denoising stage achieved a noise recall of 0.826" before showing the table.
- Tables and figures referenced in text before they appear.

### 8.6 Discussion
- Compare with existing methods using specific numbers.
- Acknowledge limitations explicitly: "The current implementation does not handle..."
- Future work: concrete next steps, not vague promises.

### 8.7 Conclusion
- No new information.
- Mirror abstract structure but shorter (150–200 words).
- End with one forward-looking sentence.

---

## 9. Formatting (docx output)

| Element | Font | Size | Spacing |
|---------|------|------|---------|
| Title | Times New Roman | 16pt (SZ_T=32) | Center, line 360, after 200 |
| Heading | Times New Roman | 14pt (SZ_H=28) | Left, line 360, before 360, after 200 |
| Body | Times New Roman | 12pt (SZ=24) | Justified, line 360, after 200 |
| Contributions | Times New Roman | 12pt | Justified, line 360, after 120, indent left 360 |
| References | Times New Roman | 12pt | Justified, line 360, after 160, indent left 360, hanging 360 |

- Page: US Letter (12240 x 15840 DXA), margins 1 inch (1440 all sides).
- Line spacing: 1.5 (360 twips).

---

## 10. Self-Review Checklist (run before finalising each section)

- [ ] No flagged terms from Section 4.1
- [ ] Em dashes count for entire paper still under 3
- [ ] No 5+ same-length sentences in a row
- [ ] No sentence exceeds 45 words
- [ ] No standalone "gap paragraph" — gaps emerge from literature
- [ ] Contributions use active voice with quantitative results
- [ ] Terminology consistent with Section 6.1 table
- [ ] All variables italicised, all abbreviations defined on first use
- [ ] Paragraph length varies (short after long, long after short)
- [ ] Each paragraph's last sentence bridges to the next topic
- [ ] No throat-clearing openers ("It is important to note...", "In order to...")
- [ ] No meta-commentary ("This section discusses...")
- [ ] Citations integrated into narrative, not listed
