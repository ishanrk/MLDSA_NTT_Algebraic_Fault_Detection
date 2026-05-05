#!/usr/bin/env python3
import ctypes as C
import hashlib
import sys
from pathlib import Path

Q = 8380417
N = 256


class Poly(C.Structure):
    _fields_ = [("c", C.c_uint32 * N)]


class Ntt(C.Structure):
    _fields_ = [("c", C.c_uint32 * N)]


def matrix(rho):
    out = []
    for r in range(4):
        row = []
        for c in range(4):
            raw = hashlib.shake_128(rho + bytes((c, r))).digest(2048)
            a = []
            for pos in range(0, len(raw), 3):
                x = int.from_bytes(raw[pos:pos + 3], "little") & 0x7fffff
                if x < Q:
                    a.append(x)
                if len(a) == N:
                    break
            assert len(a) == N
            row.append(a)
        out.append(row)
    return out


def secrets(rho):
    out = []
    for n in range(8):
        raw = hashlib.shake_256(rho + n.to_bytes(2, "little")).digest(1024)
        a = []
        for x in raw:
            for y in (x & 15, x >> 4):
                if y < 15:
                    a.append((2 - y % 5) % Q)
                if len(a) == N:
                    break
            if len(a) == N:
                break
        assert len(a) == N
        out.append(a)
    return out


def mask(rho, nonce):
    out = []
    for i in range(4):
        raw = hashlib.shake_256(rho + ((nonce + i) & 65535).to_bytes(2, "little")).digest(576)
        x = int.from_bytes(raw, "little")
        out.append([(131072 - ((x >> (18 * j)) & 262143)) % Q for j in range(N)])
    return out


def ball(seed):
    raw = hashlib.shake_256(seed).digest(512)
    sign = int.from_bytes(raw[:8], "little")
    a = [0] * N
    pos = 8
    for i in range(N - 39, N):
        j = raw[pos]
        pos += 1
        while j > i:
            j = raw[pos]
            pos += 1
        a[i] = a[j]
        a[j] = Q - 1 if (sign >> (i - (N - 39))) & 1 else 1
    return a


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    for name in ("mldsa44_expand_a", "mldsa44_expand_s", "mldsa44_expand_mask",
                 "mldsa44_sample_ball"):
        getattr(lib, name).restype = None
    lib.mldsa44_expand_a.argtypes = [C.c_void_p, C.c_void_p]
    lib.mldsa44_expand_s.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p]
    lib.mldsa44_expand_mask.argtypes = [C.c_void_p, C.c_void_p, C.c_uint32]
    lib.mldsa44_sample_ball.argtypes = [C.c_void_p, C.c_void_p]

    for rho in (bytes(32), bytes(range(32))):
        a = ((Ntt * 4) * 4)()
        lib.mldsa44_expand_a(C.byref(a), rho)
        want = matrix(rho)
        for r in range(4):
            for c in range(4):
                assert list(a[r][c].c) == want[r][c]

    for rho in (bytes(64), bytes(range(64))):
        s1, s2, y = (Poly * 4)(), (Poly * 4)(), (Poly * 4)()
        lib.mldsa44_expand_s(C.byref(s1), C.byref(s2), rho)
        want = secrets(rho)
        for i in range(4):
            assert list(s1[i].c) == want[i]
            assert list(s2[i].c) == want[i + 4]
        for nonce in (0, 1, 65535):
            lib.mldsa44_expand_mask(C.byref(y), rho, nonce)
            want = mask(rho, nonce)
            for i in range(4):
                assert list(y[i].c) == want[i]

    for seed in (bytes(32), bytes(range(32)), bytes([255] * 32)):
        c = Poly()
        lib.mldsa44_sample_ball(C.byref(c), seed)
        assert list(c.c) == ball(seed)
        assert sum(x != 0 for x in c.c) == 39
    print("sampling model passed: matrix secrets masks and challenges")


if __name__ == "__main__":
    main()
