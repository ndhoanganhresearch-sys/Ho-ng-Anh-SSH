# -*- coding: utf-8 -*-
"""Smoke tests for Step 7 AI assistant offline fallback."""
import os
import numpy as np

from tunnel_analysis.models import PipelineContext, SectionGeometry
from tunnel_analysis.rag_ai import TunnelRAGAssistant

P = F = 0

def ck(name, cond, info=""):
    global P, F
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  " + info) if info else ""))
    P += 1 if cond else 0
    F += 0 if cond else 1


def section(ch=10.0, violation=True):
    sg = SectionGeometry(chainage=ch)
    sg.clearance_violation = violation
    sg.min_clearance_dist = -0.05 if violation else 0.20
    return sg

print("=== Step 7 AI offline assessment ===")
ctx = PipelineContext(
    parameters={
        "crown_settlement_mm": 32.0,
        "lateral_convergence_mm": 8.0,
        "ovality_mean_pct": 0.2,
        "eccentricity_mean_mm": 2.0,
    },
    sections=[section()],
)
ai = TunnelRAGAssistant()
offline = ai._offline_analysis(ctx)
ck("offline includes decision-support disclaimer", "decision support" in offline.lower())
ck("offline reports critical status", "OVERALL STATUS: CRITICAL" in offline)
ck("offline includes next steps", "NEXT STEPS" in offline)
ck("offline includes section alerts", "clearance violation" in offline.lower())

print("=== Step 7 AI query fallback ===")
os.environ["TUNNEL_OLLAMA_URL"] = "http://127.0.0.1:1/api/generate"
ai = TunnelRAGAssistant()
ai.OLLAMA_URL = "http://127.0.0.1:1/api/generate"
ai._TIMEOUT = (0.2, 0.2)
text = ai.query("Summarize current tunnel status", ctx)
ck("query falls back when Ollama unavailable", "LOCAL AI FALLBACK" in text or "OFFLINE RULE-BASED" in text)
ck("fallback query keeps next steps", "NEXT STEPS" in text)

print(f"\nPASS={P} FAIL={F}")
raise SystemExit(1 if F else 0)
