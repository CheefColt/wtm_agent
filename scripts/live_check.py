"""Manual live check: runs both twins of each trap in data/twins.json through real Gemini.

  python scripts/live_check.py            # all 12 traps (about 100 Gemini calls)
  python scripts/live_check.py 1 4 7      # only these traps
Not a push gate (it spends quota). A twin passes when the decision equals the expected one.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from paycheck import agent  # noqa: E402
from paycheck.store import Session  # noqa: E402


def main(only):
    twins = json.loads((ROOT / "data" / "twins.json").read_text())
    passed = total = 0
    for t in twins:
        if only and t["trap"] not in only:
            continue
        for side in ("risky", "clean"):
            x = t[side]
            r = agent.handle(Session(x["persona"]), x["text"], mode=x["mode"])
            ok = r["decision"] == x["expect"]
            passed += ok
            total += 1
            print(f"{'PASS' if ok else 'FAIL'}  trap {t['trap']:>2} {side:<5} expect={x['expect']:<4} got={r['decision']:<5} "
                  f"| {r['message']}", flush=True)
            if not ok:
                print("        " + " / ".join(r["tool_log"]), flush=True)
    print(f"\n{passed}/{total} twins as expected")


if __name__ == "__main__":
    main({int(a) for a in sys.argv[1:]})
