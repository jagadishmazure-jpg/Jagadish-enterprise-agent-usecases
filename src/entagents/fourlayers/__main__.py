"""python -m entagents.fourlayers [bench|gate|record] (writes results/layers.json for bench)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import bench, gate


def main(argv: list[str] | None = None) -> int:
    cmd = (argv or sys.argv[1:] or ["bench"])[0]
    if cmd == "bench":
        out = (argv or sys.argv[1:] + [None, None])[1] if len(argv or sys.argv[1:]) > 1 else "results/layers.json"
        r = bench.run()
        Path(out).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
        print(json.dumps(r["layers"], indent=1))
        return 0
    if cmd == "record":
        print(json.dumps({k: v for k, v in gate.record(2).items() if k != "cases"}))
        return 0
    if cmd == "gate":
        res = gate.check()
        print(json.dumps(res))
        return 0 if res["passed"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
