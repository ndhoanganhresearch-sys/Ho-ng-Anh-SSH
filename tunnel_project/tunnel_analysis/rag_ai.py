"""
rag_ai.py - RAG-enhanced local AI assistant with tunnel safety standards.
Per PDF section 3.7: vector DB + local LLM + safety standards knowledge base.
"""
from .common import *
from .models import PipelineContext
from .headroom_adapter import optimize_prompt
from pathlib import Path
from urllib.parse import urlparse
import os
import json
import hashlib


# ???? Korean/International tunnel safety standards knowledge base ????????????????????????
SAFETY_STANDARDS = [
    # Crown settlement
    "Crown settlement threshold: caution >10mm, critical >25mm. "
    "Per KR C-08080 (Korean Railway Safety Standards) and ITA guidelines.",

    "Crown settlement (delta_v) is measured as vertical displacement at tunnel crown. "
    "Immediate inspection required when delta_v exceeds 25mm. "
    "Monitoring frequency should increase when delta_v exceeds 10mm.",

    # Convergence
    "Horizontal convergence threshold: caution >15mm, critical >30mm. "
    "Convergence (delta_h) = sum of inward wall displacement on both sides.",

    "When horizontal convergence exceeds 30mm, tunnel may require emergency shoring. "
    "Per NATM guidelines, convergence rate >2mm/day requires immediate action.",

    # Ovality
    "Ovality (epsilon) threshold: caution >0.5%, critical >1.0%. "
    "Ovality = (a-b)/a * 100% where a=major axis, b=minor axis of fitted ellipse.",

    "High ovality indicates uneven ground pressure. "
    "Ovality >1% in circular tunnels suggests potential lining distress.",

    # Eccentricity
    "Eccentricity (e) threshold: caution >10mm, critical >25mm. "
    "Eccentricity = distance between measured center and design center.",

    "Large eccentricity may indicate differential settlement or construction error. "
    "Per KDS 27 25 00 (Korean Design Standard for Tunnels).",

    # Clearance
    "Vehicle clearance violation is a critical safety issue requiring immediate action. "
    "Korean Railway Act Article 26: minimum clearance must be maintained at all times.",

    "Clearance envelope for standard Korean railway: width 3.0m, height 4.5m for box section. "
    "Circle tunnel: minimum radius 3.0m from track centerline.",

    # Heatmap
    "Hausdorff distance heatmap color coding: "
    "green = stable (<1mm), yellow = caution (1-3mm), red = critical (>3mm). "
    "Red zones require priority inspection and possible repair.",

    # General
    "LiDAR-based tunnel inspection should be performed at minimum annually. "
    "High-risk tunnels (age >30 years, heavy traffic) require semi-annual inspection.",

    "Point cloud registration RMSE should be <2mm for reliable deformation analysis. "
    "ICP convergence criteria: relative fitness <1e-6, relative RMSE <1e-6.",

    "Frenet-Serret coordinate system ensures orthogonal cross-section extraction. "
    "Non-orthogonal sections cause apparent ovality errors up to 15%.",

    "B-spline centerline with C2 continuity eliminates kink artifacts in curved tunnels. "
    "Sliding window curvature detection identifies direction change points automatically.",

    "Ring seam detection using intensity derivative: "
    "concrete ring joints show intensity drop of 30-60% compared to lining surface. "
    "Typical ring spacing: 1.0-1.5m for precast concrete segments.",

    "Statistical outlier removal (SOR): partition tunnel into 1m sections, "
    "compute radial deviation per section, remove points outside mu +/- 2.5*sigma.",

    "Voxel downsampling grid size recommendation: 0.05m for high-density scans, "
    "0.02m for precision analysis, 0.10m for quick preview.",
]


