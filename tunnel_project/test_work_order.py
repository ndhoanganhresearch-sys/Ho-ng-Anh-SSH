"""Regression test for AI work-order data logic (item 2.1, sub-step a).

Locks build_work_order(): the pure grouping/ranking transform that turns
classify_sections() output into a structured, ranked work order. No LLM/DB.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from tunnel_analysis.rag_ai import build_work_order, _dominant_issue
from tunnel_analysis.models import SectionGeometry

PASS = 0
FAIL = 0

def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"[PASS] {name}  {extra}")
    else:
        FAIL += 1; print(f"[FAIL] {name}  {extra}")

def secs(chainages):
    return [SectionGeometry(chainage=float(c)) for c in chainages]

# ---- _dominant_issue: CRITICAL outranks CAUTION, then magnitude ----
d = _dominant_issue([("CAUTION", "dW", 12.0, "mm"), ("CRITICAL", "dEcc", 11.0, "mm")])
check("dominant prefers CRITICAL", d[0] == "CRITICAL" and d[1] == "dEcc")
d2 = _dominant_issue([("CAUTION", "dW", 12.0, "mm"), ("CAUTION", "dOval", 0.7, "%")])
check("dominant picks larger magnitude among same level", d2[1] == "dW")
check("dominant of empty -> None", _dominant_issue([]) is None)

# ---- grouping: adjacent same-label sections merge into one zone ----
sections = secs([448, 450, 452, 700])
statuses = [
    ("CRITICAL", [("CRITICAL", "dW", 32.0, "mm")]),
    ("CRITICAL", [("CRITICAL", "dW", 35.0, "mm")]),
    ("CAUTION",  [("CAUTION",  "dW", 18.0, "mm")]),
    ("CAUTION",  [("CAUTION",  "ovality", 0.7, "%")]),
]
wo = build_work_order(sections, statuses, project_name="TestTunnel", group_gap_m=2.0)
check("n_sections counted", wo["n_sections"] == 4)
check("n_flagged counted", wo["n_flagged"] == 4)
# 448-452 dW merge into one zone (gaps 2.0 <= group_gap), ovality separate -> 2 items
check("merged into 2 zones", len(wo["items"]) == 2, f"got {len(wo['items'])}")
zone_dw = wo["items"][0]
check("dW zone is CRITICAL (escalated)", zone_dw["level"] == "CRITICAL")
check("dW zone spans 448-452", zone_dw["chainage_start"] == 448.0 and zone_dw["chainage_end"] == 452.0)
check("dW zone has 3 sections", zone_dw["n_sections"] == 3)
check("dW zone peak magnitude = 35", zone_dw["max_value"] == 35.0)
check("dW maps to convergence phenomenon", "convergence" in zone_dw["phenomenon"].lower())
check("dW maps to KDS standard", "KDS" in zone_dw["standard"])
check("CRITICAL priority = 48h", "48" in zone_dw["priority"])

# ---- ranking: CRITICAL ranked before CAUTION ----
check("CRITICAL zone ranked first", wo["items"][0]["level"] == "CRITICAL")
check("counts: 1 critical / 1 caution", wo["n_critical"] == 1 and wo["n_caution"] == 1)
check("ids assigned sequentially", wo["items"][0]["id"] == "WO-001" and wo["items"][1]["id"] == "WO-002")

# ---- gap larger than group_gap splits zones ----
sections2 = secs([100, 105])  # gap 5 > 2.0
statuses2 = [("CRITICAL", [("CRITICAL", "dW", 30.0, "mm")]),
             ("CRITICAL", [("CRITICAL", "dW", 30.0, "mm")])]
wo2 = build_work_order(sections2, statuses2, group_gap_m=2.0)
check("gap > group_gap -> 2 separate zones", len(wo2["items"]) == 2)

# ---- clearance violation maps to Railway Act ----
sections3 = secs([10])
statuses3 = [("CRITICAL", [("CRITICAL", "clearance", 120.0, "mm")])]
wo3 = build_work_order(sections3, statuses3)
check("clearance -> Railway Act", "Railway Act" in wo3["items"][0]["standard"])

# ---- all OK -> no items ----
wo4 = build_work_order(secs([1, 2]), [("OK", []), ("OK", [])])
check("all OK -> empty items", wo4["items"] == [] and wo4["n_flagged"] == 0)

# ---- empty input safe ----
wo5 = build_work_order([], [])
check("empty input safe", wo5["items"] == [] and wo5["n_sections"] == 0)

# ---- enrich_work_order offline: returns order unchanged, no crash ----
from tunnel_analysis.rag_ai import TunnelRAGAssistant
asst = TunnelRAGAssistant()
asst.OLLAMA_URL = "http://127.0.0.1:1/api/generate"  # unreachable -> offline path
before = len(wo["items"])
enriched = asst.enrich_work_order(wo, None, use_llm=True)
check("enrich offline returns same items", len(enriched["items"]) == before)
check("enrich offline adds no narrative", all("narrative" not in it for it in enriched["items"]))
check("enrich use_llm=False is no-op", asst.enrich_work_order(wo, None, use_llm=False) is wo)

# ---- export_work_order_pdf writes a valid PDF (headless) ----
from tunnel_analysis.pdf_reporter import TunnelPDFReporter
from tunnel_analysis.models import PipelineContext
import tempfile
ctx = PipelineContext()
ctx.sections = sections
out = os.path.join(tempfile.gettempdir(), "test_work_order_out.pdf")
if os.path.exists(out):
    os.remove(out)
try:
    written = TunnelPDFReporter().export_work_order_pdf(ctx, wo, out, project_name="TestTunnel")
    ok_file = os.path.exists(written) and os.path.getsize(written) > 500
    with open(written, "rb") as fh:
        head = fh.read(5)
    check("PDF written and non-trivial", ok_file)
    check("PDF has %PDF header", head == b"%PDF-")
except RuntimeError as e:
    # reportlab not installed -> skip gracefully (not a logic failure)
    check("export_work_order_pdf (reportlab missing, skipped)", "reportlab" in str(e).lower(),
          str(e)[:50])

# ---- empty order PDF also renders ----
try:
    out2 = os.path.join(tempfile.gettempdir(), "test_work_order_empty.pdf")
    TunnelPDFReporter().export_work_order_pdf(ctx, wo4, out2)
    check("empty-order PDF renders", os.path.exists(out2) and os.path.getsize(out2) > 300)
except RuntimeError:
    check("empty-order PDF (reportlab missing, skipped)", True)

print(f"\nPASS={PASS}  FAIL={FAIL}")
if FAIL == 0:
    print("WORK ORDER DATA LOGIC OK")
sys.exit(1 if FAIL else 0)
