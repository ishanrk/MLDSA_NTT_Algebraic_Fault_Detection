#!/usr/bin/env python3
import ctypes as C
import random
import re
import sys
from pathlib import Path

Q = 8380417
N = 256
ZETA = 1753


class Poly(C.Structure):
    _fields_ = [("c", C.c_uint32 * N)]


class Ntt(C.Structure):
    _fields_ = [("c", C.c_uint32 * N)]


def bitrev8(x):
    return int(f"{x:08b}"[::-1], 2)


def schoolbook(a, b):
    c = [0] * N
    for i in range(N):
        for j in range(N):
            k = i + j
            if k < N:
                c[k] += a[i] * b[j]
            else:
                c[k - N] -= a[i] * b[j]
    return [x % Q for x in c]


def evaluate(a, x):
    r = 0
    for c in reversed(a):
        r = (r * x + c) % Q
    return r


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    for name, args, ret in (
        ("mldsa_reduce", [C.c_uint64], C.c_uint32),
        ("mldsa_add", [C.c_uint32, C.c_uint32], C.c_uint32),
        ("mldsa_sub", [C.c_uint32, C.c_uint32], C.c_uint32),
        ("mldsa_mul", [C.c_uint32, C.c_uint32], C.c_uint32),
        ("mldsa_center", [C.c_uint32], C.c_int32),
        ("mldsa_uncenter", [C.c_int32], C.c_uint32),
        ("mldsa_ntt_forward", [C.POINTER(Ntt), C.POINTER(Poly)], None),
        ("mldsa_ntt_inverse", [C.POINTER(Poly), C.POINTER(Ntt)], None),
        ("mldsa_ntt_mul", [C.POINTER(Ntt), C.POINTER(Ntt), C.POINTER(Ntt)], None),
        ("mldsa_poly_mul", [C.POINTER(Poly), C.POINTER(Poly), C.POINTER(Poly)], None),
    ):
        f = getattr(lib, name)
        f.argtypes = args
        f.restype = ret

    assert pow(ZETA, N, Q) == Q - 1
    assert pow(ZETA, 2 * N, Q) == 1
    z = [0] + [pow(ZETA, bitrev8(i), Q) for i in range(1, N)]
    data = (Path(__file__).resolve().parents[1] / "src/zetas.inc").read_text()
    got = [int(x) for x in re.findall(r"(\d+)U", data)]
    assert got == z
    points = [pow(ZETA, 2 * bitrev8(i) + 1, Q) for i in range(N)]
    assert len(set(points)) == N
    assert all(pow(x, N, Q) == Q - 1 for x in points)

    rng = random.Random(0x20444)
    for _ in range(1000):
        a = rng.randrange(Q)
        b = rng.randrange(Q)
        x = rng.getrandbits(64)
        assert lib.mldsa_reduce(x) == x % Q
        assert lib.mldsa_add(a, b) == (a + b) % Q
        assert lib.mldsa_sub(a, b) == (a - b) % Q
        assert lib.mldsa_mul(a, b) == a * b % Q
        c = a if a <= Q // 2 else a - Q
        assert lib.mldsa_center(a) == c
        assert lib.mldsa_uncenter(c) == a

    vectors = [[0] * N, [1] * N, [i % Q for i in range(N)]]
    vectors += [[rng.randrange(Q) for _ in range(N)] for _ in range(5)]
    for a in vectors:
        ap = Poly((C.c_uint32 * N)(*a))
        at = Ntt()
        back = Poly()
        lib.mldsa_ntt_forward(C.byref(at), C.byref(ap))
        assert list(at.c) == [evaluate(a, x) for x in points]
        lib.mldsa_ntt_inverse(C.byref(back), C.byref(at))
        assert list(back.c) == a

    for i in range(1, len(vectors)):
        a = vectors[i]
        b = vectors[(i + 1) % len(vectors)]
        ap = Poly((C.c_uint32 * N)(*a))
        bp = Poly((C.c_uint32 * N)(*b))
        at, bt, ct = Ntt(), Ntt(), Ntt()
        out, back = Poly(), Poly()
        lib.mldsa_ntt_forward(C.byref(at), C.byref(ap))
        lib.mldsa_ntt_forward(C.byref(bt), C.byref(bp))
        lib.mldsa_ntt_mul(C.byref(ct), C.byref(at), C.byref(bt))
        lib.mldsa_ntt_inverse(C.byref(back), C.byref(ct))
        lib.mldsa_poly_mul(C.byref(out), C.byref(ap), C.byref(bp))
        expected = schoolbook(a, b)
        assert list(back.c) == expected
        assert list(out.c) == expected
    print("Python model passed: arithmetic roots twiddles NTT and 7 products")


if __name__ == "__main__":
    main()
