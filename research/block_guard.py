#!/usr/bin/env python3
"""generate the constants for the eight block checks."""
from pathlib import Path
import sys

Q = 8380417
ROOT = 1753
N = 256
BLOCKS = 8
SIZE = N // BLOCKS


def bit_reverse(value, bits):
    return int(f"{value:0{bits}b}"[::-1], 2)


def inverse(value):
    return pow(value, Q - 2, Q)


def make_tables():
    roots = [pow(ROOT, 2 * bit_reverse(i, 8) + 1, Q) for i in range(N)]
    weights = []
    expected = []
    for block in range(BLOCKS):
        base = roots[block * SIZE]
        eta = pow(base, SIZE, Q)
        scale = (1 - eta) * inverse(SIZE * eta % Q) % Q
        expected.append(sum(pow(base, SIZE * j, Q) for j in range(BLOCKS)) % Q)
        for i in range(block * SIZE, (block + 1) * SIZE):
            weights.append(scale * roots[i] * inverse((1 - roots[i]) % Q) % Q)
    zetas = [pow(ROOT, bit_reverse(i, 3) * SIZE, Q) for i in range(BLOCKS)]
    return {"block_weights": weights, "block_expected": expected,
            "block_zetas": zetas}


def render(tables):
    lines = []
    for name, values in tables.items():
        lines.append(f"static const uint32_t {name}[{len(values)}] = {{")
        for i in range(0, len(values), 8):
            lines.append("    " + ", ".join(f"{x}U" for x in values[i:i + 8]) + ",")
        lines.append("};")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(__file__).with_name("block_tables.inc")
    contents = render(make_tables())
    if sys.argv[1:] == ["--check"]:
        if path.read_text() != contents:
            raise SystemExit("block_tables.inc differs from generator")
        print("block tables match")
    elif len(sys.argv) == 1:
        path.write_text(contents)
    else:
        raise SystemExit("usage: python3 research/block_guard.py [--check]")
