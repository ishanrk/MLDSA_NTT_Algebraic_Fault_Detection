#!/usr/bin/env python3
import argparse
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src/keccak_tables.inc"


def rc(t):
    if t % 255 == 0:
        return 1
    r = 1
    for _ in range(t % 255):
        top = r >> 7
        r = (r << 1) & 255
        if top:
            r ^= 0x71
    return r & 1


def tables():
    rounds = []
    for i in range(24):
        x = 0
        for j in range(7):
            x |= rc(j + 7 * i) << ((1 << j) - 1)
        rounds.append(x)

    offsets = [0] * 25
    x, y = 1, 0
    seen = {(0, 0)}
    for t in range(24):
        assert (x, y) not in seen
        seen.add((x, y))
        offsets[x + 5 * y] = ((t + 1) * (t + 2) // 2) % 64
        x, y = y, (2 * x + 3 * y) % 5
    assert len(seen) == 25 and (x, y) == (1, 0)
    assert rounds[0] == 1 and rounds[1] == 0x8082
    return rounds, offsets


def render():
    rounds, offsets = tables()
    a = ["// generated from FIPS 202 sections 3.2.2 and 3.2.5",
         "static const uint64_t rc[24] = {"]
    for i in range(0, 24, 4):
        a.append("    " + ", ".join(f"UINT64_C(0x{x:016x})" for x in rounds[i:i + 4]) + ",")
    a += ["};", "", "static const unsigned rho[25] = {"]
    for i in range(0, 25, 5):
        a.append("    " + ", ".join(f"{x}U" for x in offsets[i:i + 5]) + ",")
    a += ["};", ""]
    return "\n".join(a)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    text = render()
    if args.check:
        if OUT.read_text() != text:
            raise SystemExit("Keccak constants differ from generator output")
        print("Keccak constants verified")
    else:
        OUT.write_text(text)
        print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
