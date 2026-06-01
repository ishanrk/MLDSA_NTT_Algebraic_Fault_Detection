#!/usr/bin/env python3
import ctypes as C
import random
import sys
from pathlib import Path

from pqcrypto import InvalidSignatureError
from pqcrypto.sign import ml_dsa_44 as oracle


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    lib.mldsa44_keygen.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p]
    lib.mldsa44_sign.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t,
                                 C.c_void_p, C.c_size_t, C.c_void_p,
                                 C.c_size_t, C.c_void_p]
    lib.mldsa44_sign.restype = C.c_int
    lib.mldsa44_verify.argtypes = [C.c_void_p, C.c_size_t, C.c_void_p,
                                   C.c_size_t, C.c_void_p, C.c_size_t,
                                   C.c_void_p, C.c_size_t]
    lib.mldsa44_verify.restype = C.c_int
    rng = random.Random(20446)
    for i in range(200):
        seed = rng.randbytes(32)
        rnd = rng.randbytes(32)
        msg = rng.randbytes(i % 301)
        ctx = rng.randbytes(i % 256)
        pk = C.create_string_buffer(1312)
        sk = C.create_string_buffer(2560)
        sig = C.create_string_buffer(2420)
        lib.mldsa44_keygen(pk, sk, seed)
        assert lib.mldsa44_sign(sig, sk, 2560, msg, len(msg), ctx, len(ctx), rnd) == 0, i
        assert lib.mldsa44_verify(pk, 1312, msg, len(msg), ctx, len(ctx), sig, 2420) == 0, i
        oracle.verify(pk.raw, msg, sig.raw, ctx)
        ext = oracle.sign(sk.raw, msg, ctx)
        assert lib.mldsa44_verify(pk, 1312, msg, len(msg), ctx, len(ctx), ext, len(ext)) == 0, i
        try:
            oracle.verify(pk.raw, msg + b"x", sig.raw, ctx)
        except InvalidSignatureError:
            pass
        else:
            raise AssertionError((i, "oracle accepted changed message"))
    print("black box pqcrypto differential passed: 200 seeded key and message cases")


if __name__ == "__main__":
    main()
