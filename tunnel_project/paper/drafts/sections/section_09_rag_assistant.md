## 9. On-Device RAG Engineering Assistant

Converting deformation metrics into a written assessment is repetitive engineering work. The assistant module (`rag_ai.py`) drafts a preliminary summary from the extracted metrics using Retrieval-Augmented Generation [15], grounding the language model in a curated set of standard excerpts. The assistant runs entirely on-device, and its output is a draft for an engineer to review, not an authoritative judgement. This local, standards-grounded assistant is the third principal contribution.

### 9.1 Retrieval

The knowledge base holds 17 curated excerpts covering the inspection metrics and methods of this pipeline: crown settlement, convergence, ovality, eccentricity, clearance, deformation heatmaps, and the underlying point cloud techniques. Each excerpt is embedded with the all-MiniLM-L6-v2 sentence-transformer model [27] and indexed in a ChromaDB collection under cosine distance. At query time the section metrics are formed into a question, embedded, and matched against the collection to retrieve the most relevant excerpts. Retrieval grounds the generated text in domain material rather than the model's parametric memory, which is the mechanism by which RAG reduces hallucination in technical settings [16].

### 9.2 Generation

The retrieved excerpts and the section metrics are passed to a local large language model served by Ollama, with Qwen2.5-3B as the default model and a low sampling temperature of 0.15 to favour faithful, low-variance summaries over creative text. The model and the vector store both run on the inspection workstation; the endpoint and model name are configurable through environment variables, so an operator can substitute a larger local model without code changes. No survey data leaves the device, which suits the data-handling constraints of critical infrastructure.

### 9.3 Deterministic fallback

A language model may be unavailable on a field laptop, and a monitoring tool cannot depend on one. When the local model cannot be reached, the assistant falls back to a deterministic rule-based assessment (`_offline_analysis`) that maps the metrics directly to OK, CAUTION, or CRITICAL using the same thresholds as the section classifier of Section 8, together with a fixed table of maintenance actions keyed to each exceeded metric. The fallback guarantees that every report receives a consistent assessment, with or without the language model, and that the deterministic path, not the generative one, owns the safety-relevant classification.

### 9.4 Scope and limitation

The assistant drafts language; it does not certify condition. Generated summaries are explicitly preliminary and require review by a qualified engineer before use in any maintenance decision. A quantitative evaluation of retrieval accuracy against a curated question-and-answer set is not yet available and is reported as an open item (Section 11.6); accordingly, this study makes no numerical claim about the assistant's answer quality. The contribution is the architecture: an on-device, standards-grounded drafting aid with a deterministic safety floor, integrated into an end-to-end tunnel pipeline.
