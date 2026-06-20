#!/usr/bin/env python3
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main():
    path = Path(sys.argv[1])
    data = defaultdict(list)
    for line in path.read_text().splitlines():
        x = json.loads(line)
        if "cycles" in x and x["op"] != "overhead":
            data[x["op"]].append(x["cycles"])
    print("operation          samples      min    median      max")
    for name in ("ntt_forward", "ntt_inverse", "pointwise",
                 "keygen", "sign", "verify"):
        a = data[name]
        if not a:
            raise SystemExit(f"missing {name} observations")
        print(f"{name:16} {len(a):8} {min(a):8} {statistics.median(a):9.0f} {max(a):8}")


if __name__ == "__main__":
    main()
