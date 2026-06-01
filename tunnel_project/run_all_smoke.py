# -*- coding: utf-8 -*-
"""Aggregate runner for all smoke tests (T5).

Run from the tunnel_project directory:
    python run_all_smoke.py              # run every smoke_test_*.py
    python run_all_smoke.py centerline   # run only tests whose name matches

Each smoke_test_*.py is a standalone script that prints "SMOKE TEST PASSED" and
exits 0 on success. This runner executes each in a subprocess with the SAME
interpreter, captures pass/fail, and prints a summary table plus a non-zero exit
code if any failed - so CI or a single command can gate the whole suite without
adding a test-framework dependency (pytest is not installed in either venv).

Tests that need optional packages (py4dgeo / small_gicp) are reported as SKIP,
not FAIL, when the package is missing, so the core suite stays green on the
lighter interpreter.
"""
import glob
import os
import subprocess
import sys

# Tests that require optional heavy deps; skipped (not failed) when unavailable.
OPTIONAL_DEPS = {
    "smoke_test_advanced_integrations.py": ["py4dgeo", "small_gicp"],
    "smoke_test_ifc_export.py": ["ifcopenshell"],
    "smoke_test_gror_registration.py": ["open3d"],
    "smoke_test_registration_engine.py": ["open3d"],
}


def _missing(deps):
    import importlib.util
    return [d for d in deps if importlib.util.find_spec(d) is None]


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    pattern = argv[1] if len(argv) > 1 else ""
    tests = sorted(glob.glob(os.path.join(here, "smoke_test_*.py")))
    tests = [t for t in tests if pattern in os.path.basename(t)]
    if not tests:
        print(f"No smoke tests match {pattern!r}")
        return 1

    results = []
    for t in tests:
        name = os.path.basename(t)
        miss = _missing(OPTIONAL_DEPS.get(name, []))
        if miss:
            results.append((name, "SKIP", f"missing {', '.join(miss)}"))
            continue
        proc = subprocess.run(
            [sys.executable, t], cwd=here,
            capture_output=True, text=True)
        ok = proc.returncode == 0 and "SMOKE TEST PASSED" in proc.stdout
        if ok:
            results.append((name, "PASS", ""))
        else:
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
            results.append((name, "FAIL", tail[0][:80]))

    width = max(len(n) for n, _, _ in results)
    print("\n" + "=" * (width + 24))
    print(f"{'TEST':<{width}}  RESULT  NOTE")
    print("-" * (width + 24))
    n_pass = n_fail = n_skip = 0
    for name, status, note in results:
        print(f"{name:<{width}}  {status:<6}  {note}")
        n_pass += status == "PASS"
        n_fail += status == "FAIL"
        n_skip += status == "SKIP"
    print("=" * (width + 24))
    print(f"{n_pass} passed, {n_fail} failed, {n_skip} skipped "
          f"(interpreter: {os.path.basename(os.path.dirname(os.path.dirname(sys.executable)))})")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