# Map a classify_sections issue label -> (phenomenon, governing standard, the
# recommended field action). Keys cover both the T0-comparison labels
# (dW/dH/dR/dOval/dEcc) and the single-scan absolute labels
# (ovality/eccentricity/clearance) emitted by classify_sections().
WORK_ORDER_RULES = {
    "clearance":    ("Vehicle clearance violation",
                     "Korean Railway Act Art.26",
                     "Verify gauge intrusion on site; restrict/redirect traffic until cleared."),
    "dW":           ("Lateral convergence (clear-width change)",
                     "KDS 27 25 00",
                     "Install temporary props/shoring; survey convergence daily."),
    "dH":           ("Crown settlement (clear-height change)",
                     "KR C-08080",
                     "Increase crown-settlement monitoring frequency; assess overburden load."),
    "dR":           ("Radius deformation",
                     "KDS 27 25 00",
                     "Inspect lining for cracking along the affected ring(s)."),
    "dOval":        ("Ovality (cross-section distortion)",
                     "KDS 27 25 00",
                     "Check for differential ground pressure; schedule lining-distress survey."),
    "ovality":      ("Ovality (cross-section distortion)",
                     "KDS 27 25 00",
                     "Check for differential ground pressure; schedule lining-distress survey."),
    "dEcc":         ("Eccentricity (centre offset)",
                     "KDS 27 25 00",
                     "Investigate differential settlement / construction tolerance."),
    "eccentricity": ("Eccentricity (centre offset)",
                     "KDS 27 25 00",
                     "Investigate differential settlement / construction tolerance."),
}
_WORK_ORDER_FALLBACK = ("Structural anomaly", "ITA guidelines",
                        "Perform detailed engineering inspection.")
_PRIORITY = {"CRITICAL": "Within 48 hours", "CAUTION": "Within 30 days"}


def _dominant_issue(issues):
    """Pick the governing issue of a section: CRITICAL outranks CAUTION, then
    the largest magnitude. ``issues`` is the classify_sections list of
    (level, label, value, unit). Returns that tuple, or None when empty."""
    if not issues:
        return None
    def _key(it):
        level, _label, value, _unit = it
        sev = 1 if level == "CRITICAL" else 0
        mag = abs(value) if isinstance(value, (int, float)) and np.isfinite(value) else 0.0
        return (sev, mag)
    return max(issues, key=_key)


def build_work_order(sections, section_statuses, project_name="Tunnel",
                     group_gap_m=2.0):
    """Group classified warning sections into a ranked, structured work order.

    Pure data transform (no LLM / DB): consumes the SAME
    ``classify_sections()`` output used by every view (single source of truth)
    and is injected here so this module stays headless and never imports the UI.

    Args:
        sections: list of SectionGeometry (for chainage lookup).
        section_statuses: classify_sections() output -> list of (status, issues)
            aligned 1:1 with ``sections``.
        project_name: shown on the order header.
        group_gap_m: merge adjacent flagged sections sharing the same dominant
            issue when their chainage gap is <= this (metres) into one zone.

    Returns a dict with project/header counts and a ``items`` list, each item a
    contiguous zone: id, level, chainage_start/end, n_sections, phenomenon,
    issue_label, max_value, unit, standard, priority, action.
    """
    flagged = []
    for i, sec in enumerate(sections or []):
        if i >= len(section_statuses or []):
            break
        status, issues = section_statuses[i]
        if status == "OK":
            continue
        dom = _dominant_issue(issues)
        if dom is None:
            continue
        level, label, value, unit = dom
        flagged.append({
            "idx": i,
            "chainage": float(getattr(sec, "chainage", float(i))),
            "level": level, "label": label,
            "value": float(value) if isinstance(value, (int, float)) else float("nan"),
            "unit": unit,
        })

    flagged.sort(key=lambda f: f["chainage"])

    # Merge adjacent same-label sections into zones.
    zones = []
    for f in flagged:
        z = zones[-1] if zones else None
        if (z is not None and z["label"] == f["label"]
                and f["chainage"] - z["chainage_end"] <= group_gap_m):
            z["chainage_end"] = f["chainage"]
            z["n_sections"] += 1
            z["_vals"].append(f["value"])
            if f["level"] == "CRITICAL":
                z["level"] = "CRITICAL"
        else:
            zones.append({
                "label": f["label"], "level": f["level"],
                "chainage_start": f["chainage"], "chainage_end": f["chainage"],
                "n_sections": 1, "unit": f["unit"], "_vals": [f["value"]],
            })

    # Rank: CRITICAL first, then by peak magnitude.
    def _peak(z):
        vals = [abs(v) for v in z["_vals"] if np.isfinite(v)]
        return max(vals) if vals else 0.0
    zones.sort(key=lambda z: (0 if z["level"] == "CRITICAL" else 1, -_peak(z)))

    items = []
    for n, z in enumerate(zones, start=1):
        phenomenon, standard, action = WORK_ORDER_RULES.get(z["label"], _WORK_ORDER_FALLBACK)
        items.append({
            "id": f"WO-{n:03d}",
            "level": z["level"],
            "chainage_start": round(z["chainage_start"], 2),
            "chainage_end": round(z["chainage_end"], 2),
            "n_sections": z["n_sections"],
            "phenomenon": phenomenon,
            "issue_label": z["label"],
            "max_value": round(_peak(z), 2),
            "unit": z["unit"],
            "standard": standard,
            "priority": _PRIORITY.get(z["level"], "Schedule inspection"),
            "action": action,
        })

    return {
        "project": project_name,
        "n_sections": len(sections or []),
        "n_flagged": len(flagged),
        "n_critical": sum(1 for it in items if it["level"] == "CRITICAL"),
        "n_caution": sum(1 for it in items if it["level"] == "CAUTION"),
        "items": items,
    }


class TunnelRAGAssistant:
    """RAG-enhanced AI assistant with tunnel safety knowledge base."""

    # Defaults; overridden per-instance by env vars in __init__ so that runtime
    # / Docker environment changes are honoured (class-body reads would freeze
    # the values at import time):
    #   TUNNEL_OLLAMA_URL=http://localhost:11434/api/generate
    #   TUNNEL_OLLAMA_MODEL=qwen2.5:3b
    #   TUNNEL_CHROMA_HOST=http://localhost:8000  (Docker ChromaDB)
    OLLAMA_URL_DEFAULT   = "http://localhost:11434/api/generate"
    OLLAMA_MODEL_DEFAULT = "qwen2.5:3b"
    _TIMEOUT     = (5.0, 120.0)
    _DB_PATH     = str(Path.home() / ".tunnel_analysis" / "chroma_db")

    def __init__(self):
        # Read env at instantiation, not import time.
        self.OLLAMA_URL   = os.environ.get("TUNNEL_OLLAMA_URL",   self.OLLAMA_URL_DEFAULT)
        self.OLLAMA_MODEL = os.environ.get("TUNNEL_OLLAMA_MODEL", self.OLLAMA_MODEL_DEFAULT)
        self.CHROMA_HOST  = os.environ.get("TUNNEL_CHROMA_HOST",  "")   # set → Docker ChromaDB
        self._collection = None
        self._embedder   = None
        self._ready      = False

    @staticmethod
    def _parse_chroma_host(raw: str) -> tuple:
        """Parse TUNNEL_CHROMA_HOST into (host, port), tolerating missing
        scheme, https, trailing slash, and missing port. Defaults to port 8000
        (ChromaDB default) when none is given."""
        s = (raw or "").strip()
        if "://" not in s:
            s = "http://" + s
        u = urlparse(s)
        host = u.hostname or "localhost"
        port = u.port or 8000
        return host, int(port)

    def initialize(self) -> str:
        """Initialize ChromaDB + sentence-transformers embedder."""
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return "RAG dependencies missing: pip install chromadb sentence-transformers"

        try:
            # Dùng Docker ChromaDB nếu TUNNEL_CHROMA_HOST được set
            if self.CHROMA_HOST:
                host, port = self._parse_chroma_host(self.CHROMA_HOST)
                client = chromadb.HttpClient(host=host, port=port)
            else:
                Path(self._DB_PATH).mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=self._DB_PATH)
            self._collection = client.get_or_create_collection(
                name="tunnel_safety",
                metadata={"hnsw:space": "cosine"})

            # Load embedder (small, fast model)
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")

            # Index safety standards if not already indexed
            existing = self._collection.count()
            if existing < len(SAFETY_STANDARDS):
                ids  = [f"std_{i}" for i in range(len(SAFETY_STANDARDS))]
                embs = self._embedder.encode(SAFETY_STANDARDS).tolist()
                self._collection.upsert(
                    ids=ids,
                    embeddings=embs,
                    documents=SAFETY_STANDARDS)

            self._ready = True
            return f"RAG initialized: {self._collection.count()} safety standards indexed."
        except Exception as e:
            return f"RAG initialization failed: {e}"

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
        """Split plain/Markdown text into small overlapping chunks."""
        clean = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if not clean:
            return []
        if chunk_size <= overlap:
            raise ValueError("chunk_size must be greater than overlap")

        chunks = []
        start = 0
        while start < len(clean):
            end = min(start + chunk_size, len(clean))
            if end < len(clean):
                boundary = max(clean.rfind("\n\n", start, end), clean.rfind(". ", start, end))
                if boundary > start + chunk_size // 2:
                    end = boundary + 1
            chunk = clean[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(clean):
                break
            start = max(0, end - overlap)
        return chunks

    def ingest_markdown(self, path: str, source: str = None,
                        chunk_size: int = 1200, overlap: int = 150) -> str:
        """Index an external Markdown/plain-text document into the RAG collection."""
        if not self._ready or not self._embedder or not self._collection:
            init_msg = self.initialize()
            if not self._ready:
                return init_msg

        doc_path = Path(path)
        try:
            text = doc_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = doc_path.read_text(encoding="utf-8-sig")

        chunks = self._chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return f"No text chunks found in {doc_path}"

        source_name = source or doc_path.name
        digest = hashlib.sha1(str(doc_path.resolve()).encode("utf-8")).hexdigest()[:12]
        ids = [f"doc_{digest}_{i}" for i in range(len(chunks))]
        embeddings = self._embedder.encode(chunks).tolist()
        metadatas = [{"source": source_name, "path": str(doc_path), "chunk": i}
                     for i in range(len(chunks))]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas)
        return f"Indexed {len(chunks)} chunks from {source_name}. Collection size: {self._collection.count()}."

    def query(self, prompt: str, context: PipelineContext,
              n_results: int = 5) -> str:
        """Query local LLM with RAG context from safety standards."""
        # Build context string from parameters
        params_str = self._build_params_str(context)

        # RAG retrieval
        rag_context = ""
        if self._ready and self._embedder and self._collection:
            try:
                q_emb = self._embedder.encode([prompt]).tolist()
                results = self._collection.query(
                    query_embeddings=q_emb, n_results=n_results)
                docs = results.get("documents", [[]])[0]
                if docs:
                    rag_context = "\n".join(f"- {d}" for d in docs)
            except Exception as e:
                rag_context = f"(RAG retrieval failed: {e})"

        # Build prompt context separately from the engineer query so Headroom
        # can compress long measurement/RAG context while protecting the query.
        system_context = f"""You are a licensed structural engineer specialising in tunnel SHM.
Answer based on the measurement data and safety standards provided.
Be concise, quantitative, and actionable.

=== TUNNEL MEASUREMENT DATA ===
{params_str}

=== RELEVANT SAFETY STANDARDS ===
{rag_context if rag_context else "(Safety standards not available - answer from general knowledge)"}

Provide:
1. Assessment of current tunnel condition
2. Parameters exceeding thresholds (if any)
3. Recommended actions with priority
4. Locations requiring immediate attention"""
        optimized = optimize_prompt(system_context, prompt, model=self.OLLAMA_MODEL)

        # Query Ollama
        try:
            import requests
            payload = {
                "model": self.OLLAMA_MODEL,
                "prompt": optimized.prompt,
                "stream": False,
                "options": {"temperature": 0.15, "num_predict": 1500}
            }
            r = requests.post(self.OLLAMA_URL, json=payload, timeout=self._TIMEOUT)
            r.raise_for_status()
            data = r.json()
            text = data.get("response", "").strip()
            if not text:
                return ("[EMPTY RESPONSE FROM LOCAL LLM] Falling back to offline assessment.\n\n"
                        f"{self._offline_analysis(context)}")
            m  = data.get("model", "unknown")
            n  = data.get("eval_count", "?")
            es = data.get("eval_duration", 0) / 1e9
            rag_note = f"RAG: {n_results} standards retrieved" if self._ready else "RAG: not initialized"
            return f"{text}\n\n{'-'*52}\nModel: {m} | Tokens: {n} | Eval: {es:.1f}s | {rag_note} | {optimized.note}"
        except Exception as e:
            return (f"[LOCAL AI FALLBACK] Ollama/RAG response unavailable: {e}\n"
                    f"To enable LLM mode: start Ollama with 'ollama serve' and pull '{self.OLLAMA_MODEL}'.\n\n"
                    f"{self._offline_analysis(context)}")

    def enrich_work_order(self, order: dict, context: PipelineContext = None,
                          use_llm: bool = True, max_items: int = 20) -> dict:
        """Add a one-line LLM advisory ``narrative`` to each work-order item.

        All numbers come from the item data (the prompt forbids inventing
        figures); the LLM only phrases the advisory. Degrades gracefully: if
        ``use_llm`` is off, requests is missing, or Ollama is unreachable, the
        order is returned unchanged (template ``action`` still present). Safe to
        call headless / offline.
        """
        items = order.get("items") if isinstance(order, dict) else None
        if not use_llm or not items:
            return order
        try:
            import requests
        except ImportError:
            return order
        for it in items[:max_items]:
            prompt = (
                "In one concise sentence, advise a tunnel maintenance engineer about a "
                f"{it.get('level')} {it.get('phenomenon')} at chainage "
                f"{it.get('chainage_start')}-{it.get('chainage_end')} m "
                f"(peak {it.get('max_value')}{it.get('unit')}), governed by "
                f"{it.get('standard')}. Do not invent any numbers.")
            try:
                r = requests.post(self.OLLAMA_URL, json={
                    "model": self.OLLAMA_MODEL, "prompt": prompt, "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 80}},
                    timeout=(3.0, 30.0))
                r.raise_for_status()
                txt = (r.json().get("response") or "").strip().replace("\n", " ")
                if txt:
                    it["narrative"] = txt[:240]
            except Exception:
                continue
        return order

    def generate_work_order(self, context: PipelineContext, section_statuses,
                            project_name: str = "Tunnel", use_llm: bool = True,
                            group_gap_m: float = 2.0) -> dict:
        """Build + (optionally) LLM-enrich a work order in one call.

        ``section_statuses`` is the classify_sections() output (injected by the
        caller so this module never imports the UI). Render the result with
        TunnelPDFReporter.export_work_order_pdf().
        """
        order = build_work_order(context.sections, section_statuses,
                                 project_name=project_name, group_gap_m=group_gap_m)
        return self.enrich_work_order(order, context, use_llm=use_llm)

    def _build_params_str(self, context: PipelineContext) -> str:
        lines = []
        p = context.parameters
        if p:
            for k, v in p.items():
                if isinstance(v, (int, float)) and np.isfinite(float(v)):
                    lines.append(f"  {k}: {v:.3f}")
        if context.sections:
            n_viol = sum(1 for s in context.sections if s.clearance_violation)
            ov_vals = [s.ovality for s in context.sections if np.isfinite(s.ovality)]
            ec_vals = [s.eccentricity for s in context.sections if np.isfinite(s.eccentricity)]
            lines.append(f"  sections_count: {len(context.sections)}")
            lines.append(f"  clearance_violations: {n_viol}")
            if ov_vals:
                lines.append(f"  ovality_max_pct: {max(ov_vals):.3f}")
            if ec_vals:
                lines.append(f"  eccentricity_max_mm: {max(ec_vals):.3f}")
        scan = context.active_scan
        if scan:
            lines.append(f"  scan_points: {len(scan.points):,}")
            lines.append(f"  scan_file: {scan.path or 'N/A'}")
        return "\n".join(lines) if lines else "  (no parameters extracted yet)"

    def _offline_analysis(self, context: PipelineContext) -> str:
        """Offline rule-based analysis when Ollama/RAG is not available."""
        THRESHOLDS = {
            "crown_settlement_mm":    ("Crown Settlement",    10.0, 25.0, "mm"),
            "lateral_convergence_mm": ("Convergence",         15.0, 30.0, "mm"),
            "ovality_mean_pct":       ("Ovality",              0.5,  1.0, "%"),
            "eccentricity_mean_mm":   ("Eccentricity",        10.0, 25.0, "mm"),
        }
        p = context.parameters or {}
        sections = list(getattr(context, "sections", []) or [])
        lines = [
            "OFFLINE RULE-BASED ASSESSMENT",
            "=" * 40,
            "This is decision support only; confirm actions with a qualified tunnel/structural engineer.",
            "",
            "MEASUREMENT SUMMARY",
        ]
        overall = "STABLE"
        measured = 0
        for key, (label, c_thr, r_thr, unit) in THRESHOLDS.items():
            val = p.get(key)
            if not isinstance(val, (int, float)) or not np.isfinite(float(val)):
                continue
            measured += 1
            if val >= r_thr:
                lines.append(f"[CRITICAL] {label} = {val:.2f}{unit} (critical >= {r_thr}{unit})")
                overall = "CRITICAL"
            elif val >= c_thr:
                lines.append(f"[CAUTION]  {label} = {val:.2f}{unit} (caution >= {c_thr}{unit})")
                if overall == "STABLE":
                    overall = "CAUTION"
            else:
                lines.append(f"[OK]       {label} = {val:.2f}{unit}")
        if measured == 0:
            lines.append("[INFO] No Step 5 deformation parameters are available yet.")

        lines.append("")
        lines.append("SECTION ALERTS")
        if sections:
            n_viol = sum(1 for s in sections if getattr(s, "clearance_violation", False))
            clearance_values = [getattr(s, "min_clearance_dist", np.nan) for s in sections]
            clearance_values = [float(v) for v in clearance_values if np.isfinite(float(v))]
            if n_viol:
                lines.append(f"[CRITICAL] {n_viol} clearance violation section(s) detected.")
                overall = "CRITICAL"
            else:
                lines.append(f"[OK] {len(sections)} section(s) available; no clearance violation flag set.")
            if clearance_values:
                lines.append(f"Minimum clearance distance: {min(clearance_values):.3f} m")
        else:
            lines.append("[INFO] No 2D sections available; run Step 6.3 before final engineering review.")

        lines.append("")
        lines.append(f"OVERALL STATUS: {overall}")
        lines.append("NEXT STEPS")
        if overall == "CRITICAL":
            lines.append("1. Restrict/inspect the affected chainage immediately.")
            lines.append("2. Review Step 6.2/6.3 maps and export an IFC/work order for engineering action.")
        elif overall == "CAUTION":
            lines.append("1. Schedule detailed inspection and repeat monitoring at the next time point.")
            lines.append("2. Compare Step 6 trend and M3C2 map to confirm whether deformation is accelerating.")
        else:
            lines.append("1. Continue routine monitoring and keep T0/Tn records for trend comparison.")
            lines.append("2. Re-run Step 6 after the next scan campaign.")
        return "\n".join(lines)
